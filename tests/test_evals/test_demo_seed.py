from __future__ import annotations

from sqlalchemy import select

from app.evals.demo_seed import DEFAULT_WORKSPACE_NAME, seed_demo_workspace
from app.evals.gold_set import load_default_cases
from app.models.connector import Connector
from app.models.knowledge import KnowledgeModel
from app.models.source import ConnectorType, SourceDocument


class TestDemoSeed:
    async def test_seed_demo_workspace_creates_eval_ready_workspace(self, db_session):
        result = await seed_demo_workspace(
            db_session,
            workspace_name=DEFAULT_WORKSPACE_NAME,
            replace_existing=True,
        )

        connectors = list(await db_session.scalars(select(Connector)))
        models = list(await db_session.scalars(select(KnowledgeModel)))
        documents = list(await db_session.scalars(select(SourceDocument)))

        assert result.status == "created"
        assert result.seeded_case_count == len(load_default_cases())
        assert {connector.connector_type for connector in connectors} >= {
            ConnectorType.NOTION,
            ConnectorType.SLACK,
            ConnectorType.ZOOM,
            ConnectorType.GITHUB,
        }
        assert any(model.name == "GitHub Insights" for model in models)
        assert len(documents) >= 20
