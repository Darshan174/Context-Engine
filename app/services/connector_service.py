"""Service layer for connector management."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import httpx
from redis import asyncio as aioredis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.connector import Connector, ConnectorStatus
from app.models.source import ConnectorType, SourceDocument
from app.models.user import Workspace
from app.utils.crypto import EncryptionError, decrypt_token, encrypt_token


class ConnectorServiceError(Exception):
    """Base connector service error."""


class ConnectorNotFoundError(ConnectorServiceError):
    """Raised when a requested connector is not present."""


class WorkspaceNotFoundError(ConnectorServiceError):
    """Raised when the referenced workspace does not exist."""


class ConfigurationError(ConnectorServiceError):
    """Raised when required configuration (env vars) is missing."""


class OAuthError(ConnectorServiceError):
    """Raised when a Slack OAuth exchange fails."""


class InvalidStateError(ConnectorServiceError):
    """Raised when the OAuth state parameter is invalid or expired."""


class SyncError(ConnectorServiceError):
    """Raised when a sync operation fails."""


class SyncInProgressError(ConnectorServiceError):
    """Raised when a sync is already running for this connector."""

    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Sync already in progress. Job ID: {job_id}")
        self.job_id = job_id


# Redis key prefix for OAuth state nonces
_STATE_PREFIX = "ce:oauth_state:"


class ConnectorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── List / get / sync / disconnect (unchanged) ─────────────────

    async def list_connectors(self, workspace_id: UUID) -> list[Connector]:
        await self._require_workspace(workspace_id)
        result = await self.session.scalars(
            select(Connector)
            .where(Connector.workspace_id == workspace_id)
            .order_by(Connector.connector_type)
        )
        return list(result)

    async def get_connector(self, connector_id: UUID) -> Connector:
        connector = await self.session.scalar(
            select(Connector).where(Connector.id == connector_id)
        )
        if connector is None:
            raise ConnectorNotFoundError("Connector not found")
        return connector

    async def queue_sync(self, connector_id: UUID) -> "SyncJob":
        """Dispatch a background sync job for the given connector.

        Validates connector state, creates a SyncJob, dispatches to Celery,
        and returns immediately with the pending job.  The pipeline runs
        asynchronously in the worker process.
        """
        from app.models.job import SyncJob, SyncJobStatus

        connector = await self.get_connector(connector_id)

        if connector.status != ConnectorStatus.CONNECTED:
            raise SyncError("Connector is not in a connected state")

        if not connector.oauth_token_encrypted:
            raise SyncError("Connector has no stored auth token")

        try:
            decrypt_token(connector.oauth_token_encrypted)  # validate decryptable now
        except EncryptionError as exc:
            raise ConfigurationError(str(exc)) from exc

        # Guard against double-dispatch
        existing = await self.session.scalar(
            select(SyncJob).where(
                SyncJob.connector_id == connector_id,
                SyncJob.status.in_([SyncJobStatus.PENDING, SyncJobStatus.RUNNING]),
            )
        )
        if existing is not None:
            raise SyncInProgressError(existing.id)

        job = SyncJob(
            connector_id=connector_id,
            job_type="sync",
            status=SyncJobStatus.PENDING,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)

        try:
            from app.tasks.sync import run_sync
            task_result = run_sync.delay(str(job.id), str(connector_id))
            job.celery_task_id = task_result.id
            connector.config = {
                **connector.config,
                "sync_queued_at": datetime.now(timezone.utc).isoformat(),
                "message": "Sync queued",
            }
            await self.session.commit()
            await self.session.refresh(job)
        except Exception as dispatch_exc:
            job.status = SyncJobStatus.FAILED
            job.error_type = "DispatchError"
            job.error_message = str(dispatch_exc)
            connector.config = {
                **{k: v for k, v in connector.config.items() if k != "sync_queued_at"},
                "message": f"Sync dispatch failed: {dispatch_exc}",
            }
            await self.session.commit()
            raise SyncError(f"Failed to dispatch sync task: {dispatch_exc}") from dispatch_exc

        return job

    async def get_latest_sync_job(self, connector_id: UUID):
        """Return the most recent SyncJob for this connector, or None."""
        from app.models.job import SyncJob
        await self.get_connector(connector_id)  # raises ConnectorNotFoundError if missing
        return await self.session.scalar(
            select(SyncJob)
            .where(SyncJob.connector_id == connector_id)
            .order_by(SyncJob.created_at.desc())
            .limit(1)
        )

    async def list_sync_jobs(self, connector_id: UUID, limit: int = 20):
        """Return recent SyncJobs for this connector, most recent first."""
        from app.models.job import SyncJob
        await self.get_connector(connector_id)  # raises ConnectorNotFoundError if missing
        result = await self.session.scalars(
            select(SyncJob)
            .where(SyncJob.connector_id == connector_id)
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        )
        return list(result)

    async def disconnect(self, connector_id: UUID) -> None:
        connector = await self.get_connector(connector_id)
        connector.status = ConnectorStatus.DISCONNECTED
        connector.oauth_token_encrypted = None
        await self.session.commit()

    # ── Notion manual connect ─────────────────────────────────────

    async def connect_notion(
        self, *, workspace_id: UUID, token: str
    ) -> Connector:
        """Create or update a Notion connector with the given integration token."""
        await self._require_workspace(workspace_id)

        try:
            encrypted = encrypt_token(token)
        except EncryptionError as exc:
            raise ConfigurationError(str(exc)) from exc

        connector = await self.session.scalar(
            select(Connector).where(
                Connector.workspace_id == workspace_id,
                Connector.connector_type == ConnectorType.NOTION,
            )
        )

        if connector is None:
            connector = Connector(
                workspace_id=workspace_id,
                connector_type=ConnectorType.NOTION,
                status=ConnectorStatus.CONNECTED,
                oauth_token_encrypted=encrypted,
                config={},
            )
            self.session.add(connector)
        else:
            connector.status = ConnectorStatus.CONNECTED
            connector.oauth_token_encrypted = encrypted

        await self.session.commit()
        await self.session.refresh(connector)
        return connector

    # ── Source document queries ────────────────────────────────────

    async def list_source_documents(
        self,
        workspace_id: UUID,
        *,
        connector_type: ConnectorType | None = None,
        processed: bool | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[SourceDocument], int, bool]:
        """Return source documents for a workspace with optional filters.

        Returns (items, total_count, has_more).
        """
        await self._require_workspace(workspace_id)

        # Base filter: docs scoped to workspace via connector join
        connector_ids_q = (
            select(Connector.id)
            .where(Connector.workspace_id == workspace_id)
        )
        if connector_type is not None:
            connector_ids_q = connector_ids_q.where(
                Connector.connector_type == connector_type
            )

        base = select(SourceDocument).where(
            SourceDocument.connector_id.in_(connector_ids_q)
        )
        count_q = select(func.count()).select_from(SourceDocument).where(
            SourceDocument.connector_id.in_(connector_ids_q)
        )

        if processed is True:
            base = base.where(SourceDocument.processed_at.is_not(None))
            count_q = count_q.where(SourceDocument.processed_at.is_not(None))
        elif processed is False:
            base = base.where(SourceDocument.processed_at.is_(None))
            count_q = count_q.where(SourceDocument.processed_at.is_(None))

        if cursor:
            try:
                cursor_id = UUID(cursor)
                # Fetch the cursor document's (ingested_at, id) for keyset pagination
                cursor_row = (await self.session.execute(
                    select(SourceDocument.ingested_at, SourceDocument.id).where(
                        SourceDocument.id == cursor_id,
                        SourceDocument.connector_id.in_(connector_ids_q),
                    )
                )).one_or_none()
                if cursor_row is not None:
                    cursor_ts, cursor_uid = cursor_row
                    # Compound keyset: rows that sort strictly after the cursor
                    from sqlalchemy import tuple_
                    base = base.where(
                        tuple_(
                            SourceDocument.ingested_at, SourceDocument.id
                        ) < tuple_(cursor_ts, cursor_uid)
                    )
            except ValueError:
                pass  # Invalid cursor — ignore

        total = await self.session.scalar(count_q) or 0

        rows = list(await self.session.scalars(
            base.order_by(
                SourceDocument.ingested_at.desc(),
                SourceDocument.id.desc(),
            ).limit(limit + 1)
        ))

        has_more = len(rows) > limit
        items = rows[:limit]

        return items, total, has_more

    async def get_source_document(
        self, document_id: UUID, workspace_id: UUID
    ) -> SourceDocument:
        """Return a single source document by ID, scoped to workspace."""
        await self._require_workspace(workspace_id)

        connector_ids_q = (
            select(Connector.id)
            .where(Connector.workspace_id == workspace_id)
        )
        doc = await self.session.scalar(
            select(SourceDocument).where(
                SourceDocument.id == document_id,
                SourceDocument.connector_id.in_(connector_ids_q),
            )
        )
        if doc is None:
            raise ConnectorNotFoundError("Source document not found")
        return doc

    async def get_processing_summary(
        self, workspace_id: UUID
    ) -> list[dict]:
        """Return per-connector processing counts for a workspace."""
        await self._require_workspace(workspace_id)

        connectors = await self.list_connectors(workspace_id)
        summaries = []
        for conn in connectors:
            total = await self.session.scalar(
                select(func.count()).select_from(SourceDocument).where(
                    SourceDocument.connector_id == conn.id
                )
            ) or 0
            processed = await self.session.scalar(
                select(func.count()).select_from(SourceDocument).where(
                    SourceDocument.connector_id == conn.id,
                    SourceDocument.processed_at.is_not(None),
                )
            ) or 0
            summaries.append({
                "connector_id": conn.id,
                "connector_type": conn.connector_type.value,
                "status": conn.status.value,
                "total_documents": total,
                "processed_documents": processed,
                "unprocessed_documents": total - processed,
                "last_sync_at": conn.last_sync_at,
            })
        return summaries

    # ── Slack install URL with Redis-backed state ──────────────────

    async def build_slack_install_url(self, workspace_id: UUID) -> str:
        self._require_slack_config()

        nonce = secrets.token_urlsafe(24)
        state = f"{workspace_id}:{nonce}"

        # Persist state → workspace_id mapping in Redis with TTL
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await redis.setex(
                f"{_STATE_PREFIX}{state}",
                settings.oauth_state_ttl_seconds,
                str(workspace_id),
            )
        finally:
            await redis.aclose()

        scopes = "channels:history,channels:read,groups:history,groups:read,users:read,team:read"
        redirect_uri = settings.slack_redirect_uri or ""

        url = (
            "https://slack.com/oauth/v2/authorize"
            f"?client_id={settings.slack_client_id}"
            f"&scope={scopes}"
            f"&state={state}"
        )
        if redirect_uri:
            url += f"&redirect_uri={redirect_uri}"

        return url

    # ── Slack OAuth callback ───────────────────────────────────────

    async def handle_slack_callback(
        self, *, code: str | None, state: str | None, error: str | None
    ) -> Connector:
        """Process the OAuth callback from Slack.

        Validates state, exchanges the code for a token, and upserts
        the Connector row.
        """
        if error:
            raise OAuthError(f"Slack returned an error: {error}")

        if not state:
            raise InvalidStateError("Missing OAuth state parameter")

        if not code:
            raise OAuthError("Missing authorization code from Slack")

        # Validate + consume state from Redis (one-time use)
        workspace_id = await self._validate_and_consume_state(state)

        # Exchange code for access token
        token_data = await self._exchange_slack_code(code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise OAuthError("Slack token exchange did not return an access token")

        try:
            encrypted = encrypt_token(access_token)
        except EncryptionError as exc:
            raise ConfigurationError(str(exc)) from exc

        # Upsert: create or update connector for workspace + slack
        connector = await self.session.scalar(
            select(Connector).where(
                Connector.workspace_id == workspace_id,
                Connector.connector_type == ConnectorType.SLACK,
            )
        )

        slack_team = token_data.get("team", {})
        oauth_meta = {
            "team_id": slack_team.get("id"),
            "team_name": slack_team.get("name"),
            "authed_user_id": token_data.get("authed_user", {}).get("id"),
            "scope": token_data.get("scope"),
        }

        if connector is None:
            connector = Connector(
                workspace_id=workspace_id,
                connector_type=ConnectorType.SLACK,
                status=ConnectorStatus.CONNECTED,
                oauth_token_encrypted=encrypted,
                config=oauth_meta,
            )
            self.session.add(connector)
        else:
            connector.status = ConnectorStatus.CONNECTED
            connector.oauth_token_encrypted = encrypted
            # Merge: preserve existing operational fields (document_count,
            # sync_queued_at, etc.) while updating OAuth/team metadata.
            connector.config = {**connector.config, **oauth_meta}

        await self.session.commit()
        await self.session.refresh(connector)
        return connector

    # ── Private helpers ────────────────────────────────────────────

    async def _validate_and_consume_state(self, state: str) -> UUID:
        """Look up the state nonce in Redis, delete it, return the workspace_id."""
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            key = f"{_STATE_PREFIX}{state}"
            workspace_id_str = await redis.getdel(key)
        finally:
            await redis.aclose()

        if workspace_id_str is None:
            raise InvalidStateError("Invalid or expired OAuth state")

        try:
            workspace_id = UUID(workspace_id_str)
        except ValueError:
            raise InvalidStateError("Corrupt OAuth state data")

        # Verify workspace still exists
        await self._require_workspace(workspace_id)
        return workspace_id

    async def _exchange_slack_code(self, code: str) -> dict:
        """POST to Slack's oauth.v2.access to exchange code for token."""
        self._require_slack_config()

        async with httpx.AsyncClient(timeout=15) as http:
            try:
                resp = await http.post(
                    "https://slack.com/api/oauth.v2.access",
                    data={
                        "client_id": settings.slack_client_id,
                        "client_secret": settings.slack_client_secret,
                        "code": code,
                        "redirect_uri": settings.slack_redirect_uri or "",
                    },
                )
            except httpx.HTTPError as exc:
                raise OAuthError(
                    f"Slack token exchange request failed: {exc.__class__.__name__}"
                ) from exc

        if resp.status_code != 200:
            raise OAuthError(f"Slack API returned HTTP {resp.status_code}")

        body = resp.json()
        if not body.get("ok"):
            slack_error = body.get("error", "unknown_error")
            raise OAuthError(f"Slack token exchange failed: {slack_error}")

        return body

    def _require_slack_config(self) -> None:
        if not settings.slack_client_id or not settings.slack_client_secret:
            raise ConfigurationError(
                "Slack integration is not configured. "
                "Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET environment variables."
            )

    async def _require_workspace(self, workspace_id: UUID) -> None:
        exists = await self.session.scalar(
            select(Workspace.id).where(Workspace.id == workspace_id).limit(1)
        )
        if exists is None:
            raise WorkspaceNotFoundError("Workspace not found")
