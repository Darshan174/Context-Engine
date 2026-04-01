from __future__ import annotations

from datetime import UTC, datetime

from app.evals.gold_set import STARTUP_GOLD_SET, load_default_cases, load_fixtures
from app.evals.harness import StartupEvalHarness
from app.models import Component, ComponentSource, Connector, ConnectorStatus, ConnectorType, KnowledgeModel, SourceDocument
from app.processing.embedder import HashingEmbedder
from app.services.query_service import QueryService


async def _seed_connector(db_session, workspace_id, connector_type: ConnectorType) -> Connector:
    connector = Connector(
        workspace_id=workspace_id,
        connector_type=connector_type,
        status=ConnectorStatus.CONNECTED,
        config={},
    )
    db_session.add(connector)
    await db_session.flush()
    return connector


async def _seed_model(db_session, workspace_id, name: str, description: str) -> KnowledgeModel:
    model = KnowledgeModel(
        workspace_id=workspace_id,
        name=name,
        description=description,
    )
    db_session.add(model)
    await db_session.flush()
    return model


_embedder = HashingEmbedder()


async def _seed_component(
    db_session,
    *,
    model_id,
    name: str,
    value: str,
    authority_weight: float = 0.9,
) -> Component:
    embedding = await _embedder.embed_text(f"{name} {value}")
    component = Component(
        model_id=model_id,
        name=name,
        value=value,
        confidence=0.95,
        authority_source="seeded-eval",
        authority_weight=authority_weight,
        last_verified_at=datetime.now(UTC),
        embedding=embedding,
    )
    db_session.add(component)
    await db_session.flush()
    return component


async def _link_source(
    db_session,
    *,
    component_id,
    connector_id,
    connector_type: ConnectorType,
    external_id: str,
    content: str,
    label_metadata: dict,
) -> None:
    doc = SourceDocument(
        connector_id=connector_id,
        connector_type=connector_type,
        external_id=external_id,
        content=content,
        author="seed",
        source_url=f"https://example.com/{external_id}",
        created_at_source=datetime.now(UTC),
        metadata_json=label_metadata,
        processed_at=datetime.now(UTC),
    )
    db_session.add(doc)
    await db_session.flush()
    db_session.add(
        ComponentSource(
            component_id=component_id,
            source_document_id=doc.id,
            extraction_context=content,
            extractor_name="structured_llm",
            extractor_kind="llm_structured",
            extractor_schema_version="fact_extraction.v1",
        )
    )
    await db_session.flush()


async def _seed_all_connectors(db_session, workspace_id):
    """Create one connector per type and return a dict keyed by ConnectorType."""
    connectors = {}
    for ct in (ConnectorType.SLACK, ConnectorType.NOTION, ConnectorType.ZOOM, ConnectorType.GONG):
        connectors[ct] = await _seed_connector(db_session, workspace_id, ct)
    return connectors


async def _seed_full_dataset(db_session, workspace):
    """Seed all 25 eval fixture components with matching source links."""
    c = await _seed_all_connectors(db_session, workspace.id)

    pricing = await _seed_model(db_session, workspace.id, "Pricing", "Pricing facts")
    roadmap = await _seed_model(db_session, workspace.id, "Roadmap", "Roadmap facts")
    meetings = await _seed_model(db_session, workspace.id, "Zoom Insights", "Meeting facts")
    decisions = await _seed_model(db_session, workspace.id, "Decisions", "Decision facts")

    # --- Pricing domain (5 cases) ---
    enterprise = await _seed_component(
        db_session, model_id=pricing.id,
        name="Enterprise Plan",
        value="Enterprise pricing is $600/seat with annual terms.",
    )
    await _link_source(
        db_session, component_id=enterprise.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-enterprise-plan",
        content="Enterprise pricing is $600/seat.",
        label_metadata={"page_title": "Pricing Handbook"},
    )
    await _link_source(
        db_session, component_id=enterprise.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-enterprise-plan",
        content="Decision: enterprise stays at $600/seat.",
        label_metadata={"channel_name": "pricing"},
    )

    starter = await _seed_component(
        db_session, model_id=pricing.id,
        name="Starter Plan",
        value="Starter Plan is $29/mo.",
    )
    await _link_source(
        db_session, component_id=starter.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-starter-plan",
        content="Starter Plan is $29/mo.",
        label_metadata={"page_title": "Pricing Handbook"},
    )

    growth = await _seed_component(
        db_session, model_id=pricing.id,
        name="Growth Plan",
        value="Growth tier is $149/mo with team features included.",
    )
    await _link_source(
        db_session, component_id=growth.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-growth-plan",
        content="Growth Plan: $149/mo with team features.",
        label_metadata={"page_title": "Pricing Handbook"},
    )

    annual_discount = await _seed_component(
        db_session, model_id=pricing.id,
        name="Annual Discount Policy",
        value="We offer a 20% discount for annual commitments across all plans.",
    )
    await _link_source(
        db_session, component_id=annual_discount.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-annual-discount",
        content="Annual discount: 20% off for annual billing on all plans.",
        label_metadata={"page_title": "Pricing Handbook"},
    )

    # --- Blocker domain (5 cases) ---
    sso_blocker = await _seed_component(
        db_session, model_id=roadmap.id,
        name="SSO Blocker",
        value="Active blockers: SSO is blocked by engineering bandwidth and analytics reliability work.",
    )
    await _link_source(
        db_session, component_id=sso_blocker.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-sso-blocker",
        content="SSO is blocked by engineering bandwidth.",
        label_metadata={"channel_name": "roadmap"},
    )
    await _link_source(
        db_session, component_id=sso_blocker.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-sso-blocker",
        content="Meeting blocker: engineering bandwidth is the blocker for SSO.",
        label_metadata={"meeting_topic": "Weekly Product Review"},
    )

    meeting_blocker = await _seed_component(
        db_session, model_id=meetings.id,
        name="Blocker in Weekly Product Review",
        value="From meetings: current blockers include waiting on legal approval.",
    )
    await _link_source(
        db_session, component_id=meeting_blocker.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-legal-blocker",
        content="Current blocker: waiting on legal approval.",
        label_metadata={"meeting_topic": "Weekly Product Review"},
    )

    api_migration_blocker = await _seed_component(
        db_session, model_id=roadmap.id,
        name="API Migration Blocker",
        value="API migration is blocked by downstream partner integration not being ready.",
    )
    await _link_source(
        db_session, component_id=api_migration_blocker.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-api-migration-blocker",
        content="Blocker: downstream partner integration not ready for API migration.",
        label_metadata={"channel_name": "engineering"},
    )

    mobile_release_blocker = await _seed_component(
        db_session, model_id=roadmap.id,
        name="Mobile Release Blocker",
        value="Mobile release is blocked pending app store review approval.",
    )
    await _link_source(
        db_session, component_id=mobile_release_blocker.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-mobile-release-blocker",
        content="Blocker: waiting on app store review for mobile release.",
        label_metadata={"channel_name": "mobile"},
    )

    # --- Roadmap domain (5 cases) ---
    sso_launch = await _seed_component(
        db_session, model_id=roadmap.id,
        name="SSO Launch Target",
        value="SSO launch target is Q3.",
    )
    await _link_source(
        db_session, component_id=sso_launch.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-sso-launch",
        content="SSO launch target is Q3.",
        label_metadata={"page_title": "Roadmap"},
    )

    analytics_rewrite = await _seed_component(
        db_session, model_id=roadmap.id,
        name="Analytics Rewrite Target",
        value="Analytics rewrite is targeted for Q4 delivery.",
    )
    await _link_source(
        db_session, component_id=analytics_rewrite.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-analytics-rewrite",
        content="Analytics rewrite target: Q4.",
        label_metadata={"page_title": "Roadmap"},
    )

    mobile_app_launch = await _seed_component(
        db_session, model_id=roadmap.id,
        name="Mobile App Launch",
        value="Mobile app launch is planned for Q2 with cross-platform support.",
    )
    await _link_source(
        db_session, component_id=mobile_app_launch.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-mobile-launch",
        content="Mobile app launch: Q2 with cross-platform mobile support.",
        label_metadata={"page_title": "Roadmap"},
    )
    await _link_source(
        db_session, component_id=mobile_app_launch.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-mobile-launch",
        content="Confirmed: mobile app targets Q2 launch.",
        label_metadata={"channel_name": "product"},
    )

    # --- Decision domain (5 cases) ---
    meeting_decision = await _seed_component(
        db_session, model_id=meetings.id,
        name="Decision in Weekly Product Review",
        value="Meeting decision: we decided the launch timing — ship the onboarding flow next Tuesday.",
    )
    await _link_source(
        db_session, component_id=meeting_decision.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-onboarding-decision",
        content="We decided to ship onboarding next Tuesday.",
        label_metadata={"meeting_topic": "Weekly Product Review"},
    )

    db_migration = await _seed_component(
        db_session, model_id=decisions.id,
        name="DB Migration Decision",
        value="We decided to migrate to Postgres 16 using a rolling upgrade strategy.",
    )
    await _link_source(
        db_session, component_id=db_migration.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-db-migration",
        content="Decision: migrate to Postgres 16 with rolling upgrade.",
        label_metadata={"channel_name": "engineering"},
    )

    auth_provider = await _seed_component(
        db_session, model_id=decisions.id,
        name="Auth Provider Decision",
        value="We chose Auth0 as our authentication provider.",
    )
    await _link_source(
        db_session, component_id=auth_provider.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-auth-provider",
        content="Decision: going with Auth0 for authentication.",
        label_metadata={"channel_name": "engineering"},
    )
    await _link_source(
        db_session, component_id=auth_provider.id,
        connector_id=c[ConnectorType.NOTION].id, connector_type=ConnectorType.NOTION,
        external_id="notion-auth-provider",
        content="Auth provider decision: Auth0 selected.",
        label_metadata={"page_title": "Architecture Decisions"},
    )

    framework_decision = await _seed_component(
        db_session, model_id=decisions.id,
        name="Framework Decision",
        value="We picked FastAPI for the new service framework.",
    )
    await _link_source(
        db_session, component_id=framework_decision.id,
        connector_id=c[ConnectorType.SLACK].id, connector_type=ConnectorType.SLACK,
        external_id="slack-framework-decision",
        content="Decision: picked FastAPI for the new service.",
        label_metadata={"channel_name": "engineering"},
    )

    # --- Meeting domain (5 cases) ---
    # meeting-001 reuses Decision in Weekly Product Review + Blocker in Weekly Product Review (already seeded)

    action_item_eng = await _seed_component(
        db_session, model_id=meetings.id,
        name="Action Item from Engineering Sync",
        value="Action item: run load test on staging before the release.",
    )
    await _link_source(
        db_session, component_id=action_item_eng.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-eng-action-item",
        content="AI: run load test on staging before release.",
        label_metadata={"meeting_topic": "Engineering Sync"},
    )

    sales_pipeline = await _seed_component(
        db_session, model_id=meetings.id,
        name="Sales Pipeline Update",
        value="Enterprise pipeline is growing with three new deals in negotiation.",
    )
    await _link_source(
        db_session, component_id=sales_pipeline.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-sales-pipeline",
        content="Sales update: enterprise pipeline growing, three new deals.",
        label_metadata={"meeting_topic": "Sales Standup"},
    )
    await _link_source(
        db_session, component_id=sales_pipeline.id,
        connector_id=c[ConnectorType.GONG].id, connector_type=ConnectorType.GONG,
        external_id="gong-sales-pipeline",
        content="Enterprise pipeline update: three deals in negotiation.",
        label_metadata={"location": "Sales Call Recording"},
    )

    retro_concern = await _seed_component(
        db_session, model_id=meetings.id,
        name="Retro Concern",
        value="Concern raised: deployment rollback process needs improvement.",
    )
    await _link_source(
        db_session, component_id=retro_concern.id,
        connector_id=c[ConnectorType.ZOOM].id, connector_type=ConnectorType.ZOOM,
        external_id="zoom-retro-concern",
        content="Retro: deployment rollback process needs improvement.",
        label_metadata={"meeting_topic": "Sprint Retrospective"},
    )

    customer_feedback = await _seed_component(
        db_session, model_id=meetings.id,
        name="Customer Feedback Summary",
        value="Customer feedback: onboarding documentation needs to be clearer.",
    )
    await _link_source(
        db_session, component_id=customer_feedback.id,
        connector_id=c[ConnectorType.GONG].id, connector_type=ConnectorType.GONG,
        external_id="gong-customer-feedback",
        content="Customer call: onboarding documentation needs improvement.",
        label_metadata={"location": "Customer Success Call"},
    )

    return c


class TestStartupGoldSet:
    async def test_gold_set_regression_thresholds(self, db_session, workspace):
        """Original 10-case gold set passes regression thresholds."""
        await _seed_full_dataset(db_session, workspace)

        summary = await StartupEvalHarness(QueryService(db_session)).run(
            workspace_id=workspace.id,
            cases=STARTUP_GOLD_SET,
        )

        assert len(summary.cases) == len(STARTUP_GOLD_SET)
        assert summary.average_retrieval_hit_quality >= 0.8
        assert summary.average_extracted_fact_correctness >= 0.8
        assert summary.average_final_answer_correctness >= 0.75

    async def test_full_25_fixture_regression(self, db_session, workspace):
        """All 25 JSONL fixtures pass against fully seeded data."""
        await _seed_full_dataset(db_session, workspace)
        all_cases = load_default_cases()
        assert len(all_cases) == 25

        summary = await StartupEvalHarness(QueryService(db_session)).run(
            workspace_id=workspace.id,
            cases=all_cases,
        )

        assert summary.total == 25
        assert summary.pass_threshold == 0.5
        assert summary.confidence_calibration_error >= 0.0
        assert summary.average_retrieval_hit_quality >= 0.75
        assert summary.average_extracted_fact_correctness >= 0.75
        assert summary.average_final_answer_correctness >= 0.70

        # Every domain should have at least one passing case
        for ds in summary.domain_summaries:
            assert ds.pass_rate > 0, f"Domain {ds.domain} has 0% pass rate"

    async def test_domain_filter_against_seeded_data(self, db_session, workspace):
        """Each domain filter returns only matching cases and they all pass."""
        await _seed_full_dataset(db_session, workspace)

        for domain in ("pricing", "blocker", "roadmap", "decision", "meeting"):
            cases = load_fixtures(domains=[domain])
            assert len(cases) == 5, f"Expected 5 cases for {domain}"

            summary = await StartupEvalHarness(QueryService(db_session)).run(
                workspace_id=workspace.id,
                cases=cases,
            )
            assert summary.total == 5
            assert len(summary.domain_summaries) == 1
            assert summary.domain_summaries[0].domain == domain
