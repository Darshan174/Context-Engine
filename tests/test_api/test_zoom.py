"""Tests for the Zoom transcript connector path."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

import app.services.connector_service as connector_module
import app.services.sync_service as sync_module
from app.connectors.base import AuthenticationError, NormalizedDocument, RateLimitError
from app.connectors.zoom import ZoomConnector
from app.models.connector import Connector, ConnectorStatus
from app.models.knowledge import Component, KnowledgeModel
from app.models.source import ConnectorType, SourceDocument
from app.services.sync_service import SyncError as SyncExecutorError, SyncExecutor
from app.utils.crypto import decrypt_token, encrypt_token

from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value

    async def getdel(self, key: str) -> str | None:
        return self.store.pop(key, None)

    async def aclose(self):
        pass


def _make_connected_zoom(workspace, encrypted_token):
    return Connector(
        workspace_id=workspace.id,
        connector_type=ConnectorType.ZOOM,
        status=ConnectorStatus.CONNECTED,
        oauth_token_encrypted=encrypted_token,
        config={
            "ingestion_mode": "transcripts_only",
            "source_focus": "meeting_transcripts",
        },
    )


async def _mock_zoom_fetch(documents):
    for document in documents:
        yield document


def _signed_zoom_webhook_request(
    payload: dict,
    *,
    secret: str,
    timestamp: str | None = None,
) -> tuple[bytes, dict[str, str]]:
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    request_timestamp = timestamp or str(int(datetime.now(timezone.utc).timestamp()))
    signature = "v0=" + hmac.new(
        secret.encode(),
        b"v0:" + request_timestamp.encode() + b":" + raw_body,
        hashlib.sha256,
    ).hexdigest()
    return raw_body, {
        "content-type": "application/json",
        "x-zm-request-timestamp": request_timestamp,
        "x-zm-signature": signature,
    }


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        *,
        json_body: dict | None = None,
        text: str = "",
        headers: dict[str, str] | None = None,
        json_error: Exception | None = None,
    ):
        self.status_code = status_code
        self._json_body = json_body or {}
        self.text = text
        self.headers = headers or {}
        self._json_error = json_error

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_body


class _FakeZoomHttpClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestZoomNormalizedDocumentMapping:
    def test_maps_zoom_transcript_to_normalized_document(self):
        meeting = {
            "id": 987654321,
            "uuid": "zoom-meeting-uuid",
            "topic": "Weekly Product Review",
            "host_email": "founder@example.com",
            "participants": [
                {"name": "Founder"},
                {"email": "ops@example.com"},
            ],
            "start_time": "2026-03-31T10:00:00Z",
            "share_url": "https://zoom.us/rec/share/meeting-link",
        }
        transcript_file = {
            "id": "transcript-file-1",
            "file_type": "TRANSCRIPT",
            "file_extension": "VTT",
            "recording_type": "audio_transcript",
            "recording_start": "2026-03-31T10:00:05Z",
            "recording_end": "2026-03-31T10:15:00Z",
            "play_url": "https://zoom.us/rec/play/transcript-file-1",
            "download_url": "https://zoom.us/rec/download/transcript-file-1",
        }
        transcript_text = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:03.000\n"
            "Founder: decision: Launch the pricing page next Tuesday.\n\n"
            "00:00:03.000 --> 00:00:06.000\n"
            "Ops: blocker: waiting on legal approval.\n"
        )

        document = ZoomConnector._to_normalized_document(
            meeting,
            transcript_file,
            transcript_text,
        )

        assert document is not None
        assert document.external_id == "zoom:987654321:transcript-file-1"
        assert document.author == "founder@example.com"
        assert document.source_url == "https://zoom.us/rec/play/transcript-file-1"
        assert document.created_at == datetime(2026, 3, 31, 10, 0, 5, tzinfo=timezone.utc)
        assert "Meeting: Weekly Product Review" in document.content
        assert "Host: founder@example.com" in document.content
        assert "Participants: Founder, ops@example.com" in document.content
        assert "Founder: decision: Launch the pricing page next Tuesday." in document.content
        assert "Ops: blocker: waiting on legal approval." in document.content
        assert "WEBVTT" not in document.content
        assert document.metadata["meeting_id"] == 987654321
        assert document.metadata["meeting_uuid"] == "zoom-meeting-uuid"
        assert document.metadata["meeting_topic"] == "Weekly Product Review"
        assert document.metadata["host"] == "founder@example.com"
        assert document.metadata["participants"] == ["Founder", "ops@example.com"]
        assert document.metadata["source_type"] == "zoom_transcript"
        assert document.metadata["recording_date"] == "2026-03-31"


class TestZoomConnectorFetch:
    async def test_fetch_initial_downloads_and_maps_transcripts(self):
        connector = ZoomConnector("zoom-test-token")
        meeting = {
            "id": 987654321,
            "uuid": "zoom-meeting-uuid",
            "topic": "Weekly Product Review",
            "host_email": "founder@example.com",
            "participants": [{"name": "Founder"}],
            "start_time": "2026-03-31T10:00:00Z",
            "recording_files": [
                {
                    "id": "transcript-file-1",
                    "file_type": "TRANSCRIPT",
                    "file_extension": "VTT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T10:00:05Z",
                    "download_url": "https://zoom.us/rec/download/transcript-file-1",
                },
                {
                    "id": "video-file-1",
                    "file_type": "MP4",
                    "file_extension": "MP4",
                    "recording_type": "shared_screen_with_speaker_view",
                    "download_url": "https://zoom.us/rec/download/video-file-1",
                },
            ],
        }
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(
                json_body={"meetings": [meeting], "next_page_token": ""},
            ),
            _FakeResponse(
                text=(
                    "WEBVTT\n\n"
                    "00:00:00.000 --> 00:00:02.000\n"
                    "Founder: decision: Launch next Tuesday.\n"
                ),
            ),
        ])
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        documents = [doc async for doc in connector.fetch_initial()]

        assert len(documents) == 1
        assert documents[0].external_id == "zoom:987654321:transcript-file-1"
        assert documents[0].metadata["meeting_topic"] == "Weekly Product Review"
        assert len(fake_http.calls) == 2
        assert fake_http.calls[0][0].endswith("/users/me/recordings")
        assert fake_http.calls[0][1] == {"page_size": 100}
        assert fake_http.calls[1][0] == "https://zoom.us/rec/download/transcript-file-1"

    async def test_fetch_incremental_filters_out_older_transcripts(self):
        connector = ZoomConnector("zoom-test-token")
        old_meeting = {
            "id": 1,
            "topic": "Old Meeting",
            "recording_files": [
                {
                    "id": "old-transcript",
                    "file_type": "TRANSCRIPT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T09:00:00Z",
                    "download_url": "https://zoom.us/rec/download/old-transcript",
                }
            ],
        }
        new_meeting = {
            "id": 2,
            "topic": "New Meeting",
            "recording_files": [
                {
                    "id": "new-transcript",
                    "file_type": "TRANSCRIPT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T11:00:00Z",
                    "download_url": "https://zoom.us/rec/download/new-transcript",
                }
            ],
        }
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(json_body={"meetings": [old_meeting, new_meeting], "next_page_token": ""}),
            _FakeResponse(
                text=(
                    "WEBVTT\n\n"
                    "00:00:00.000 --> 00:00:02.000\n"
                    "Host: decision: Ship it.\n"
                )
            ),
        ])
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        documents = [
            doc async for doc in connector.fetch_incremental(
                cursor=str(
                    datetime(2026, 3, 31, 10, 0, tzinfo=timezone.utc).timestamp()
                )
            )
        ]

        assert len(documents) == 1
        assert documents[0].external_id == "zoom:2:new-transcript"
        assert len(fake_http.calls) == 2
        assert fake_http.calls[0][1]["from"] == "2026-03-31"
        assert "to" in fake_http.calls[0][1]
        assert fake_http.calls[1][0] == "https://zoom.us/rec/download/new-transcript"

    async def test_fetch_incremental_uses_structured_cursor_tie_breaker(self):
        connector = ZoomConnector("zoom-test-token")
        meeting = {
            "id": 55,
            "topic": "Weekly Product Review",
            "recording_files": [
                {
                    "id": "aaa",
                    "file_type": "TRANSCRIPT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T10:00:00Z",
                    "download_url": "https://zoom.us/rec/download/aaa",
                },
                {
                    "id": "bbb",
                    "file_type": "TRANSCRIPT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T10:00:00Z",
                    "download_url": "https://zoom.us/rec/download/bbb",
                },
            ],
        }
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(json_body={"meetings": [meeting], "next_page_token": ""}),
            _FakeResponse(text="WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHost: decision: keep this.\n"),
        ])
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        cursor = json.dumps(
            {
                "recording_start": "2026-03-31T10:00:00+00:00",
                "external_id": "aaa",
            }
        )
        documents = [doc async for doc in connector.fetch_incremental(cursor=cursor)]

        assert len(documents) == 1
        assert documents[0].external_id == "zoom:55:bbb"
        assert fake_http.calls[1][0] == "https://zoom.us/rec/download/bbb"

    async def test_fetch_initial_skips_empty_transcripts(self):
        connector = ZoomConnector("zoom-test-token")
        meeting = {
            "id": 987654321,
            "topic": "Weekly Product Review",
            "recording_files": [
                {
                    "id": "transcript-file-1",
                    "file_type": "TRANSCRIPT",
                    "recording_type": "audio_transcript",
                    "recording_start": "2026-03-31T10:00:05Z",
                    "download_url": "https://zoom.us/rec/download/transcript-file-1",
                }
            ],
        }
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(json_body={"meetings": [meeting], "next_page_token": ""}),
            _FakeResponse(
                text=(
                    "WEBVTT\n\n"
                    "00:00:00.000 --> 00:00:02.000\n"
                )
            ),
        ])
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        documents = [doc async for doc in connector.fetch_initial()]

        assert documents == []

    async def test_zoom_get_raises_authentication_error(self):
        connector = ZoomConnector("zoom-test-token")
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(status_code=401, json_body={"code": 124}),
        ])

        with pytest.raises(AuthenticationError, match="Zoom auth failed"):
            await connector._zoom_get(fake_http, "/users/me/recordings")

    async def test_download_transcript_raises_rate_limit(self):
        connector = ZoomConnector("zoom-test-token")
        fake_http = _FakeZoomHttpClient([
            _FakeResponse(status_code=429, headers={"Retry-After": "7"}),
        ])

        with pytest.raises(RateLimitError) as exc_info:
            await connector._download_transcript(
                fake_http,
                {"download_url": "https://zoom.us/rec/download/transcript-file-1"},
            )

        assert exc_info.value.retry_after == 7.0


class TestZoomConnectorResolution:
    def test_resolve_returns_zoom_connector(self):
        executor = SyncExecutor.__new__(SyncExecutor)
        connector = executor._resolve_connector(ConnectorType.ZOOM, "zoom-test-token")
        assert isinstance(connector, ZoomConnector)

    def test_resolve_unknown_type_still_raises(self):
        import pytest

        executor = SyncExecutor.__new__(SyncExecutor)
        with pytest.raises(SyncExecutorError, match="No connector implementation"):
            executor._resolve_connector(ConnectorType.GDRIVE, "token")


class TestZoomConnect:
    async def test_connect_creates_connector(
        self, client, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

        response = await client.post(
            "/api/connectors/zoom/connect",
            json={
                "workspace_id": str(workspace.id),
                "token": "zoom_test_access_token",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["connector_type"] == "zoom"
        assert body["status"] == "connected"
        assert body["workspace_id"] == str(workspace.id)
        assert body["provider"] == "official_api"
        assert "polling-only" in body["provider_note"].lower()
        assert body["config"]["ingestion_mode"] == "transcripts_only"
        assert body["config"]["sync_delivery_mode"] == "polling_only"
        assert body["config"]["webhook_auto_sync"] is False

        connector = await db_session.scalar(
            select(Connector).where(Connector.id == body["id"])
        )
        assert connector is not None
        assert connector.oauth_token_encrypted is not None
        assert connector.oauth_token_encrypted != "zoom_test_access_token"
        assert decrypt_token(connector.oauth_token_encrypted) == "zoom_test_access_token"

    async def test_connect_blank_token_returns_422(
        self, client, workspace, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

        response = await client.post(
            "/api/connectors/zoom/connect",
            json={
                "workspace_id": str(workspace.id),
                "token": "   ",
            },
        )
        assert response.status_code == 422

    async def test_connect_missing_encryption_key_returns_501(
        self, client, workspace, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", None)

        response = await client.post(
            "/api/connectors/zoom/connect",
            json={
                "workspace_id": str(workspace.id),
                "token": "zoom_valid_token",
            },
        )
        assert response.status_code == 501


class TestZoomOAuth:
    def _setup(self, monkeypatch, fake_redis):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        monkeypatch.setattr(connector_module.settings, "zoom_client_id", "zoom-client")
        monkeypatch.setattr(connector_module.settings, "zoom_client_secret", "zoom-secret")
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_redirect_uri",
            "https://example.com/api/connectors/zoom/callback",
        )
        monkeypatch.setattr(
            connector_module.aioredis,
            "from_url",
            lambda *args, **kwargs: fake_redis,
        )

    async def test_install_redirects_to_zoom(self, client, workspace, monkeypatch):
        fake_redis = _FakeRedis()
        self._setup(monkeypatch, fake_redis)

        response = await client.get(
            "/api/connectors/zoom/install",
            params={"workspace_id": str(workspace.id)},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "zoom.us/oauth/authorize" in response.headers["location"]
        assert "client_id=zoom-client" in response.headers["location"]
        assert len(fake_redis.store) == 1

    async def test_install_returns_501_when_zoom_oauth_not_configured(
        self, client, workspace, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "zoom_client_id", None)
        monkeypatch.setattr(connector_module.settings, "zoom_client_secret", None)

        response = await client.get(
            "/api/connectors/zoom/install",
            params={"workspace_id": str(workspace.id)},
        )

        assert response.status_code == 501
        assert "ZOOM_CLIENT_ID" in response.json()["detail"]

    async def test_callback_with_zoom_error_returns_502(self, client):
        response = await client.get(
            "/api/connectors/zoom/callback",
            params={"error": "access_denied"},
        )
        assert response.status_code == 502
        assert "access_denied" in response.json()["detail"]

    async def test_callback_with_invalid_state_returns_400(
        self, client, workspace, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup(monkeypatch, fake_redis)

        response = await client.get(
            "/api/connectors/zoom/callback",
            params={"code": "zoom-code", "state": "bogus"},
        )
        assert response.status_code == 400

    async def test_callback_creates_connector_with_refresh_token(
        self, client, workspace, db_session, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup(monkeypatch, fake_redis)
        state = f"{workspace.id}:zoomnonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_exchange_zoom_code",
            AsyncMock(
                return_value={
                    "access_token": "zoom-access",
                    "refresh_token": "zoom-refresh",
                    "expires_in": 3600,
                    "scope": "recording:read:user",
                    "token_type": "bearer",
                }
            ),
        )

        response = await client.get(
            "/api/connectors/zoom/callback",
            params={"code": "zoom-code", "state": state},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connector_type"] == "zoom"
        assert body["status"] == "connected"
        assert body["config"]["auth_mode"] == "oauth"
        assert body["config"]["access_token_expires_at"] is not None
        assert body["config"]["sync_delivery_mode"] == "webhook_auto_sync"
        assert body["config"]["webhook_auto_sync"] is True
        assert "webhook-driven sync" in body["provider_note"].lower()

        connector = await db_session.scalar(
            select(Connector).where(Connector.id == body["id"])
        )
        assert connector is not None
        assert decrypt_token(connector.oauth_token_encrypted) == "zoom-access"
        assert decrypt_token(connector.refresh_token_encrypted) == "zoom-refresh"

    async def test_webhook_url_validation_returns_expected_signature(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )
        raw_body, headers = _signed_zoom_webhook_request(
            {
                "event": "endpoint.url_validation",
                "payload": {"plainToken": "challenge-token"},
            },
            secret="zoom-webhook-secret",
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 200
        expected = hmac.new(
            b"zoom-webhook-secret",
            b"challenge-token",
            hashlib.sha256,
        ).hexdigest()
        assert response.json() == {
            "plainToken": "challenge-token",
            "encryptedToken": expected,
        }

    async def test_webhook_rejects_invalid_signature(self, client, monkeypatch):
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )
        raw_body, headers = _signed_zoom_webhook_request(
            {
                "event": "recording.completed",
                "payload": {"account_id": "acct-123", "object": {"id": "123"}},
            },
            secret="zoom-webhook-secret",
        )
        headers["x-zm-signature"] = "v0=definitely-wrong"

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 401
        assert "verification failed" in response.json()["detail"].lower()

    async def test_webhook_rejects_stale_timestamp(self, client, monkeypatch):
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_tolerance_seconds",
            300,
        )
        stale_ts = str(
            int(
                (
                    datetime.now(timezone.utc) - timedelta(minutes=10)
                ).timestamp()
            )
        )
        raw_body, headers = _signed_zoom_webhook_request(
            {
                "event": "recording.completed",
                "payload": {"account_id": "acct-123", "object": {"id": "123"}},
            },
            secret="zoom-webhook-secret",
            timestamp=stale_ts,
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 401
        assert "tolerance window" in response.json()["detail"].lower()

    async def test_webhook_accepts_regular_events_with_valid_signature(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )
        raw_body, headers = _signed_zoom_webhook_request(
            {"event": "meeting.started", "payload": {"object": {"id": "123"}}},
            secret="zoom-webhook-secret",
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["accepted"] is True
        assert response.json()["queued_count"] == 0

    async def test_webhook_queues_sync_for_matching_zoom_connector(
        self, client, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )

        matching = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("zoom-access"),
            refresh_token_encrypted=encrypt_token("zoom-refresh"),
            config={
                "auth_mode": "oauth",
                "account_id": "acct-123",
                "ingestion_mode": "transcripts_only",
            },
        )
        other = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("other-access"),
            refresh_token_encrypted=encrypt_token("other-refresh"),
            config={
                "auth_mode": "oauth",
                "account_id": "acct-999",
                "ingestion_mode": "transcripts_only",
            },
        )
        db_session.add_all([matching, other])
        await db_session.flush()

        queued_ids: list[str] = []

        async def _fake_queue_sync(self, connector_id):
            queued_ids.append(str(connector_id))
            return SimpleNamespace(id=uuid4(), result_metadata={})

        monkeypatch.setattr(
            connector_module.ConnectorService,
            "queue_sync",
            _fake_queue_sync,
        )

        payload = {
            "event": "recording.completed",
            "event_ts": 1711926000,
            "payload": {
                "account_id": "acct-123",
                "object": {"id": "meeting-123"},
            },
        }
        raw_body, headers = _signed_zoom_webhook_request(
            payload,
            secret="zoom-webhook-secret",
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["queued_count"] == 1
        assert body["queued_connector_ids"] == [str(matching.id)]
        assert body["skipped_connector_ids"] == []
        assert body["reconciled_count"] == 0
        assert queued_ids == [str(matching.id)]
        assert matching.config["last_zoom_webhook_event"] == "recording.completed"

    async def test_webhook_deletion_reconciles_zoom_source_documents(
        self, client, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )

        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("zoom-access"),
            refresh_token_encrypted=encrypt_token("zoom-refresh"),
            config={
                "auth_mode": "oauth",
                "account_id": "acct-123",
                "ingestion_mode": "transcripts_only",
                "document_count": 1,
            },
        )
        db_session.add(connector)
        await db_session.flush()

        document = SourceDocument(
            connector_id=connector.id,
            connector_type=ConnectorType.ZOOM,
            external_id="zoom:987654321:transcript-file-1",
            content="Founder: decision: Launch next Tuesday.",
            author="founder@example.com",
            metadata_json={
                "meeting_id": 987654321,
                "meeting_topic": "Weekly Product Review",
                "transcript_file_id": "transcript-file-1",
                "source_type": "zoom_transcript",
            },
            processed_at=datetime(2026, 3, 31, 10, 5, tzinfo=timezone.utc),
        )
        db_session.add(document)
        await db_session.flush()

        model = KnowledgeModel(
            workspace_id=workspace.id,
            name="Zoom Insights",
        )
        db_session.add(model)
        await db_session.flush()

        component = Component(
            model_id=model.id,
            name="Decision in Weekly Product Review",
            value="Launch next Tuesday.",
            confidence=0.91,
        )
        db_session.add(component)
        await db_session.flush()

        from app.models.knowledge import ComponentSource

        db_session.add(
            ComponentSource(
                component_id=component.id,
                source_document_id=document.id,
                extraction_context="Zoom transcript extraction",
            )
        )
        await db_session.flush()

        payload = {
            "event": "recording.deleted",
            "event_ts": 1711926600,
            "payload": {
                "account_id": "acct-123",
                "object": {
                    "id": 987654321,
                    "recording_files": [{"id": "transcript-file-1"}],
                },
            },
        }
        raw_body, headers = _signed_zoom_webhook_request(
            payload,
            secret="zoom-webhook-secret",
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["queued_count"] == 0
        assert body["reconciled_count"] == 1
        assert body["reconciled_document_ids"] == [str(document.id)]

        await db_session.refresh(document)
        await db_session.refresh(component)
        await db_session.refresh(connector)
        assert document.deleted_at is not None
        assert document.metadata_json["lifecycle_state"] == "deleted"
        assert component.valid_to is not None
        assert connector.config["document_count"] == 0

    async def test_webhook_deletion_ignores_non_transcript_file_deletions(
        self, client, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        monkeypatch.setattr(
            connector_module.settings,
            "zoom_webhook_secret",
            "zoom-webhook-secret",
        )

        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("zoom-access"),
            refresh_token_encrypted=encrypt_token("zoom-refresh"),
            config={
                "auth_mode": "oauth",
                "account_id": "acct-123",
                "ingestion_mode": "transcripts_only",
                "document_count": 1,
            },
        )
        db_session.add(connector)
        await db_session.flush()

        document = SourceDocument(
            connector_id=connector.id,
            connector_type=ConnectorType.ZOOM,
            external_id="zoom:987654321:transcript-file-1",
            content="Founder: decision: Launch next Tuesday.",
            author="founder@example.com",
            metadata_json={
                "meeting_id": 987654321,
                "meeting_topic": "Weekly Product Review",
                "transcript_file_id": "transcript-file-1",
                "source_type": "zoom_transcript",
            },
            processed_at=datetime(2026, 3, 31, 10, 5, tzinfo=timezone.utc),
        )
        db_session.add(document)
        await db_session.flush()

        payload = {
            "event": "recording.deleted",
            "event_ts": 1711926600,
            "payload": {
                "account_id": "acct-123",
                "object": {
                    "id": 987654321,
                    "recording_files": [
                        {
                            "id": "video-file-1",
                            "file_type": "MP4",
                            "file_extension": "MP4",
                            "recording_type": "shared_screen_with_speaker_view",
                        }
                    ],
                },
            },
        }
        raw_body, headers = _signed_zoom_webhook_request(
            payload,
            secret="zoom-webhook-secret",
        )

        response = await client.post(
            "/api/connectors/zoom/webhook",
            content=raw_body,
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["reconciled_count"] == 0

        await db_session.refresh(document)
        await db_session.refresh(connector)
        assert document.deleted_at is None
        assert connector.config["document_count"] == 1

    async def test_refreshes_expired_zoom_token_before_sync(
        self, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)
        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("expired-access"),
            refresh_token_encrypted=encrypt_token("refresh-token"),
            config={
                "auth_mode": "oauth",
                "access_token_expires_at": "2026-03-31T00:00:00+00:00",
            },
        )
        db_session.add(connector)
        await db_session.flush()

        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_refresh_zoom_access_token",
            AsyncMock(
                return_value={
                    "access_token": "fresh-access",
                    "refresh_token": "fresh-refresh",
                    "expires_in": 3600,
                    "scope": "recording:read:user",
                    "token_type": "bearer",
                }
            ),
        )

        token = await connector_module.ConnectorService(
            db_session
        ).get_access_token_for_connector(connector)

        assert token == "fresh-access"
        assert decrypt_token(connector.oauth_token_encrypted) == "fresh-access"
        assert decrypt_token(connector.refresh_token_encrypted) == "fresh-refresh"


class TestZoomSync:
    def _setup(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

    async def test_zoom_sync_persists_transcript_source_documents(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("zoom_test_token")
        connector = _make_connected_zoom(workspace, token_enc)
        db_session.add(connector)
        await db_session.flush()
        connector_id = connector.id

        sample_docs = [
            NormalizedDocument(
                external_id="zoom:987654321:transcript-file-1",
                content=(
                    "Meeting: Weekly Product Review\n"
                    "Host: founder@example.com\n\n"
                    "Founder: decision: Launch next Tuesday.\n"
                    "Ops: blocker: waiting on legal approval."
                ),
                author="founder@example.com",
                source_url="https://zoom.us/rec/share/meeting-link",
                created_at=datetime(2026, 3, 31, 10, 0, tzinfo=timezone.utc),
                metadata={
                    "meeting_id": 987654321,
                    "meeting_topic": "Weekly Product Review",
                    "host": "founder@example.com",
                    "participants": ["Founder", "Ops"],
                    "recording_date": "2026-03-31",
                    "source_type": "zoom_transcript",
                },
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_zoom_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, connector_type, token: mock_connector,
        )

        await SyncExecutor(db_session).run(connector, "zoom_test_token")

        db_session.expire_all()
        rows = list(await db_session.scalars(
            select(SourceDocument).where(SourceDocument.connector_id == connector_id)
        ))
        assert len(rows) == 1
        assert rows[0].connector_type == ConnectorType.ZOOM
        assert rows[0].external_id == "zoom:987654321:transcript-file-1"
        assert rows[0].metadata_json["meeting_id"] == 987654321
        assert rows[0].metadata_json["meeting_topic"] == "Weekly Product Review"
        assert rows[0].metadata_json["host"] == "founder@example.com"
        assert rows[0].metadata_json["participants"] == ["Founder", "Ops"]
        assert rows[0].processed_at is not None

    async def test_zoom_sync_ingests_transcript_into_knowledge_graph(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("zoom_test_token")
        connector = _make_connected_zoom(workspace, token_enc)
        db_session.add(connector)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="zoom:555:transcript-file-2",
                content=(
                    "Meeting: Weekly Product Review\n"
                    "Host: founder@example.com\n\n"
                    "Founder: decision: Launch next Tuesday.\n"
                    "Ops: blocker: waiting on legal approval."
                ),
                author="founder@example.com",
                source_url="https://zoom.us/rec/share/meeting-link",
                created_at=datetime(2026, 3, 31, 10, 0, tzinfo=timezone.utc),
                metadata={
                    "meeting_id": 555,
                    "meeting_topic": "Weekly Product Review",
                    "host": "founder@example.com",
                    "participants": ["Founder", "Ops"],
                    "recording_date": "2026-03-31",
                    "source_type": "zoom_transcript",
                },
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_zoom_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, connector_type, token: mock_connector,
        )

        result = await SyncExecutor(db_session).run(connector, "zoom_test_token")

        assert result.documents_fetched == 1
        assert result.documents_persisted == 1
        assert result.documents_processed == 1
        assert result.connector_type == ConnectorType.ZOOM

        model = await db_session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace.id,
                KnowledgeModel.name == "Zoom Insights",
            )
        )
        assert model is not None

        components = list(await db_session.scalars(
            select(Component)
            .where(Component.model_id == model.id)
            .order_by(Component.name.asc())
        ))
        assert len(components) == 2
        assert {component.name for component in components} == {
            "Blocker in Weekly Product Review",
            "Decision in Weekly Product Review",
        }
        assert any("Launch next Tuesday" in component.value for component in components)
        assert any("waiting on legal approval" in component.value for component in components)

    async def test_zoom_sync_without_token_returns_502(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.ZOOM,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=None,
            config={"ingestion_mode": "transcripts_only"},
        )
        db_session.add(connector)
        await db_session.flush()

        response = await client.post(f"/api/connectors/{connector.id}/sync")
        assert response.status_code == 502
        assert "no stored auth token" in response.json()["detail"].lower()

    async def test_zoom_connect_missing_workspace_returns_404(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

        response = await client.post(
            "/api/connectors/zoom/connect",
            json={
                "workspace_id": str(uuid4()),
                "token": "zoom_test_access_token",
            },
        )
        assert response.status_code == 404
