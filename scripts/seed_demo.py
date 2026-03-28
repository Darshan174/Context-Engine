from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models import (
    Component,
    ComponentSource,
    ConnectorType,
    KnowledgeModel,
    Relationship,
    RelationshipSentiment,
    RelationshipType,
    SourceDocument,
    Workspace,
)


WORKSPACE_NAME = "Acme SaaS Demo"


async def seed_demo() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        workspace = await session.scalar(
            select(Workspace).where(Workspace.name == WORKSPACE_NAME)
        )
        if workspace is None:
            workspace = Workspace(
                name=WORKSPACE_NAME,
                description="Demo workspace for Context Engine Phase 1",
            )
            session.add(workspace)
            await session.flush()

        existing_model = await session.scalar(
            select(KnowledgeModel.id).where(KnowledgeModel.workspace_id == workspace.id).limit(1)
        )
        if existing_model is not None:
            print(f"Seed data already exists for workspace '{WORKSPACE_NAME}'.")
            return

        models = {
            "Pricing": KnowledgeModel(
                workspace_id=workspace.id,
                name="Pricing",
                description="Pricing tiers, packaging, and commercial terms.",
            ),
            "Features": KnowledgeModel(
                workspace_id=workspace.id,
                name="Features",
                description="Product capabilities and shipping status.",
            ),
            "Customers": KnowledgeModel(
                workspace_id=workspace.id,
                name="Customers",
                description="Customer segments, needs, and recurrent asks.",
            ),
            "Roadmap": KnowledgeModel(
                workspace_id=workspace.id,
                name="Roadmap",
                description="Execution constraints, priorities, and upcoming work.",
            ),
        }
        session.add_all(models.values())
        await session.flush()

        components = {
            "Starter Plan": Component(
                model_id=models["Pricing"].id,
                name="Starter Plan",
                value="$29/mo",
                confidence=0.95,
                authority_source="Pricing handbook",
                last_verified_at=now - timedelta(days=1),
            ),
            "Pro Plan": Component(
                model_id=models["Pricing"].id,
                name="Pro Plan",
                value="$99/mo",
                confidence=0.95,
                authority_source="Pricing handbook",
                last_verified_at=now - timedelta(days=1),
            ),
            "Enterprise": Component(
                model_id=models["Pricing"].id,
                name="Enterprise",
                value="Custom pricing, starting $500/seat",
                confidence=0.80,
                authority_source="CEO Slack message",
                last_verified_at=now - timedelta(days=2),
            ),
            "AI Chat Widget": Component(
                model_id=models["Features"].id,
                name="AI Chat Widget",
                value="Live, shipped Q1",
                confidence=0.90,
                authority_source="PM launch update",
                last_verified_at=now - timedelta(days=3),
            ),
            "Analytics Dashboard": Component(
                model_id=models["Features"].id,
                name="Analytics Dashboard",
                value="In development, Q3 target",
                confidence=0.70,
                authority_source="Roadmap page",
                last_verified_at=now - timedelta(days=3),
            ),
            "SSO Integration": Component(
                model_id=models["Features"].id,
                name="SSO Integration",
                value="Deprioritized due to engineering bandwidth",
                confidence=0.85,
                authority_source="Engineering lead Slack update",
                last_verified_at=now - timedelta(days=4),
            ),
            "Enterprise Segment": Component(
                model_id=models["Customers"].id,
                name="Enterprise Segment",
                value="Most expansion opportunities are 200-1000 employee SaaS companies.",
                confidence=0.78,
                authority_source="Customer insights deck",
                last_verified_at=now - timedelta(days=5),
            ),
            "Top Request": Component(
                model_id=models["Customers"].id,
                name="Top Request",
                value="Enterprise prospects consistently ask for SSO and analytics exports.",
                confidence=0.82,
                authority_source="Sales call notes",
                last_verified_at=now - timedelta(days=2),
            ),
            "Q3 Theme": Component(
                model_id=models["Roadmap"].id,
                name="Q3 Theme",
                value="Analytics reliability and enterprise readiness.",
                confidence=0.76,
                authority_source="Quarterly roadmap",
                last_verified_at=now - timedelta(days=6),
            ),
            "Bandwidth Constraint": Component(
                model_id=models["Roadmap"].id,
                name="Bandwidth Constraint",
                value="Core platform team is capped until the end of the quarter.",
                confidence=0.83,
                authority_source="Engineering planning note",
                last_verified_at=now - timedelta(days=4),
            ),
        }
        session.add_all(components.values())
        await session.flush()

        source_documents = {
            "pricing-handbook": SourceDocument(
                connector_type=ConnectorType.NOTION,
                external_id="notion-pricing-handbook",
                content=(
                    "Pricing handbook\nStarter Plan: $29/mo\nPro Plan: $99/mo\n"
                    "Enterprise pricing begins at $500 per seat with custom terms."
                ),
                author="Growth Team",
                source_url="https://notion.example.com/pricing-handbook",
                created_at_source=now - timedelta(days=2),
                metadata_json={"page_title": "Pricing Handbook", "team": "Growth"},
            ),
            "enterprise-pricing-thread": SourceDocument(
                connector_type=ConnectorType.SLACK,
                external_id="slack-ops-2026-03-26-001",
                content=(
                    "CEO: For enterprise we should anchor pricing at $500/seat and keep custom packaging.\n"
                    "RevOps: Agreed, this matches what we have been quoting in late-stage deals."
                ),
                author="CEO",
                source_url="https://slack.example.com/archives/C012345/p174294000100",
                created_at_source=now - timedelta(days=2, hours=2),
                metadata_json={"channel": "exec-pricing", "message_type": "thread"},
            ),
            "ai-chat-launch": SourceDocument(
                connector_type=ConnectorType.SLACK,
                external_id="slack-product-2026-03-24-002",
                content=(
                    "PM: AI Chat Widget is live. We shipped the first version at the end of Q1 and it is"
                    " now enabled for all Pro accounts."
                ),
                author="Product Manager",
                source_url="https://slack.example.com/archives/C022222/p174276720200",
                created_at_source=now - timedelta(days=4),
                metadata_json={"channel": "product-launches", "message_type": "message"},
            ),
            "roadmap-q3": SourceDocument(
                connector_type=ConnectorType.NOTION,
                external_id="notion-roadmap-q3",
                content=(
                    "Q3 roadmap\nAnalytics Dashboard is the core enterprise readiness initiative and remains"
                    " in development with a Q3 target."
                ),
                author="Product Ops",
                source_url="https://notion.example.com/roadmap-q3",
                created_at_source=now - timedelta(days=5),
                metadata_json={"page_title": "Q3 Roadmap", "team": "Product"},
            ),
            "eng-bandwidth-note": SourceDocument(
                connector_type=ConnectorType.SLACK,
                external_id="slack-eng-2026-03-23-004",
                content=(
                    "Engineering Lead: SSO is deprioritized for now because the team is at capacity and we"
                    " need to focus on analytics reliability first."
                ),
                author="Engineering Lead",
                source_url="https://slack.example.com/archives/C033333/p174268080400",
                created_at_source=now - timedelta(days=5, hours=3),
                metadata_json={"channel": "eng-planning", "message_type": "message"},
            ),
            "customer-insights": SourceDocument(
                connector_type=ConnectorType.GDRIVE,
                external_id="drive-customer-insights-q1",
                content=(
                    "Customer insights Q1\nEnterprise prospects between 200 and 1000 employees most often ask"
                    " for SSO and deeper analytics exports during evaluation."
                ),
                author="Customer Success",
                source_url="https://drive.example.com/file/d/customer-insights-q1",
                created_at_source=now - timedelta(days=6),
                metadata_json={"file_name": "Customer Insights Q1", "team": "Customer Success"},
            ),
        }
        session.add_all(source_documents.values())
        await session.flush()

        session.add_all(
            [
                ComponentSource(
                    component_id=components["Starter Plan"].id,
                    source_document_id=source_documents["pricing-handbook"].id,
                    extraction_context="Starter Plan: $29/mo",
                ),
                ComponentSource(
                    component_id=components["Pro Plan"].id,
                    source_document_id=source_documents["pricing-handbook"].id,
                    extraction_context="Pro Plan: $99/mo",
                ),
                ComponentSource(
                    component_id=components["Enterprise"].id,
                    source_document_id=source_documents["pricing-handbook"].id,
                    extraction_context="Enterprise pricing begins at $500 per seat with custom terms.",
                ),
                ComponentSource(
                    component_id=components["Enterprise"].id,
                    source_document_id=source_documents["enterprise-pricing-thread"].id,
                    extraction_context="CEO: For enterprise we should anchor pricing at $500/seat.",
                ),
                ComponentSource(
                    component_id=components["AI Chat Widget"].id,
                    source_document_id=source_documents["ai-chat-launch"].id,
                    extraction_context="AI Chat Widget is live. We shipped the first version at the end of Q1.",
                ),
                ComponentSource(
                    component_id=components["Analytics Dashboard"].id,
                    source_document_id=source_documents["roadmap-q3"].id,
                    extraction_context="Analytics Dashboard remains in development with a Q3 target.",
                ),
                ComponentSource(
                    component_id=components["SSO Integration"].id,
                    source_document_id=source_documents["eng-bandwidth-note"].id,
                    extraction_context="SSO is deprioritized for now because the team is at capacity.",
                ),
                ComponentSource(
                    component_id=components["Enterprise Segment"].id,
                    source_document_id=source_documents["customer-insights"].id,
                    extraction_context="Enterprise prospects between 200 and 1000 employees...",
                ),
                ComponentSource(
                    component_id=components["Top Request"].id,
                    source_document_id=source_documents["customer-insights"].id,
                    extraction_context="Most often ask for SSO and deeper analytics exports.",
                ),
                ComponentSource(
                    component_id=components["Q3 Theme"].id,
                    source_document_id=source_documents["roadmap-q3"].id,
                    extraction_context="Analytics Dashboard is the core enterprise readiness initiative.",
                ),
                ComponentSource(
                    component_id=components["Bandwidth Constraint"].id,
                    source_document_id=source_documents["eng-bandwidth-note"].id,
                    extraction_context="The team is at capacity and we need to focus on analytics reliability first.",
                ),
            ]
        )

        session.add_all(
            [
                Relationship(
                    source_component_id=components["AI Chat Widget"].id,
                    target_component_id=components["Pro Plan"].id,
                    relationship_type=RelationshipType.ENABLES,
                    sentiment=RelationshipSentiment.POSITIVE,
                    description="The shipped AI Chat Widget increases the value of the Pro plan.",
                    confidence=0.86,
                ),
                Relationship(
                    source_component_id=components["SSO Integration"].id,
                    target_component_id=components["Analytics Dashboard"].id,
                    relationship_type=RelationshipType.BLOCKED_BY,
                    sentiment=RelationshipSentiment.NEGATIVE,
                    description="SSO work is paused while the team prioritizes analytics delivery.",
                    confidence=0.88,
                ),
                Relationship(
                    source_component_id=components["Analytics Dashboard"].id,
                    target_component_id=components["Enterprise"].id,
                    relationship_type=RelationshipType.DEPENDS_ON,
                    sentiment=RelationshipSentiment.POSITIVE,
                    description="Enterprise demand influences analytics roadmap priority.",
                    confidence=0.73,
                ),
            ]
        )

        await session.commit()
        print(
            "Seeded demo workspace with "
            f"{len(models)} models, {len(components)} components, "
            f"{len(source_documents)} source documents, and 3 relationships."
        )


async def main() -> None:
    try:
        await seed_demo()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
