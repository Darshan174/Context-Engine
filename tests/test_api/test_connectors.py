"""Tests for connector management endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select

import app.services.connector_service as connector_module
from app.models.connector import Connector, ConnectorStatus
from app.models.source import ConnectorType
from app.utils.crypto import decrypt_token, encrypt_token


# ── List / Sync / Disconnect (unchanged from Phase 2a) ────────────


class TestListConnectors:
    async def test_list_empty(self, client, workspace):
        resp = await client.get(
            "/api/connectors", params={"workspace_id": str(workspace.id)}
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_connected_slack(self, client, workspace, db_session):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={"document_count": 42},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.get(
            "/api/connectors", params={"workspace_id": str(workspace.id)}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["connector_type"] == "slack"
        assert body[0]["status"] == "connected"
        assert body[0]["config"]["document_count"] == 42
        assert body[0]["workspace_id"] == str(workspace.id)

    async def test_list_missing_workspace_returns_404(self, client):
        resp = await client.get(
            "/api/connectors", params={"workspace_id": str(uuid4())}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Workspace not found"


class TestSyncConnector:
    async def test_sync_queues_without_updating_last_sync_at(self, client, workspace, db_session):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "queued"
        assert body["last_sync_at"] is None
        assert "placeholder" in body["message"].lower()

        await db_session.refresh(conn)
        assert "sync_queued_at" in conn.config

    async def test_sync_missing_connector_returns_404(self, client):
        resp = await client.post(f"/api/connectors/{uuid4()}/sync")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Connector not found"


class TestDisconnectConnector:
    async def test_disconnect_clears_token_and_marks_disconnected(
        self, client, workspace, db_session
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted="enc-token-abc",
            config={"document_count": 10},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.delete(f"/api/connectors/{conn.id}")
        assert resp.status_code == 204

        await db_session.refresh(conn)
        assert conn.status == ConnectorStatus.DISCONNECTED
        assert conn.oauth_token_encrypted is None

    async def test_disconnect_missing_connector_returns_404(self, client):
        resp = await client.delete(f"/api/connectors/{uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Connector not found"


# ── Slack install (with Redis state) ──────────────────────────────


class _FakeRedis:
    """Minimal Redis stub for testing OAuth state storage."""

    def __init__(self):
        self.store: dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)

    async def aclose(self):
        pass


class TestSlackInstall:
    async def test_redirect_when_configured(self, client, workspace, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", "secret")
        monkeypatch.setattr(
            connector_module.settings,
            "slack_redirect_uri",
            "https://example.com/callback",
        )

        fake_redis = _FakeRedis()
        monkeypatch.setattr(
            connector_module.aioredis, "from_url", lambda *a, **kw: fake_redis
        )

        resp = await client.get(
            "/api/connectors/slack/install",
            params={"workspace_id": str(workspace.id)},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "https://slack.com/oauth/v2/authorize" in location
        assert "client_id=xoxb-fake" in location

        # State was persisted in Redis
        assert len(fake_redis.store) == 1
        stored_ws_id = list(fake_redis.store.values())[0]
        assert stored_ws_id == str(workspace.id)

    async def test_501_when_not_configured(self, client, workspace, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "slack_client_id", None)
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", None)

        resp = await client.get(
            "/api/connectors/slack/install",
            params={"workspace_id": str(workspace.id)},
        )
        assert resp.status_code == 501
        assert "SLACK_CLIENT_ID" in resp.json()["detail"]

    async def test_501_when_client_secret_missing(self, client, workspace, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", None)

        resp = await client.get(
            "/api/connectors/slack/install",
            params={"workspace_id": str(workspace.id)},
        )
        assert resp.status_code == 501
        assert "SLACK_CLIENT_SECRET" in resp.json()["detail"]

    async def test_missing_workspace_returns_404(self, client, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", "secret")

        resp = await client.get(
            "/api/connectors/slack/install",
            params={"workspace_id": str(uuid4())},
        )
        assert resp.status_code == 404


# ── Slack OAuth callback ──────────────────────────────────────────


class TestSlackCallback:
    """Tests for GET /api/connectors/slack/callback.

    We patch _exchange_slack_code at the service layer so we never hit
    the real Slack API, and use _FakeRedis for state validation.
    """

    def _setup_monkeypatch(self, monkeypatch, fake_redis):
        """Common monkeypatch setup for callback tests."""
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", "secret")
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        monkeypatch.setattr(
            connector_module.aioredis, "from_url", lambda *a, **kw: fake_redis
        )

    async def test_callback_with_slack_error(self, client):
        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"error": "access_denied"},
        )
        assert resp.status_code == 502
        assert "access_denied" in resp.json()["detail"]

    async def test_callback_with_missing_state(self, client):
        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "some-code"},
        )
        assert resp.status_code == 400
        assert "state" in resp.json()["detail"].lower()

    async def test_callback_with_invalid_state(self, client, monkeypatch):
        fake_redis = _FakeRedis()
        self._setup_monkeypatch(monkeypatch, fake_redis)

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "some-code", "state": "bogus-state"},
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()

    async def test_successful_callback_creates_connector(
        self, client, workspace, db_session, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup_monkeypatch(monkeypatch, fake_redis)

        # Simulate state that install endpoint would have stored
        state = f"{workspace.id}:testnonce123"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        # Mock the Slack token exchange
        mock_exchange = AsyncMock(return_value={
            "ok": True,
            "access_token": "xoxb-real-token-value",
            "scope": "channels:history,channels:read",
            "team": {"id": "T12345", "name": "Test Team"},
            "authed_user": {"id": "U99999"},
        })
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_slack_code",
            mock_exchange,
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "slack-auth-code", "state": state},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connector_type"] == "slack"
        assert body["status"] == "connected"
        assert body["workspace_id"] == str(workspace.id)
        assert body["config"]["team_name"] == "Test Team"

        # State was consumed (deleted from Redis)
        assert state not in fake_redis.store

        # Token is stored encrypted, not plaintext
        connector = await db_session.scalar(
            select(Connector).where(Connector.id == body["id"])
        )
        assert connector.oauth_token_encrypted is not None
        assert connector.oauth_token_encrypted != "xoxb-real-token-value"
        assert decrypt_token(connector.oauth_token_encrypted) == "xoxb-real-token-value"

    async def test_successful_callback_updates_existing_connector(
        self, client, workspace, db_session, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup_monkeypatch(monkeypatch, fake_redis)

        # Pre-create a disconnected Slack connector with operational metadata
        existing = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.DISCONNECTED,
            oauth_token_encrypted=None,
            config={"document_count": 150, "sync_queued_at": "2026-03-28T12:00:00"},
        )
        db_session.add(existing)
        await db_session.flush()
        existing_id = existing.id

        state = f"{workspace.id}:updatenonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        mock_exchange = AsyncMock(return_value={
            "ok": True,
            "access_token": "xoxb-new-token",
            "scope": "channels:history",
            "team": {"id": "T12345", "name": "Reconnected Team"},
            "authed_user": {"id": "U11111"},
        })
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_slack_code",
            mock_exchange,
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "new-code", "state": state},
        )
        assert resp.status_code == 200
        body = resp.json()

        # Same connector row was updated, not duplicated
        assert body["id"] == str(existing_id)
        assert body["status"] == "connected"
        assert body["config"]["team_name"] == "Reconnected Team"

        # Existing operational fields preserved (merge, not replace)
        assert body["config"]["document_count"] == 150
        assert body["config"]["sync_queued_at"] == "2026-03-28T12:00:00"

        await db_session.refresh(existing)
        assert decrypt_token(existing.oauth_token_encrypted) == "xoxb-new-token"

    async def test_callback_with_failed_token_exchange(
        self, client, workspace, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup_monkeypatch(monkeypatch, fake_redis)

        state = f"{workspace.id}:failnonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        mock_exchange = AsyncMock(
            side_effect=connector_module.OAuthError("Slack token exchange failed: invalid_code")
        )
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_slack_code",
            mock_exchange,
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "bad-code", "state": state},
        )
        assert resp.status_code == 502
        assert "invalid_code" in resp.json()["detail"]

    async def test_callback_with_missing_encryption_key(
        self, client, workspace, monkeypatch
    ):
        fake_redis = _FakeRedis()
        # Set up everything EXCEPT encryption_key
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", "secret")
        monkeypatch.setattr(connector_module.settings, "encryption_key", None)
        monkeypatch.setattr(
            connector_module.aioredis, "from_url", lambda *a, **kw: fake_redis
        )

        state = f"{workspace.id}:nokeynonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        mock_exchange = AsyncMock(return_value={
            "ok": True,
            "access_token": "xoxb-token",
            "team": {"id": "T1", "name": "T"},
            "authed_user": {"id": "U1"},
        })
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_slack_code",
            mock_exchange,
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "code", "state": state},
        )
        assert resp.status_code == 501
        assert "ENCRYPTION_KEY" in resp.json()["detail"]

    async def test_callback_with_malformed_encryption_key(
        self, client, workspace, monkeypatch
    ):
        fake_redis = _FakeRedis()
        monkeypatch.setattr(connector_module.settings, "slack_client_id", "xoxb-fake")
        monkeypatch.setattr(connector_module.settings, "slack_client_secret", "secret")
        monkeypatch.setattr(connector_module.settings, "encryption_key", "not-a-valid-fernet-key")
        monkeypatch.setattr(
            connector_module.aioredis, "from_url", lambda *a, **kw: fake_redis
        )

        state = f"{workspace.id}:badkeynonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        mock_exchange = AsyncMock(return_value={
            "ok": True,
            "access_token": "xoxb-token",
            "team": {"id": "T1", "name": "T"},
            "authed_user": {"id": "U1"},
        })
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_slack_code",
            mock_exchange,
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "code", "state": state},
        )
        assert resp.status_code == 501
        assert "malformed" in resp.json()["detail"].lower()


# ── Token encryption ──────────────────────────────────────────────

# Generate a stable test key (valid Fernet key)
from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


class TestTokenEncryption:
    def test_encrypt_decrypt_roundtrip(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

        ciphertext = encrypt_token("xoxb-secret-token")
        assert ciphertext != "xoxb-secret-token"
        assert decrypt_token(ciphertext) == "xoxb-secret-token"

    def test_encrypt_fails_without_key(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", None)

        import pytest
        from app.utils.crypto import EncryptionError

        with pytest.raises(EncryptionError, match="ENCRYPTION_KEY"):
            encrypt_token("something")
