"""Tests for the Notion connector — resolution, sync, document mapping."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

import app.services.connector_service as connector_module
import app.services.sync_service as sync_module
from app.connectors.base import AuthenticationError, NormalizedDocument
from app.connectors.notion import (
    NotionConnector,
    extract_block_text,
    extract_page_title,
    page_to_text,
)
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.source import ConnectorType, SourceDocument
from app.services.connector_service import ConnectorService, SyncError
from app.services.sync_service import SyncExecutor, SyncError as SyncExecutorError
from app.utils.crypto import encrypt_token

from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


# ── Fixture data shaped like Notion API responses ─────────────────────


def _make_notion_page(
    page_id: str = "page-abc-123",
    title: str = "Engineering Roadmap",
    blocks: list[dict] | None = None,
    created_time: str = "2026-03-28T10:00:00.000Z",
    last_edited_time: str = "2026-03-29T15:30:00.000Z",
    author_email: str = "alice@example.com",
    url: str = "https://notion.so/eng-roadmap-abc123",
) -> dict:
    if blocks is None:
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "We are targeting Q3 for the SSO launch."}]
                },
            },
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"plain_text": "Key Decisions"}]
                },
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"plain_text": "Adopt SAML over OIDC"}]
                },
            },
        ]

    return {
        "id": page_id,
        "object": "page",
        "created_time": created_time,
        "last_edited_time": last_edited_time,
        "url": url,
        "created_by": {
            "type": "person",
            "person": {"email": author_email},
        },
        "properties": {
            "title": {
                "type": "title",
                "title": [{"plain_text": title}],
            },
        },
        "_blocks": blocks,
    }


async def _mock_notion_fetch(docs):
    """Async generator that yields pre-built NormalizedDocuments."""
    for d in docs:
        yield d


# ── Unit tests: content extraction helpers ────────────────────────────


class TestNotionContentExtraction:
    def test_extract_page_title(self):
        page = _make_notion_page(title="My Title")
        assert extract_page_title(page) == "My Title"

    def test_extract_page_title_untitled(self):
        page = {"properties": {}}
        assert extract_page_title(page) == "Untitled"

    def test_extract_block_text_paragraph(self):
        block = {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Hello world"}]},
        }
        assert extract_block_text(block) == "Hello world"

    def test_extract_block_text_heading(self):
        block = {
            "type": "heading_1",
            "heading_1": {"rich_text": [{"plain_text": "Section Title"}]},
        }
        assert extract_block_text(block) == "# Section Title"

    def test_extract_block_text_todo(self):
        block = {
            "type": "to_do",
            "to_do": {
                "rich_text": [{"plain_text": "Review PR"}],
                "checked": True,
            },
        }
        assert extract_block_text(block) == "[x] Review PR"

    def test_extract_block_text_bullet(self):
        block = {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"plain_text": "First item"}],
            },
        }
        assert extract_block_text(block) == "- First item"

    def test_extract_block_text_code(self):
        block = {
            "type": "code",
            "code": {
                "rich_text": [{"plain_text": "print('hi')"}],
                "language": "python",
            },
        }
        assert extract_block_text(block) == "```python\nprint('hi')\n```"

    def test_extract_block_text_empty(self):
        block = {"type": "divider", "divider": {}}
        assert extract_block_text(block) == ""

    def test_page_to_text_assembles_all_blocks(self):
        page = _make_notion_page()
        text = page_to_text(page)
        assert "Engineering Roadmap" in text
        assert "targeting Q3" in text
        assert "# Key Decisions" in text
        assert "- Adopt SAML" in text

    def test_page_to_text_skips_untitled_prefix(self):
        page = _make_notion_page(title="Untitled")
        # Should still include block content but not "Untitled" as a header
        text = page_to_text(page)
        assert not text.startswith("Untitled")
        assert "targeting Q3" in text


# ── Unit tests: NormalizedDocument mapping ────────────────────────────


class TestNotionNormalizedDocumentMapping:
    def test_maps_notion_page_to_normalized_document(self):
        page = _make_notion_page()
        doc = NotionConnector._to_normalized_document(page)

        assert doc is not None
        assert doc.external_id == "notion:page-abc-123"
        assert "Engineering Roadmap" in doc.content
        assert "targeting Q3" in doc.content
        assert doc.author == "alice@example.com"
        assert doc.source_url == "https://notion.so/eng-roadmap-abc123"
        assert doc.created_at == datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc)
        assert doc.metadata["page_id"] == "page-abc-123"
        assert doc.metadata["source_type"] == "notion"
        assert doc.metadata["last_edited_time"] == "2026-03-29T15:30:00.000Z"

    def test_skips_empty_pages(self):
        page = _make_notion_page(title="Untitled", blocks=[])
        doc = NotionConnector._to_normalized_document(page)
        assert doc is None

    def test_handles_missing_created_time(self):
        page = _make_notion_page()
        del page["created_time"]
        doc = NotionConnector._to_normalized_document(page)
        assert doc is not None
        assert doc.created_at is None

    def test_handles_missing_author(self):
        page = _make_notion_page()
        page["created_by"] = {}
        doc = NotionConnector._to_normalized_document(page)
        assert doc is not None
        assert doc.author is None


# ── Connector resolution ─────────────────────────────────────────────


class TestNotionConnectorResolution:
    def test_resolve_returns_notion_connector(self):
        executor = SyncExecutor.__new__(SyncExecutor)
        connector = executor._resolve_connector(ConnectorType.NOTION, "ntn_test_token")
        assert isinstance(connector, NotionConnector)

    def test_resolve_still_returns_slack_connector(self):
        """Slack resolution is unchanged."""
        from app.connectors.slack import SlackConnector

        executor = SyncExecutor.__new__(SyncExecutor)
        connector = executor._resolve_connector(ConnectorType.SLACK, "xoxb-test")
        assert isinstance(connector, SlackConnector)

    def test_resolve_unknown_type_raises(self):
        import pytest

        executor = SyncExecutor.__new__(SyncExecutor)
        with pytest.raises(SyncExecutorError, match="No connector implementation"):
            executor._resolve_connector(ConnectorType.GDRIVE, "token")


# ── End-to-end: sync persists SourceDocuments ─────────────────────────


def _make_connected_notion(workspace, encrypted_token):
    return Connector(
        workspace_id=workspace.id,
        connector_type=ConnectorType.NOTION,
        status=ConnectorStatus.CONNECTED,
        oauth_token_encrypted=encrypted_token,
        config={"workspace_name": "Test Notion"},
    )


class TestNotionSync:
    def _setup(self, monkeypatch):
        monkeypatch.setattr(
            connector_module.settings, "encryption_key", _TEST_FERNET_KEY
        )

    async def test_notion_sync_persists_source_documents(
        self, workspace, db_session, monkeypatch
    ):
        """Notion sync end-to-end: dlt resource → NormalizedDocument → SourceDocument."""
        self._setup(monkeypatch)
        token_enc = encrypt_token("ntn_test_token")
        conn = _make_connected_notion(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        sample_docs = [
            NormalizedDocument(
                external_id="notion:page-1",
                content="Engineering Roadmap\n\nWe are targeting Q3 for the SSO launch.",
                author="alice@example.com",
                source_url="https://notion.so/page-1",
                created_at=datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc),
                metadata={"page_id": "page-1", "source_type": "notion"},
            ),
            NormalizedDocument(
                external_id="notion:page-2",
                content="Pricing Strategy\n\ndecision: Enterprise starts at $500/seat",
                author="bob@example.com",
                source_url="https://notion.so/page-2",
                created_at=datetime(2026, 3, 29, 14, 0, tzinfo=timezone.utc),
                metadata={"page_id": "page-2", "source_type": "notion"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_notion_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        await SyncExecutor(db_session).run(conn, "ntn_test_token")

        db_session.expire_all()
        docs = list(await db_session.scalars(
            select(SourceDocument).where(
                SourceDocument.connector_id == conn_id,
            )
        ))
        assert len(docs) == 2
        assert {d.external_id for d in docs} == {"notion:page-1", "notion:page-2"}
        assert all(d.connector_type == ConnectorType.NOTION for d in docs)
        assert all(d.processed_at is not None for d in docs)

    async def test_notion_sync_dedupes_on_connector_and_external_id(
        self, workspace, db_session, monkeypatch
    ):
        """Re-syncing the same pages doesn't duplicate SourceDocuments."""
        self._setup(monkeypatch)
        token_enc = encrypt_token("ntn_test_token")
        conn = _make_connected_notion(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        sample_docs = [
            NormalizedDocument(
                external_id="notion:page-dedup",
                content="Some content",
                author="u1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"page_id": "page-dedup", "source_type": "notion"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_notion_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        # First sync (initial)
        await SyncExecutor(db_session).run(conn, "ntn_test_token")

        # Second sync (incremental path, same doc)
        mock_connector.fetch_incremental = lambda cursor=None: _mock_notion_fetch(sample_docs)
        await SyncExecutor(db_session).run(conn, "ntn_test_token")

        db_session.expire_all()
        docs = list(await db_session.scalars(
            select(SourceDocument).where(
                SourceDocument.connector_id == conn_id,
            )
        ))
        assert len(docs) == 1

    async def test_notion_sync_creates_sync_state(
        self, workspace, db_session, monkeypatch
    ):
        """SyncState row is created for the Notion connector."""
        self._setup(monkeypatch)
        token_enc = encrypt_token("ntn_test_token")
        conn = _make_connected_notion(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()
        conn_id = conn.id

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_notion_fetch([
            NormalizedDocument(
                external_id="notion:ss-page",
                content="Sync state test",
                author="u1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"source_type": "notion"},
            ),
        ])
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        await SyncExecutor(db_session).run(conn, "ntn_test_token")

        db_session.expire_all()
        ss = await db_session.scalar(
            select(SyncState).where(SyncState.connector_id == conn_id)
        )
        assert ss is not None
        assert ss.last_synced_at is not None

    async def test_notion_sync_fails_without_token(
        self, client, workspace, db_session, monkeypatch
    ):
        """Sync returns an error when no auth token is stored."""
        self._setup(monkeypatch)
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=None,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 502

    async def test_notion_sync_fails_on_disconnected_status(
        self, client, workspace, db_session, monkeypatch
    ):
        """Sync returns an error when the connector is not CONNECTED."""
        self._setup(monkeypatch)
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.DISCONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 502

    async def test_notion_connector_appears_in_list(
        self, client, workspace, db_session
    ):
        """A Notion connector is listed with dlt provider metadata."""
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        resp = await client.get(
            "/api/connectors",
            params={"workspace_id": str(workspace.id)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["connector_type"] == "notion"
        assert body[0]["provider"] == "dlt"
        assert body[0]["provider_label"] == "dlt"
