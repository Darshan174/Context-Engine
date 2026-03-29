"""Service layer for connector management."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

import httpx
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.connector import Connector, ConnectorStatus
from app.models.source import ConnectorType
from app.models.user import Workspace
from app.utils.crypto import EncryptionError, encrypt_token


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
        connector = await self.get_connector(connector_id)
        connector.config = {
            **connector.config,
            "sync_queued_at": datetime.now(timezone.utc).isoformat(),
            "message": "Sync queued (placeholder)",
        }
        await self.session.commit()
        await self.session.refresh(connector)
        return connector

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
            resp = await http.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.slack_client_id,
                    "client_secret": settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": settings.slack_redirect_uri or "",
                },
            )

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
