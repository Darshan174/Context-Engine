"""Service layer for connector management."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import httpx
from redis import asyncio as aioredis
from sqlalchemy import case, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.connectors.base import AuthenticationError, BaseConnector, ConnectorError, NormalizedDocument
from app.connectors.notion import NotionConnector
from app.connectors.slack import SlackConnector
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.source import ConnectorType, SourceDocument
from app.models.user import Workspace
from app.services.ingestion_service import IngestionService
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

    async def queue_sync(self, connector_id: UUID) -> Connector:
        """Start a sync for the given connector.

        Resolves the correct connector implementation, decrypts the
        stored token, fetches documents, persists them into
        source_documents (deduped on connector_type + external_id),
        and updates SyncState with the new cursor.

        For now this runs synchronously in-request.  A future phase
        will dispatch to Celery so the endpoint returns immediately.
        """
        connector = await self.get_connector(connector_id)

        if connector.status != ConnectorStatus.CONNECTED:
            raise SyncError("Connector is not in a connected state")

        if not connector.oauth_token_encrypted:
            raise SyncError("Connector has no stored auth token")

        try:
            token = decrypt_token(connector.oauth_token_encrypted)
        except EncryptionError as exc:
            raise ConfigurationError(str(exc)) from exc

        impl = self._resolve_connector(connector.connector_type, token)

        # Read cursor from SyncState (fall back to legacy config for migration)
        sync_state = await self._get_or_create_sync_state(connector)
        cursor = sync_state.cursor or connector.config.get("sync_cursor")
        now = datetime.now(timezone.utc)

        connector.config = {
            **connector.config,
            "sync_queued_at": now.isoformat(),
            "message": "Sync in progress",
        }
        await self.session.commit()

        try:
            documents: list[NormalizedDocument] = []
            latest_ts: str | None = cursor
            previous_count = self._document_count(connector.config)

            if cursor is None:
                async for doc in impl.fetch_initial():
                    documents.append(doc)
                    if doc.created_at:
                        ts = str(doc.created_at.timestamp())
                        if latest_ts is None or ts > latest_ts:
                            latest_ts = ts
            else:
                async for doc in impl.fetch_incremental(cursor=cursor):
                    documents.append(doc)
                    if doc.created_at:
                        ts = str(doc.created_at.timestamp())
                        if latest_ts is None or ts > latest_ts:
                            latest_ts = ts

            # Persist documents into source_documents (upsert / dedupe)
            persisted = await self._persist_documents(
                connector.id, connector.connector_type, documents
            )

            # Hand off to ingestion pipeline
            ingestion = IngestionService(self.session)
            processed = await ingestion.process_connector_documents(
                workspace_id=connector.workspace_id,
                connector_id=connector.id,
                connector_type=connector.connector_type,
            )

            # Stamp completion time (not the start time captured in `now`)
            completed_at = datetime.now(timezone.utc)

            # Update SyncState
            sync_state.cursor = latest_ts
            sync_state.last_synced_at = completed_at
            if documents:
                sync_state.last_synced_item_id = documents[-1].external_id

            # Mark sync complete
            connector.last_sync_at = completed_at
            total_count = (
                persisted if cursor is None
                else previous_count + persisted
            )
            config = {
                k: v
                for k, v in connector.config.items()
                if k not in ("sync_cursor", "sync_queued_at")
            }
            connector.config = {
                **config,
                "document_count": total_count,
                "processed_count": processed,
                "message": f"Synced {persisted} documents, processed {processed}",
            }
        except AuthenticationError as exc:
            connector.status = ConnectorStatus.ERROR
            config = {
                **connector.config,
                "message": f"Auth failed: {exc}",
            }
            config.pop("sync_queued_at", None)
            connector.config = config
            await self.session.commit()
            await self.session.refresh(connector)
            raise SyncError(str(exc)) from exc
        except ConnectorError as exc:
            config = {
                **connector.config,
                "message": f"Sync failed: {exc}",
            }
            config.pop("sync_queued_at", None)
            connector.config = config
            await self.session.commit()
            await self.session.refresh(connector)
            raise SyncError(str(exc)) from exc

        await self.session.commit()
        await self.session.refresh(connector)
        return connector

    def _resolve_connector(
        self, connector_type: ConnectorType, token: str
    ) -> BaseConnector:
        """Return the concrete connector implementation for the given type."""
        if connector_type == ConnectorType.SLACK:
            return SlackConnector(token)
        if connector_type == ConnectorType.NOTION:
            return NotionConnector(token)
        raise SyncError(f"No connector implementation for {connector_type.value}")

    async def disconnect(self, connector_id: UUID) -> None:
        connector = await self.get_connector(connector_id)
        connector.status = ConnectorStatus.DISCONNECTED
        connector.oauth_token_encrypted = None
        await self.session.commit()

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

    @staticmethod
    def _document_count(config: dict) -> int:
        raw_value = config.get("document_count", 0)
        try:
            return int(raw_value or 0)
        except (TypeError, ValueError):
            return 0

    async def _get_or_create_sync_state(self, connector: Connector) -> SyncState:
        """Return the existing SyncState for a connector, or create one."""
        sync_state = await self.session.scalar(
            select(SyncState).where(SyncState.connector_id == connector.id)
        )
        if sync_state is None:
            sync_state = SyncState(connector_id=connector.id)
            self.session.add(sync_state)
            await self.session.flush()
        return sync_state

    async def _persist_documents(
        self,
        connector_id: UUID,
        connector_type: ConnectorType,
        documents: list[NormalizedDocument],
    ) -> int:
        """Upsert NormalizedDocuments into source_documents.

        Deduplicates on (connector_id, external_id).  On conflict the
        content, author, source_url, metadata, and created_at_source are
        updated so re-syncs pick up edits.

        Returns the number of **newly inserted** rows (not updates).
        Uses the PostgreSQL xmax trick: after an upsert, xmax = 0 means
        the row was freshly inserted; xmax != 0 means it was updated.
        """
        if not documents:
            return 0

        rows = [
            {
                "connector_id": connector_id,
                "connector_type": connector_type.value,
                "external_id": doc.external_id,
                "content": doc.content,
                "author": doc.author,
                "source_url": doc.source_url,
                "created_at_source": doc.created_at,
                "metadata": doc.metadata or {},
            }
            for doc in documents
        ]

        stmt = pg_insert(SourceDocument.__table__).values(rows)
        sd = SourceDocument.__table__.c
        stmt = stmt.on_conflict_do_update(
            index_elements=["connector_id", "external_id"],
            set_={
                "content": stmt.excluded.content,
                "author": stmt.excluded.author,
                "source_url": stmt.excluded.source_url,
                "created_at_source": stmt.excluded.created_at_source,
                "metadata": stmt.excluded.metadata,
                # Only reset processed_at when content actually changed;
                # unchanged pages keep their processed_at and skip
                # reprocessing in _select_unprocessed.
                "processed_at": case(
                    (sd.content != stmt.excluded.content, None),
                    else_=sd.processed_at,
                ),
            },
        )
        stmt = stmt.returning(literal_column("(xmax = 0)").label("inserted"))
        result = await self.session.execute(stmt)
        return sum(1 for row in result if row.inserted)
