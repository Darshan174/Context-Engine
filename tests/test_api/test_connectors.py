"""Tests for connector management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from sqlalchemy import select

import app.services.connector_service as connector_module
from app.connectors.base import NormalizedDocument
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.source import ConnectorType, SourceDocument
from app.utils.crypto import decrypt_token, encrypt_token

# Generate a stable test key (valid Fernet key) — used across callback & sync tests
from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


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
        assert body[0]["provider"] == "native"
        assert body[0]["provider_label"] == "Built in"

    async def test_list_missing_workspace_returns_404(self, client):
        resp = await client.get(
            "/api/connectors", params={"workspace_id": str(uuid4())}
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Workspace not found"


def _make_connected_slack(workspace, encrypted_token):
    """Helper to create a connected Slack connector row."""
    return Connector(
        workspace_id=workspace.id,
        connector_type=ConnectorType.SLACK,
        status=ConnectorStatus.CONNECTED,
        oauth_token_encrypted=encrypted_token,
        config={"team_name": "Test"},
    )


async def _mock_fetch_initial_yielding(docs):
    """Return an async generator that yields the given docs."""
    for d in docs:
        yield d


class TestSyncConnector:
    def _setup_encryption(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

    async def test_sync_runs_fetch_and_records_results(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        sample_docs = [
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

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(sample_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["last_sync_at"] is not None
        assert "2 documents" in body["message"]

        await db_session.refresh(conn)
        assert conn.config["document_count"] == 2
        assert "sync_cursor" not in conn.config  # cursor lives in SyncState now
        assert "sync_queued_at" not in conn.config

        # SyncState was created with cursor
        sync_state = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert sync_state is not None
        assert sync_state.cursor is not None
        assert sync_state.last_synced_at is not None

    async def test_sync_incremental_uses_cursor(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={"team_name": "Test"},
        )
        db_session.add(conn)
        await db_session.flush()

        # Cursor lives in SyncState
        ss = SyncState(connector_id=conn.id, cursor="1711699200.0")
        db_session.add(ss)
        await db_session.flush()

        mock_connector = AsyncMock()
        mock_connector.fetch_incremental = lambda cursor=None: _mock_fetch_initial_yielding([])
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert "0 documents" in resp.json()["message"]

    async def test_incremental_sync_accumulates_document_count(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={
                "document_count": 5,
                "team_name": "Test",
            },
        )
        db_session.add(conn)
        await db_session.flush()

        # Cursor in SyncState triggers incremental path
        ss = SyncState(connector_id=conn.id, cursor="1711699200.0")
        db_session.add(ss)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="C1:1234.7",
                content="New message",
                author="U3",
                created_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:1234.8",
                content="Another new message",
                author="U4",
                created_at=datetime(2026, 3, 29, 12, 5, tzinfo=timezone.utc),
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_incremental = lambda cursor=None: _mock_fetch_initial_yielding(sample_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        assert "2 documents" in resp.json()["message"]

        await db_session.refresh(conn)
        assert conn.config["document_count"] == 7
        assert "sync_queued_at" not in conn.config

    async def test_sync_disconnected_connector_returns_502(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup_encryption(monkeypatch)
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

    async def test_sync_auth_failure_marks_connector_error(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-revoked")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        from app.connectors.base import AuthenticationError

        async def _raise_auth():
            raise AuthenticationError("Slack auth failed: token_revoked")
            yield  # make it an async generator  # noqa: E702

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = _raise_auth
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 502
        assert "token_revoked" in resp.json()["detail"]

        await db_session.refresh(conn)
        assert conn.status == ConnectorStatus.ERROR

    async def test_sync_missing_connector_returns_404(self, client):
        resp = await client.post(f"/api/connectors/{uuid4()}/sync")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Connector not found"

    # ── Persistence & dedupe tests ────────────────────────────────

    async def test_sync_persists_source_documents(
        self, client, workspace, db_session, monkeypatch
    ):
        """Initial sync writes NormalizedDocuments into source_documents table."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="C1:1001.0",
                content="Hello from persistence test",
                author="Alice",
                source_url="https://slack.com/archives/C1/p10010",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "general"},
            ),
            NormalizedDocument(
                external_id="C1:1002.0",
                content="Second message",
                author="Bob",
                created_at=datetime(2026, 3, 29, 11, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(sample_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        # Verify rows in source_documents
        rows = list(await db_session.scalars(
            select(SourceDocument)
            .where(SourceDocument.connector_type == ConnectorType.SLACK)
            .order_by(SourceDocument.external_id)
        ))
        assert len(rows) == 2
        assert rows[0].external_id == "C1:1001.0"
        assert rows[0].content == "Hello from persistence test"
        assert rows[0].author == "Alice"
        assert rows[0].source_url == "https://slack.com/archives/C1/p10010"
        assert rows[0].created_at_source == datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc)
        assert rows[0].metadata_json["channel_name"] == "general"
        assert rows[1].external_id == "C1:1002.0"
        assert rows[1].content == "Second message"

    async def test_sync_deduplicates_on_resync(
        self, client, workspace, db_session, monkeypatch
    ):
        """Re-syncing the same external_ids updates content, doesn't duplicate rows."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        original_docs = [
            NormalizedDocument(
                external_id="C1:dedup.1",
                content="Original content",
                author="Alice",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
        ]
        updated_docs = [
            NormalizedDocument(
                external_id="C1:dedup.1",
                content="Edited content",
                author="Alice (edited)",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:dedup.2",
                content="Brand new message",
                author="Bob",
                created_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_connector = AsyncMock()
        # First sync — one document
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(original_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )
        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        rows = list(await db_session.scalars(
            select(SourceDocument).where(
                SourceDocument.connector_type == ConnectorType.SLACK
            )
        ))
        assert len(rows) == 1
        assert rows[0].content == "Original content"

        # Second sync — same external_id with edited content + one new doc
        # Reset SyncState cursor so this runs as initial again
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        ss.cursor = None
        await db_session.flush()

        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(updated_docs)

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        # Expire cached ORM objects — raw SQL upsert bypasses identity map
        db_session.expire_all()
        rows = list(await db_session.scalars(
            select(SourceDocument)
            .where(SourceDocument.connector_type == ConnectorType.SLACK)
            .order_by(SourceDocument.external_id)
        ))
        assert len(rows) == 2  # Not 3 — dedup prevented duplicate
        assert rows[0].external_id == "C1:dedup.1"
        assert rows[0].content == "Edited content"  # Updated, not duplicated
        assert rows[0].author == "Alice (edited)"
        assert rows[1].external_id == "C1:dedup.2"
        assert rows[1].content == "Brand new message"

    async def test_sync_creates_and_updates_sync_state(
        self, client, workspace, db_session, monkeypatch
    ):
        """SyncState is created on first sync, updated on subsequent syncs."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        # No SyncState yet
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert ss is None

        sample_docs = [
            NormalizedDocument(
                external_id="C1:ss.1",
                content="First message",
                author="U1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(sample_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        # SyncState created
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert ss is not None
        first_cursor = ss.cursor
        assert first_cursor is not None
        assert ss.last_synced_at is not None
        assert ss.last_synced_item_id == "C1:ss.1"

        # Second sync — cursor advances
        newer_docs = [
            NormalizedDocument(
                external_id="C1:ss.2",
                content="Newer message",
                author="U2",
                created_at=datetime(2026, 3, 30, 8, 0, tzinfo=timezone.utc),
            ),
        ]
        mock_connector.fetch_incremental = lambda cursor=None: _mock_fetch_initial_yielding(newer_docs)

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        await db_session.refresh(ss)
        assert ss.cursor > first_cursor  # Cursor advanced
        assert ss.last_synced_item_id == "C1:ss.2"

    async def test_sync_reads_cursor_from_sync_state_not_config(
        self, client, workspace, db_session, monkeypatch
    ):
        """When SyncState has a cursor, it drives incremental — config is ignored."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={"team_name": "Test"},
        )
        db_session.add(conn)
        await db_session.flush()

        # SyncState has a cursor — should trigger incremental
        ss = SyncState(connector_id=conn.id, cursor="1711699200.0")
        db_session.add(ss)
        await db_session.flush()

        calls = []

        async def _track_incremental(cursor=None):
            calls.append(("incremental", cursor))
            return
            yield  # noqa: E702

        mock_connector = AsyncMock()
        mock_connector.fetch_incremental = _track_incremental
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        # Verify fetch_incremental was called with the SyncState cursor
        assert len(calls) == 1
        assert calls[0] == ("incremental", "1711699200.0")

    async def test_incremental_update_only_does_not_inflate_count(
        self, client, workspace, db_session, monkeypatch
    ):
        """Editing already-known docs in a delta sync must not inflate document_count."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        original_docs = [
            NormalizedDocument(
                external_id="C1:inflat.1",
                content="Original A",
                author="U1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:inflat.2",
                content="Original B",
                author="U2",
                created_at=datetime(2026, 3, 29, 11, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(original_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        # Initial sync — 2 new docs
        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        await db_session.refresh(conn)
        assert conn.config["document_count"] == 2

        # Incremental sync that re-fetches the same 2 docs (edits, not new)
        edited_docs = [
            NormalizedDocument(
                external_id="C1:inflat.1",
                content="Edited A",
                author="U1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
            ),
            NormalizedDocument(
                external_id="C1:inflat.2",
                content="Edited B",
                author="U2",
                created_at=datetime(2026, 3, 29, 11, 0, tzinfo=timezone.utc),
            ),
        ]
        mock_connector.fetch_incremental = lambda cursor=None: _mock_fetch_initial_yielding(edited_docs)

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        await db_session.refresh(conn)
        # Count must stay at 2 — updates don't inflate
        assert conn.config["document_count"] == 2
        assert "0 documents" in conn.config["message"]

        # Content was actually updated
        db_session.expire_all()
        row = await db_session.scalar(
            select(SourceDocument).where(SourceDocument.external_id == "C1:inflat.1")
        )
        assert row.content == "Edited A"

    async def test_last_synced_at_reflects_completion_not_start(
        self, client, workspace, db_session, monkeypatch
    ):
        """last_sync_at and SyncState.last_synced_at are stamped after
        fetch/persist finishes, not when the sync starts."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        before_sync = datetime.now(timezone.utc)

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding([])
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        after_sync = datetime.now(timezone.utc)

        await db_session.refresh(conn)
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )

        # Both timestamps are between before and after (i.e. after the start marker)
        assert conn.last_sync_at >= before_sync
        assert conn.last_sync_at <= after_sync
        assert ss.last_synced_at >= before_sync
        assert ss.last_synced_at <= after_sync

    async def test_legacy_config_cursor_migrates_to_sync_state(
        self, client, workspace, db_session, monkeypatch
    ):
        """A connector with sync_cursor in config (legacy) still works
        and the cursor gets migrated to SyncState."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=token_enc,
            config={"sync_cursor": "1711699200.0", "team_name": "Test"},
        )
        db_session.add(conn)
        await db_session.flush()

        mock_connector = AsyncMock()
        mock_connector.fetch_incremental = lambda cursor=None: _mock_fetch_initial_yielding([])
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        await db_session.refresh(conn)
        # sync_cursor removed from config
        assert "sync_cursor" not in conn.config

        # Cursor now in SyncState
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn.id)
        )
        assert ss is not None
        assert ss.cursor == "1711699200.0"

    async def test_edited_document_resets_processed_at_for_reprocessing(
        self, client, workspace, db_session, monkeypatch
    ):
        """When a document's content changes on re-sync, processed_at is
        reset to NULL so the ingestion pipeline re-extracts it."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        original_docs = [
            NormalizedDocument(
                external_id="C1:reprocess.1",
                content="decision: ship v1 Monday",
                author="PM",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "product"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(original_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        # Initial sync — doc is persisted and processed
        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 200

        db_session.expire_all()
        row = await db_session.scalar(
            select(SourceDocument).where(
                SourceDocument.external_id == "C1:reprocess.1"
            )
        )
        assert row.processed_at is not None

        # Incremental sync — same external_id but content edited
        edited_docs = [
            NormalizedDocument(
                external_id="C1:reprocess.1",
                content="decision: ship v1 Wednesday instead",
                author="PM",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "product"},
            ),
        ]
        mock_connector.fetch_incremental = lambda cursor=None: (
            _mock_fetch_initial_yielding(edited_docs)
        )

        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 200

        db_session.expire_all()
        row = await db_session.scalar(
            select(SourceDocument).where(
                SourceDocument.external_id == "C1:reprocess.1"
            )
        )
        # Content updated
        assert row.content == "decision: ship v1 Wednesday instead"
        # processed_at was reset, then re-stamped by ingestion pipeline
        assert row.processed_at is not None

        # Verify the component was updated with new content
        from app.models.knowledge import Component
        comps = list(await db_session.scalars(
            select(Component).where(Component.value.like("%Wednesday%"))
        ))
        assert len(comps) >= 1

    async def test_unchanged_content_keeps_processed_at(
        self, client, workspace, db_session, monkeypatch
    ):
        """When a re-sync fetches a document with identical content,
        processed_at is NOT reset — the doc is not re-extracted."""
        self._setup_encryption(monkeypatch)
        token_enc = encrypt_token("xoxb-test-token")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        original_docs = [
            NormalizedDocument(
                external_id="C1:unchanged.1",
                content="decision: ship v1 Monday",
                author="PM",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "product"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(original_docs)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        # Initial sync — doc is persisted and processed
        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 200

        db_session.expire_all()
        row = await db_session.scalar(
            select(SourceDocument).where(
                SourceDocument.external_id == "C1:unchanged.1"
            )
        )
        first_processed_at = row.processed_at
        assert first_processed_at is not None

        # Incremental sync — same external_id, SAME content
        mock_connector.fetch_incremental = lambda cursor=None: (
            _mock_fetch_initial_yielding(original_docs)
        )

        resp = await client.post(f"/api/connectors/{conn_id}/sync")
        assert resp.status_code == 200

        db_session.expire_all()
        row = await db_session.scalar(
            select(SourceDocument).where(
                SourceDocument.external_id == "C1:unchanged.1"
            )
        )
        # processed_at should NOT have been reset — content is identical
        assert row.processed_at is not None
        # The second sync should have processed 0 documents
        body = resp.json()
        assert "processed 0" in body["message"]


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

    async def test_callback_with_transport_error_returns_502(
        self, client, workspace, monkeypatch
    ):
        fake_redis = _FakeRedis()
        self._setup_monkeypatch(monkeypatch, fake_redis)

        state = f"{workspace.id}:transportnonce"
        fake_redis.store[f"ce:oauth_state:{state}"] = str(workspace.id)

        class _RaisingAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("boom")

        monkeypatch.setattr(
            connector_module.httpx,
            "AsyncClient",
            lambda *args, **kwargs: _RaisingAsyncClient(),
        )

        resp = await client.get(
            "/api/connectors/slack/callback",
            params={"code": "bad-code", "state": state},
        )
        assert resp.status_code == 502
        assert "request failed" in resp.json()["detail"]

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


# ── NormalizedDocument ────────────────────────────────────────────


class TestNormalizedDocument:
    def test_creation_with_defaults(self):
        doc = NormalizedDocument(external_id="abc", content="Hello")
        assert doc.external_id == "abc"
        assert doc.content == "Hello"
        assert doc.author is None
        assert doc.source_url is None
        assert doc.created_at is None
        assert doc.metadata == {}

    def test_creation_with_all_fields(self):
        dt = datetime(2026, 3, 29, tzinfo=timezone.utc)
        doc = NormalizedDocument(
            external_id="C1:123.4",
            content="Test message",
            author="U1",
            source_url="https://slack.com/archives/C1/p1234",
            created_at=dt,
            metadata={"channel_name": "general"},
        )
        assert doc.author == "U1"
        assert doc.source_url == "https://slack.com/archives/C1/p1234"
        assert doc.created_at == dt
        assert doc.metadata["channel_name"] == "general"

    def test_is_immutable(self):
        doc = NormalizedDocument(external_id="x", content="y")
        import pytest
        with pytest.raises(AttributeError):
            doc.content = "changed"


# ── SlackConnector unit tests ─────────────────────────────────────


class TestSlackConnector:
    def test_constructor_sets_auth_header(self):
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-my-token")
        assert conn._headers["Authorization"] == "Bearer xoxb-my-token"

    async def test_handle_webhook_returns_empty(self):
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-test")
        result = await conn.handle_webhook({"type": "event_callback"})
        assert result == []

    async def test_slack_get_raises_auth_error_on_token_revoked(self):
        import pytest
        from unittest.mock import MagicMock
        from app.connectors.base import AuthenticationError
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-bad")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False, "error": "token_revoked"}

        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response

        with pytest.raises(AuthenticationError, match="token_revoked"):
            await conn._slack_get(mock_http, "conversations.list")

    async def test_slack_get_raises_rate_limit(self):
        import pytest
        from unittest.mock import MagicMock
        from app.connectors.base import RateLimitError
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-test")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "10"}

        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            await conn._slack_get(mock_http, "conversations.list")
        assert exc_info.value.retry_after == 10.0

    async def test_slack_get_wraps_transport_errors(self):
        import pytest
        from app.connectors.base import ConnectorError
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-test")
        mock_http = AsyncMock()
        mock_http.get.side_effect = httpx.ConnectError("boom")

        with pytest.raises(ConnectorError, match="request failed"):
            await conn._slack_get(mock_http, "conversations.list")

    async def test_fetch_channel_history_resolves_users_and_concatenates_threads(
        self, monkeypatch
    ):
        from app.connectors.slack import SlackConnector

        conn = SlackConnector("xoxb-test")

        async def fake_slack_get(http, method, params=None):
            if method == "conversations.history":
                return {
                    "ok": True,
                    "messages": [
                        {
                            "ts": "1711706400.0",
                            "text": "Launch is blocked",
                            "user": "U1",
                            "thread_ts": "1711706400.0",
                            "reply_count": 2,
                        },
                        {
                            "ts": "1711706460.0",
                            "text": "Need pricing approval",
                            "user": "U2",
                            "thread_ts": "1711706400.0",
                        },
                    ],
                    "response_metadata": {},
                }
            if method == "conversations.replies":
                return {
                    "ok": True,
                    "messages": [
                        {
                            "ts": "1711706400.0",
                            "text": "Launch is blocked",
                            "user": "U1",
                            "thread_ts": "1711706400.0",
                        },
                        {
                            "ts": "1711706460.0",
                            "text": "Need pricing approval",
                            "user": "U2",
                            "thread_ts": "1711706400.0",
                        },
                        {
                            "ts": "1711706520.0",
                            "text": "Waiting on finance",
                            "user": "U1",
                            "thread_ts": "1711706400.0",
                        },
                    ],
                    "response_metadata": {},
                }
            if method == "users.info":
                user_id = params["user"]
                names = {
                    "U1": {"display_name": "Alice"},
                    "U2": {"display_name": "Bob"},
                }
                return {
                    "ok": True,
                    "user": {
                        "id": user_id,
                        "profile": names[user_id],
                    },
                }
            raise AssertionError(f"Unexpected Slack method: {method}")

        monkeypatch.setattr(conn, "_slack_get", fake_slack_get)

        docs = [
            doc
            async for doc in conn._fetch_channel_history(
                AsyncMock(),
                {"id": "C1", "name": "general"},
                oldest=None,
            )
        ]

        assert len(docs) == 1
        doc = docs[0]
        assert doc.author == "Alice"
        assert doc.metadata["reply_count"] == 2
        assert doc.metadata["channel_name"] == "general"
        assert "Thread replies:" in doc.content
        assert "Bob: Need pricing approval" in doc.content
        assert "Alice: Waiting on finance" in doc.content
