"""Tests for the ingestion pipeline — SourceDocument → KnowledgeModel/Component."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

import app.services.connector_service as connector_module
from app.connectors.base import NormalizedDocument
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.knowledge import Component, ComponentSource, KnowledgeModel
from app.models.source import ConnectorType, SourceDocument
from app.services.ingestion_service import IngestionService
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


async def _mock_fetch_initial_yielding(docs):
    for d in docs:
        yield d


@pytest.fixture
async def slack_connector(db_session, workspace):
    """A CONNECTED Slack connector for the workspace."""
    conn = Connector(
        workspace_id=workspace.id,
        connector_type=ConnectorType.SLACK,
        status=ConnectorStatus.CONNECTED,
        config={"team_name": "Test"},
    )
    db_session.add(conn)
    await db_session.flush()
    return conn


# ── IngestionService unit tests ──────────────────────────────────


class TestIngestionServiceDirect:
    """Tests that call IngestionService directly, bypassing the API layer."""

    async def test_selects_only_unprocessed_documents(
        self, db_session, workspace, slack_connector
    ):
        """Already-processed docs (processed_at != None) are skipped."""
        processed = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:already.done",
            content="decision: ship v2",
            processed_at=datetime(2026, 3, 29, tzinfo=timezone.utc),
        )
        unprocessed = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:needs.work",
            content="decision: delay v3",
        )
        db_session.add_all([processed, unprocessed])
        await db_session.flush()

        svc = IngestionService(db_session)
        docs = await svc._select_unprocessed(slack_connector.id)

        assert len(docs) == 1
        assert docs[0].external_id == "C1:needs.work"

    async def test_processing_creates_model_and_components(
        self, db_session, workspace, slack_connector
    ):
        """Processing docs with decision patterns creates a model + components."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:fact.1",
            content="decision: migrate to Postgres 16\nblocker: need DBA approval",
            metadata_json={"channel_name": "engineering"},
        )
        db_session.add(doc)
        await db_session.flush()

        svc = IngestionService(db_session)
        count = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )

        assert count == 1

        # Model auto-created
        model = await db_session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace.id,
                KnowledgeModel.auto_generated.is_(True),
            )
        )
        assert model is not None
        assert model.name == "Slack Insights"

        # Two components — one decision, one blocker
        components = list(await db_session.scalars(
            select(Component)
            .where(Component.model_id == model.id)
            .order_by(Component.name)
        ))
        assert len(components) == 2

        blocker = next(c for c in components if "Blocker" in c.name)
        assert blocker.value == "need DBA approval"
        assert blocker.confidence == 0.80

        decision = next(c for c in components if "Decision" in c.name)
        assert decision.value == "migrate to Postgres 16"
        assert decision.confidence == 0.75

    async def test_component_source_links_created(
        self, db_session, workspace, slack_connector
    ):
        """Each extracted component is linked to its source document."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:link.1",
            content="action item: update runbook",
            source_url="https://slack.com/archives/C1/p123",
            metadata_json={"channel_name": "ops"},
        )
        db_session.add(doc)
        await db_session.flush()

        svc = IngestionService(db_session)
        await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )

        links = list(await db_session.scalars(
            select(ComponentSource).where(
                ComponentSource.source_document_id == doc.id
            )
        ))
        assert len(links) == 1
        assert links[0].extraction_context is not None
        assert "slack" in links[0].extraction_context.lower()

    async def test_processed_at_stamped(
        self, db_session, workspace, slack_connector
    ):
        """After processing, the doc's processed_at is set."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:stamp.1",
            content="decision: go with option A",
            metadata_json={"channel_name": "general"},
        )
        db_session.add(doc)
        await db_session.flush()

        assert doc.processed_at is None

        svc = IngestionService(db_session)
        await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )

        await db_session.refresh(doc)
        assert doc.processed_at is not None

    async def test_already_processed_docs_skipped_on_rerun(
        self, db_session, workspace, slack_connector
    ):
        """Running processing twice doesn't re-process already-handled docs."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:rerun.1",
            content="decision: use FastAPI",
            metadata_json={"channel_name": "backend"},
        )
        db_session.add(doc)
        await db_session.flush()

        svc = IngestionService(db_session)

        # First run processes it
        count1 = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
        )
        assert count1 == 1

        # Second run finds nothing unprocessed
        count2 = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
        )
        assert count2 == 0

    async def test_component_upsert_updates_existing(
        self, db_session, workspace, slack_connector
    ):
        """If the same fact name is extracted again, the component is updated not duplicated."""
        doc1 = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:upsert.1",
            content="decision: launch Monday",
            metadata_json={"channel_name": "product"},
        )
        doc2 = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:upsert.2",
            content="decision: launch Tuesday instead",
            metadata_json={"channel_name": "product"},
        )
        db_session.add_all([doc1, doc2])
        await db_session.flush()

        svc = IngestionService(db_session)
        count = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )
        assert count == 2

        # Only one component named "Decision in #product"
        components = list(await db_session.scalars(
            select(Component).where(Component.name == "Decision in #product")
        ))
        assert len(components) == 1
        # Value updated to the later doc's extraction
        assert "Tuesday" in components[0].value

        # But both source docs are linked
        links = list(await db_session.scalars(
            select(ComponentSource).where(
                ComponentSource.component_id == components[0].id
            )
        ))
        assert len(links) == 2

    async def test_threaded_discussion_creates_fallback_component(
        self, db_session, workspace, slack_connector
    ):
        """Messages with reply_count but no structured patterns use the fallback."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:thread.1",
            content="We should revisit the pricing model\n\nThread replies:\nBob: agreed",
            author="Alice",
            metadata_json={
                "channel_name": "strategy",
                "reply_count": 1,
            },
        )
        db_session.add(doc)
        await db_session.flush()

        svc = IngestionService(db_session)
        await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )

        comp = await db_session.scalar(
            select(Component).where(Component.name == "Discussion in #strategy")
        )
        assert comp is not None
        assert "Alice" in comp.value
        assert comp.confidence == 0.55

    async def test_no_facts_no_components(
        self, db_session, workspace, slack_connector
    ):
        """A message with no patterns and no thread creates nothing."""
        doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:noop.1",
            content="hey anyone want coffee?",
            metadata_json={"channel_name": "random"},
        )
        db_session.add(doc)
        await db_session.flush()

        svc = IngestionService(db_session)
        count = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )
        # Doc still processed (stamp set), just no components created
        assert count == 1
        await db_session.refresh(doc)
        assert doc.processed_at is not None

        comp_count = await db_session.scalar(
            select(func.count()).select_from(Component)
        )
        assert comp_count == 0

    async def test_tenant_isolation(self, db_session, workspace, slack_connector):
        """Documents from a different connector are never processed by another workspace."""
        # Second workspace + connector
        from app.models.user import Workspace

        ws2 = Workspace(name="Other Corp")
        db_session.add(ws2)
        await db_session.flush()

        conn2 = Connector(
            workspace_id=ws2.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={"team_name": "Other"},
        )
        db_session.add(conn2)
        await db_session.flush()

        # Doc belongs to conn2
        doc_other = SourceDocument(
            connector_id=conn2.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:other.1",
            content="decision: secret strategy from other org",
            metadata_json={"channel_name": "confidential"},
        )
        # Doc belongs to slack_connector (workspace 1)
        doc_own = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:own.1",
            content="decision: our public plan",
            metadata_json={"channel_name": "general"},
        )
        db_session.add_all([doc_other, doc_own])
        await db_session.flush()

        # Process workspace 1's connector
        svc = IngestionService(db_session)
        count = await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )

        assert count == 1  # Only our doc, not the other workspace's

        # The other workspace's doc is still unprocessed
        await db_session.refresh(doc_other)
        assert doc_other.processed_at is None

        # No model created in workspace 2
        model_ws2 = await db_session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == ws2.id,
            )
        )
        assert model_ws2 is None

    async def test_different_connector_types_get_separate_models(
        self, db_session, workspace, slack_connector
    ):
        """Slack and Notion connectors produce distinct KnowledgeModels."""
        notion_conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.NOTION,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(notion_conn)
        await db_session.flush()

        # Slack doc
        slack_doc = SourceDocument(
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
            external_id="C1:model-iso.1",
            content="decision: adopt Kubernetes",
            metadata_json={"channel_name": "infra"},
        )
        # Notion doc
        notion_doc = SourceDocument(
            connector_id=notion_conn.id,
            connector_type=ConnectorType.NOTION,
            external_id="notion:model-iso.1",
            content="decision: migrate to Aurora",
            metadata_json={"channel_name": "unknown"},
        )
        db_session.add_all([slack_doc, notion_doc])
        await db_session.flush()

        svc = IngestionService(db_session)

        await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=slack_connector.id,
            connector_type=ConnectorType.SLACK,
        )
        await svc.process_connector_documents(
            workspace_id=workspace.id,
            connector_id=notion_conn.id,
            connector_type=ConnectorType.NOTION,
        )

        models = list(await db_session.scalars(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace.id,
                KnowledgeModel.auto_generated.is_(True),
            )
        ))
        assert len(models) == 2
        names = {m.name for m in models}
        assert names == {"Slack Insights", "Notion Insights"}


# ── End-to-end: sync triggers ingestion ──────────────────────────


class TestSyncTriggersIngestion:
    """Verify that queue_sync → _persist_documents → IngestionService
    runs end-to-end through the API."""

    def _setup(self, monkeypatch):
        monkeypatch.setattr(
            connector_module.settings, "encryption_key", _TEST_FERNET_KEY
        )

    async def test_sync_processes_documents_into_knowledge_graph(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="C1:e2e.1",
                content="decision: adopt Kubernetes",
                author="DevOps Lead",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "infra"},
            ),
            NormalizedDocument(
                external_id="C1:e2e.2",
                content="blocker: need budget approval for K8s cluster",
                author="VP Eng",
                created_at=datetime(2026, 3, 29, 11, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "infra"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(
            sample_docs
        )
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200
        body = resp.json()
        assert "processed" in body["message"]

        await db_session.refresh(conn)
        assert conn.config.get("processed_count", 0) > 0

        # Knowledge model auto-created
        model = await db_session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace.id,
                KnowledgeModel.auto_generated.is_(True),
            )
        )
        assert model is not None

        # Components extracted
        components = list(await db_session.scalars(
            select(Component).where(Component.model_id == model.id)
        ))
        assert len(components) >= 2

        # Source documents scoped to this connector and processed
        docs = list(await db_session.scalars(
            select(SourceDocument).where(
                SourceDocument.connector_id == conn.id,
                SourceDocument.processed_at.is_not(None),
            )
        ))
        assert len(docs) == 2

    async def test_second_sync_only_processes_new_documents(
        self, client, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        token_enc = encrypt_token("xoxb-test")
        conn = _make_connected_slack(workspace, token_enc)
        db_session.add(conn)
        await db_session.flush()

        batch1 = [
            NormalizedDocument(
                external_id="C1:batch.1",
                content="decision: use Redis for caching",
                author="U1",
                created_at=datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "backend"},
            ),
        ]

        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_fetch_initial_yielding(batch1)
        monkeypatch.setattr(
            connector_module.ConnectorService,
            "_resolve_connector",
            lambda self, ct, tok: mock_connector,
        )

        # First sync
        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        # Second sync with one new doc
        batch2 = [
            NormalizedDocument(
                external_id="C1:batch.2",
                content="action item: benchmark Redis vs Memcached",
                author="U2",
                created_at=datetime(2026, 3, 30, 8, 0, tzinfo=timezone.utc),
                metadata={"channel_name": "backend"},
            ),
        ]
        mock_connector.fetch_incremental = lambda cursor=None: (
            _mock_fetch_initial_yielding(batch2)
        )

        resp = await client.post(f"/api/connectors/{conn.id}/sync")
        assert resp.status_code == 200

        await db_session.refresh(conn)
        # Only the new doc was processed in the second sync
        assert conn.config["processed_count"] == 1

        # Total components: decision + action item
        comp_count = await db_session.scalar(
            select(func.count()).select_from(Component)
        )
        assert comp_count == 2
