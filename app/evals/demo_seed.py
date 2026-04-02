"""Deterministic demo seed data for local smoke runs and eval regressions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evals.gold_set import load_default_cases
from app.models.connector import Connector, ConnectorStatus
from app.models.knowledge import Component, ComponentSource, KnowledgeModel
from app.models.source import ConnectorType, SourceDocument
from app.models.user import Workspace
from app.processing.embedder import HashingEmbedder


DEFAULT_WORKSPACE_NAME = "Acme Accuracy Demo"
_EMBEDDER = HashingEmbedder()


@dataclass(frozen=True, slots=True)
class SourceSeed:
    connector_type: ConnectorType
    external_id: str
    content: str
    label_metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class ComponentSeed:
    model_name: str
    model_description: str
    name: str
    value: str
    sources: tuple[SourceSeed, ...]
    authority_weight: float = 0.9


@dataclass(frozen=True, slots=True)
class SeedResult:
    workspace_id: UUID
    workspace_name: str
    status: str
    seeded_case_count: int


_SEEDS: tuple[ComponentSeed, ...] = (
    ComponentSeed(
        model_name="Pricing",
        model_description="Pricing facts",
        name="Enterprise Plan",
        value="Enterprise pricing is $600/seat with annual terms.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-enterprise-plan",
                "Enterprise pricing is $600/seat.",
                {"page_title": "Pricing Handbook"},
            ),
            SourceSeed(
                ConnectorType.SLACK,
                "slack-enterprise-plan",
                "Decision: enterprise stays at $600/seat.",
                {"channel_name": "pricing"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Pricing",
        model_description="Pricing facts",
        name="Starter Plan",
        value="Starter Plan is $29/mo.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-starter-plan",
                "Starter Plan is $29/mo.",
                {"page_title": "Pricing Handbook"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Pricing",
        model_description="Pricing facts",
        name="Growth Plan",
        value="Growth tier is $149/mo with team features included.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-growth-plan",
                "Growth Plan: $149/mo with team features.",
                {"page_title": "Pricing Handbook"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Pricing",
        model_description="Pricing facts",
        name="Annual Discount Policy",
        value="We offer a 20% discount for annual commitments across all plans.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-annual-discount",
                "Annual discount: 20% off for annual billing on all plans.",
                {"page_title": "Pricing Handbook"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="SSO Blocker",
        value="Active blockers: SSO is blocked by engineering bandwidth and analytics reliability work.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-sso-blocker",
                "SSO is blocked by engineering bandwidth.",
                {"channel_name": "roadmap"},
            ),
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-sso-blocker",
                "Meeting blocker: engineering bandwidth is the blocker for SSO.",
                {"meeting_topic": "Weekly Product Review"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Blocker in Weekly Product Review",
        value="From meetings: current blockers include waiting on legal approval.",
        sources=(
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-legal-blocker",
                "Current blocker: waiting on legal approval.",
                {"meeting_topic": "Weekly Product Review"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="API Migration Blocker",
        value="API migration is blocked by downstream partner integration not being ready.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-api-migration-blocker",
                "Blocker: downstream partner integration not ready for API migration.",
                {"channel_name": "engineering"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="Mobile Release Blocker",
        value="Mobile release is blocked pending app store review approval.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-mobile-release-blocker",
                "Blocker: waiting on app store review for mobile release.",
                {"channel_name": "mobile"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="SSO Launch Target",
        value="SSO launch target is Q3.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-sso-launch",
                "SSO launch target is Q3.",
                {"page_title": "Roadmap"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="Analytics Rewrite Target",
        value="Analytics rewrite is targeted for Q4 delivery.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-analytics-rewrite",
                "Analytics rewrite target: Q4.",
                {"page_title": "Roadmap"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Roadmap",
        model_description="Roadmap facts",
        name="Mobile App Launch",
        value="Mobile app launch is planned for Q2 with cross-platform support.",
        sources=(
            SourceSeed(
                ConnectorType.NOTION,
                "notion-mobile-launch",
                "Mobile app launch: Q2 with cross-platform mobile support.",
                {"page_title": "Roadmap"},
            ),
            SourceSeed(
                ConnectorType.SLACK,
                "slack-mobile-launch",
                "Confirmed: mobile app targets Q2 launch.",
                {"channel_name": "product"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Decision in Weekly Product Review",
        value="Meeting decision: we decided the launch timing — ship the onboarding flow next Tuesday.",
        sources=(
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-onboarding-decision",
                "We decided to ship onboarding next Tuesday.",
                {"meeting_topic": "Weekly Product Review"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Decisions",
        model_description="Decision facts",
        name="DB Migration Decision",
        value="We decided to migrate to Postgres 16 using a rolling upgrade strategy.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-db-migration",
                "Decision: migrate to Postgres 16 with rolling upgrade.",
                {"channel_name": "engineering"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Decisions",
        model_description="Decision facts",
        name="Auth Provider Decision",
        value="We chose Auth0 as our authentication provider.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-auth-provider",
                "Decision: going with Auth0 for authentication.",
                {"channel_name": "engineering"},
            ),
            SourceSeed(
                ConnectorType.NOTION,
                "notion-auth-provider",
                "Auth provider decision: Auth0 selected.",
                {"page_title": "Architecture Decisions"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Decisions",
        model_description="Decision facts",
        name="Framework Decision",
        value="We picked FastAPI for the new service framework.",
        sources=(
            SourceSeed(
                ConnectorType.SLACK,
                "slack-framework-decision",
                "Decision: picked FastAPI for the new service.",
                {"channel_name": "engineering"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Action Item from Engineering Sync",
        value="Action item: run load test on staging before the release.",
        sources=(
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-eng-action-item",
                "AI: run load test on staging before release.",
                {"meeting_topic": "Engineering Sync"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Sales Pipeline Update",
        value="Enterprise pipeline is growing with three new deals in negotiation.",
        sources=(
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-sales-pipeline",
                "Sales update: enterprise pipeline growing, three new deals.",
                {"meeting_topic": "Sales Standup"},
            ),
            SourceSeed(
                ConnectorType.GONG,
                "gong-sales-pipeline",
                "Enterprise pipeline update: three deals in negotiation.",
                {"location": "Sales Call Recording"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Retro Concern",
        value="Concern raised: deployment rollback process needs improvement.",
        sources=(
            SourceSeed(
                ConnectorType.ZOOM,
                "zoom-retro-concern",
                "Retro: deployment rollback process needs improvement.",
                {"meeting_topic": "Sprint Retrospective"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="Zoom Insights",
        model_description="Meeting facts",
        name="Customer Feedback Summary",
        value="Customer feedback: onboarding documentation needs to be clearer.",
        sources=(
            SourceSeed(
                ConnectorType.GONG,
                "gong-customer-feedback",
                "Customer call: onboarding documentation needs improvement.",
                {"location": "Customer Success Call"},
            ),
        ),
    ),
    ComponentSeed(
        model_name="GitHub Insights",
        model_description="GitHub issue and pull-request context",
        name="CI Workflow Follow-up",
        value="GitHub issue tracks tightening accuracy regression gating in CI.",
        sources=(
            SourceSeed(
                ConnectorType.GITHUB,
                "github:acme/context-engine:issue:42",
                "Issue #42: tighten accuracy regression gating in CI and document the local eval path.",
                {
                    "title": "Tighten accuracy regression gating",
                    "repo_full_name": "acme/context-engine",
                },
            ),
        ),
    ),
)


async def seed_demo_workspace(
    session: AsyncSession,
    *,
    workspace_name: str = DEFAULT_WORKSPACE_NAME,
    replace_existing: bool = False,
) -> SeedResult:
    workspace = await session.scalar(
        select(Workspace).where(Workspace.name == workspace_name).limit(1)
    )
    if workspace is not None and replace_existing:
        await session.delete(workspace)
        await session.commit()
        workspace = None

    if workspace is not None:
        return SeedResult(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            status="existing",
            seeded_case_count=len(load_default_cases()),
        )

    workspace = Workspace(
        name=workspace_name,
        description="Deterministic demo workspace for local smoke tests and eval regressions.",
    )
    session.add(workspace)
    await session.flush()

    connectors = {
        connector_type: await _ensure_connector(session, workspace.id, connector_type)
        for connector_type in {
            source.connector_type
            for seed in _SEEDS
            for source in seed.sources
        }
    }
    models: dict[str, KnowledgeModel] = {}
    now = datetime.now(UTC)

    for seed in _SEEDS:
        model = models.get(seed.model_name)
        if model is None:
            model = KnowledgeModel(
                workspace_id=workspace.id,
                name=seed.model_name,
                description=seed.model_description,
            )
            session.add(model)
            await session.flush()
            models[seed.model_name] = model

        component = Component(
            model_id=model.id,
            name=seed.name,
            value=seed.value,
            confidence=0.95,
            authority_source="seeded-demo",
            authority_weight=seed.authority_weight,
            last_verified_at=now,
            embedding=await _EMBEDDER.embed_text(f"{seed.name}\n{seed.value}"),
        )
        session.add(component)
        await session.flush()

        for source_seed in seed.sources:
            connector = connectors[source_seed.connector_type]
            document = SourceDocument(
                connector_id=connector.id,
                connector_type=source_seed.connector_type,
                external_id=source_seed.external_id,
                content=source_seed.content,
                author="seed",
                source_url=f"https://example.com/{source_seed.external_id}",
                created_at_source=now,
                metadata_json=source_seed.label_metadata,
                processed_at=now,
            )
            session.add(document)
            await session.flush()
            session.add(
                ComponentSource(
                    component_id=component.id,
                    source_document_id=document.id,
                    extraction_context=source_seed.content,
                    extractor_name="structured_llm",
                    extractor_kind="llm_structured",
                    extractor_schema_version="fact_extraction.v1",
                )
            )

    await session.commit()
    return SeedResult(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        status="created",
        seeded_case_count=len(load_default_cases()),
    )


async def _ensure_connector(
    session: AsyncSession,
    workspace_id: UUID,
    connector_type: ConnectorType,
) -> Connector:
    connector = Connector(
        workspace_id=workspace_id,
        connector_type=connector_type,
        status=ConnectorStatus.CONNECTED,
        config=_connector_config(connector_type),
    )
    session.add(connector)
    await session.flush()
    return connector


def _connector_config(connector_type: ConnectorType) -> dict[str, object]:
    if connector_type == ConnectorType.ZOOM:
        return {
            "ingestion_mode": "transcripts_only",
            "source_focus": "meeting_transcripts",
            "auth_mode": "manual_token",
            "sync_delivery_mode": "polling_only",
            "webhook_auto_sync": False,
        }
    if connector_type == ConnectorType.GITHUB:
        return {
            "ingestion_mode": "issues_and_pull_requests",
            "source_focus": "engineering_system_of_record",
            "auth_mode": "manual_token",
            "sync_delivery_mode": "polling_only",
            "webhook_auto_sync": False,
            "repositories": ["acme/context-engine"],
        }
    return {}
