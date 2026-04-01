"""Tests for background sync job infrastructure.

TestSyncJobDispatch  — API-level: POST /sync returns 202 + SyncJob row
TestSyncJobStatus    — GET /sync-status and GET /sync-jobs endpoints
TestSyncExecutor     — SyncExecutor.run() pipeline tests (no HTTP needed)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

import app.services.connector_service as connector_module
import app.services.sync_service as sync_module
from app.connectors.base import AuthenticationError, NormalizedDocument
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.job import SyncJob, SyncJobStatus
from app.models.source import ConnectorType, SourceDocument
from app.utils.crypto import encrypt_token

from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


def _make_connected_slack(workspace, encrypted_token):
    return Connector(
        workspace_id=workspace.id,
        connector_type=ConnectorType.SLACK,
        status=ConnectorStatus.CONNECTED,
        oauth_token_encrypted=encrypted_token,
        config={"team_name": "Test"},
    )


async def _mock_fetch_yielding(docs):
    for d in docs:
        yield d


# ── API dispatch tests ────────────────────────────────────────────


class TestSyncJobDispatch:
    def _setup(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

    async def test_sync_returns_202_with_job_id(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        mock_delay = MagicMock()
        mock_delay.return_value.id = "celery-task-abc"
        monkeypatch.setattr("app.tasks.sync.run_sync.delay", mock_delay)

        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert "id" not in body
        assert body["job_type"] == "sync"
        assert body["status"] == "pending"
        assert body["connector_id"] == str(conn_id)

        job = await db_session.scalar(
            select(SyncJob).where(SyncJob.connector_id == conn_id)
        )
        assert job is not None
        assert job.job_type == "sync"
        assert job.status == SyncJobStatus.PENDING
        await db_session.refresh(conn)
        assert conn.config["message"] == "Sync queued"
        assert conn.config["sync_queued_at"] is not None
        assert mock_delay.called

    async def test_double_sync_returns_409(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        # Pre-create a PENDING job
        existing = SyncJob(connector_id=conn.id, status=SyncJobStatus.PENDING)
        db_session.add(existing)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["detail"].lower()

    async def test_running_job_also_returns_409(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        existing = SyncJob(connector_id=conn.id, status=SyncJobStatus.RUNNING)
        db_session.add(existing)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 409

    async def test_completed_job_allows_new_sync(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        # A completed job should not block a new sync
        old_job = SyncJob(connector_id=conn.id, status=SyncJobStatus.COMPLETED)
        db_session.add(old_job)
        await db_session.flush()

        mock_delay = MagicMock()
        mock_delay.return_value.id = "celery-new"
        monkeypatch.setattr("app.tasks.sync.run_sync.delay", mock_delay)

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 202

    async def test_dispatch_failure_marks_job_failed(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id  # capture before expire_all

        monkeypatch.setattr(
            "app.tasks.sync.run_sync.delay",
            MagicMock(side_effect=Exception("Redis unreachable")),
        )

        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 502

        db_session.expire_all()
        job = await db_session.scalar(
            select(SyncJob).where(SyncJob.connector_id == conn_id)
        )
        assert job is not None
        assert job.status == SyncJobStatus.FAILED
        assert job.error_type == "DispatchError"

    async def test_sync_disconnected_connector_returns_502(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.DISCONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 502
        assert "not in a connected state" in resp.json()["detail"]

    async def test_sync_missing_connector_returns_404(self, client):
        resp = await client.post(f"/api/connectors/{uuid4()}/sync")
        assert resp.status_code == 404


# ── Status / list endpoints ───────────────────────────────────────


class TestSyncJobStatus:
    async def test_sync_status_returns_latest_job(
        self, client, workspace, db_session
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        job = SyncJob(
            connector_id=conn.id,
            status=SyncJobStatus.COMPLETED,
            result_metadata={"documents_fetched": 5},
        )
        db_session.add(job)
        await db_session.flush()

        resp = await client.get(f"/api/connectors/{conn.id}/sync-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == str(job.id)
        assert "id" not in body
        assert body["job_type"] == "sync"
        assert body["status"] == "completed"
        assert body["result_metadata"]["documents_fetched"] == 5

    async def test_sync_status_no_jobs_returns_404(
        self, client, workspace, db_session
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.get(f"/api/connectors/{conn.id}/sync-status")
        assert resp.status_code == 404

    async def test_sync_status_failed_job_includes_error(
        self, client, workspace, db_session
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.ERROR,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        job = SyncJob(
            connector_id=conn.id,
            status=SyncJobStatus.FAILED,
            error_type="AuthenticationError",
            error_message="token_revoked",
        )
        db_session.add(job)
        await db_session.flush()

        resp = await client.get(f"/api/connectors/{conn.id}/sync-status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_type"] == "AuthenticationError"
        assert body["error_message"] == "token_revoked"

    async def test_sync_jobs_list_returns_most_recent_first(
        self, client, workspace, db_session
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        for i in range(3):
            db_session.add(SyncJob(connector_id=conn.id, status=SyncJobStatus.COMPLETED))
        await db_session.flush()

        resp = await client.get(f"/api/connectors/{conn.id}/sync-jobs")
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) == 3
        # Each should have required fields
        for j in jobs:
            assert "job_id" in j
            assert "id" not in j
            assert j["job_type"] == "sync"
            assert j["status"] == "completed"

    async def test_sync_jobs_missing_connector_returns_404(self, client):
        resp = await client.get(f"/api/connectors/{uuid4()}/sync-jobs")
        assert resp.status_code == 404


# ── SyncExecutor pipeline tests ───────────────────────────────────


class TestSyncExecutor:
    """Direct tests of SyncExecutor.run() — no HTTP client needed.

    These replace the old TestSyncConnector tests that called POST /sync
    and tested the inline pipeline.  Monkeypatching _resolve_connector
    on SyncExecutor keeps the mock pattern identical to the old approach.
    """

    def _setup(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

    def _mock_executor_connector(self, monkeypatch, mock_connector):
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

    async def test_initial_sync_fetches_and_persists(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        docs = [
            NormalizedDocument(
                external_id="C1:1234.5",
                content="Hello world",
                author="U1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:1234.6",
                content="Another message",
                author="U2",
                created_at=datetime(2026, 3, 29, 11, 0, tzinfo=timezone.utc),
            ),
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(docs)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        result = await SyncExecutor(db_session).run(conn, "xoxb-test")

        assert result.documents_fetched == 2
        assert result.documents_persisted == 2
        assert result.sync_mode == "initial"

        await db_session.refresh(conn)
        assert conn.config["document_count"] == 2
        assert "2 new documents" in conn.config["message"]
        assert conn.config["sync_mode"] == "initial"
        assert conn.last_sync_at is not None

    async def test_incremental_sync_uses_cursor(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        ss = SyncState(connector_id=conn.id, cursor="1711699200.0")
        db_session.add(ss)
        await db_session.flush()

        calls = []

        async def _track_incremental(cursor=None):
            calls.append(cursor)
            return
            yield  # noqa: E702

        mock_conn = AsyncMock()
        mock_conn.fetch_incremental = _track_incremental
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        result = await SyncExecutor(db_session).run(conn, "xoxb-test")

        assert result.sync_mode == "incremental"
        assert calls == ["1711699200.0"]

    async def test_sync_persists_source_documents(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        docs = [
            NormalizedDocument(
                external_id="C1:1001.0",
                content="Hello from persistence test",
                author="Alice",
                source_url="https://slack.com/archives/C1/p10010",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "general"},
            ),
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(docs)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        rows = list(await db_session.scalars(
            select(SourceDocument).where(SourceDocument.connector_type == ConnectorType.SLACK)
        ))
        assert len(rows) == 1
        assert rows[0].content == "Hello from persistence test"
        assert rows[0].author == "Alice"
        assert rows[0].metadata_json["channel_name"] == "general"

    async def test_sync_deduplicates_on_resync(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        original = [NormalizedDocument(
            external_id="C1:dup.1",
            content="Original content",
            author="Alice",
            created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
        )]
        updated = [
            NormalizedDocument(
                external_id="C1:dup.1",
                content="Edited content",
                author="Alice (edited)",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:dup.2",
                content="Brand new",
                author="Bob",
                created_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(original)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        # Reset cursor so second run is also initial
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        ss.cursor = None
        await db_session.flush()

        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(updated)
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        db_session.expire_all()
        rows = list(await db_session.scalars(
            select(SourceDocument)
            .where(SourceDocument.connector_type == ConnectorType.SLACK)
            .order_by(SourceDocument.external_id)
        ))
        assert len(rows) == 2
        assert rows[0].content == "Edited content"

    async def test_sync_creates_and_updates_sync_state(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        docs = [NormalizedDocument(
            external_id="C1:ss.1",
            content="First message",
            author="U1",
            created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
        )]
        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(docs)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert ss is not None
        assert ss.cursor is not None
        assert ss.last_synced_item_id == "C1:ss.1"

    async def test_auth_failure_marks_connector_error(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-revoked")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        async def _raise_auth():
            raise AuthenticationError("token_revoked")
            yield  # noqa: E702

        mock_conn = AsyncMock()
        mock_conn.fetch_initial = _raise_auth
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor, SyncError
        with pytest.raises(SyncError, match="token_revoked"):
            await SyncExecutor(db_session).run(conn, "xoxb-revoked")

        await db_session.refresh(conn)
        assert conn.status == ConnectorStatus.ERROR
        assert conn.config["last_error"]["error_type"] == "AuthenticationError"
        assert "failed_at" in conn.config["last_error"]

    async def test_incremental_accumulates_document_count(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={"document_count": 5, "team_name": "Test"},
        )
        db_session.add(conn)
        await db_session.flush()
        ss = SyncState(connector_id=conn.id, cursor="1711699200.0")
        db_session.add(ss)
        await db_session.flush()

        new_docs = [
            NormalizedDocument(
                external_id="C1:inc.1",
                content="New msg",
                author="U1",
                created_at=datetime(2026, 3, 30, 10, 0, tzinfo=timezone.utc),
            ),
        ]
        mock_conn = AsyncMock()
        mock_conn.fetch_incremental = lambda cursor=None: _mock_fetch_yielding(new_docs)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        await db_session.refresh(conn)
        assert conn.config["document_count"] == 6

    async def test_total_processed_count_is_cumulative(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        batch1 = [NormalizedDocument(
            external_id="C1:cum.1",
            content="decision: ship v1",
            author="U1",
            created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            metadata={"channel_name": "product"},
        )]
        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding(batch1)
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")
        await db_session.refresh(conn)
        first_total = conn.config["total_processed_count"]

        batch2 = [NormalizedDocument(
            external_id="C1:cum.2",
            content="blocker: waiting on design",
            author="U2",
            created_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            metadata={"channel_name": "product"},
        )]
        mock_conn.fetch_incremental = lambda cursor=None: _mock_fetch_yielding(batch2)
        await SyncExecutor(db_session).run(conn, "xoxb-test")
        await db_session.refresh(conn)
        second_total = conn.config["total_processed_count"]

        assert second_total >= first_total

    async def test_legacy_cursor_in_config_migrates_to_sync_state(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={"sync_cursor": "1711699200.0", "team_name": "Test"},
        )
        db_session.add(conn)
        await db_session.flush()

        mock_conn = AsyncMock()
        mock_conn.fetch_incremental = lambda cursor=None: _mock_fetch_yielding([])
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "xoxb-test")

        await db_session.refresh(conn)
        assert "sync_cursor" not in conn.config
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert ss.cursor == "1711699200.0"

    async def test_notion_sync_sets_sync_mode_note(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("ntn_test_token")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        mock_conn = AsyncMock()
        mock_conn.fetch_initial = lambda: _mock_fetch_yielding([])
        self._mock_executor_connector(monkeypatch, mock_conn)

        from app.services.sync_service import SyncExecutor
        await SyncExecutor(db_session).run(conn, "ntn_test_token")

        await db_session.refresh(conn)
        assert "sync_mode_note" in conn.config
        assert "Notion API limitation" in conn.config["sync_mode_note"]
