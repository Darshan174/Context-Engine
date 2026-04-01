from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import (
    Component,
    ComponentSource,
    Connector,
    ConnectorStatus,
    ConnectorType,
    KnowledgeModel,
    Relationship,
    RelationshipSentiment,
    RelationshipType,
    ReviewItem,
    SourceDocument,
)


async def _create_model(db_session, workspace_id, name: str, description: str) -> KnowledgeModel:
    model = KnowledgeModel(
        workspace_id=workspace_id,
        name=name,
        description=description,
    )
    db_session.add(model)
    await db_session.flush()
    return model


async def _create_component(
    db_session,
    *,
    model_id,
    name: str,
    value: str,
    confidence: float = 0.9,
    authority_source: str | None = None,
    authority_weight: float = 0.5,
    last_verified_at: datetime | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> Component:
    component = Component(
        model_id=model_id,
        name=name,
        value=value,
        confidence=confidence,
        authority_source=authority_source,
        authority_weight=authority_weight,
        valid_from=valid_from or datetime.now(UTC),
        valid_to=valid_to,
        last_verified_at=last_verified_at or datetime.now(UTC),
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
    author: str,
    url: str,
    content: str,
    created_at_source: datetime,
) -> SourceDocument:
    document = SourceDocument(
        connector_id=connector_id,
        connector_type=connector_type,
        external_id=external_id,
        content=content,
        author=author,
        source_url=url,
        created_at_source=created_at_source,
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        ComponentSource(
            component_id=component_id,
            source_document_id=document.id,
            extraction_context=content[:120],
        )
    )
    await db_session.flush()
    return document


async def _create_relationship(
    db_session,
    *,
    source_component_id,
    target_component_id,
    relationship_type: RelationshipType,
    sentiment: RelationshipSentiment = RelationshipSentiment.NEUTRAL,
    confidence: float = 0.8,
    description: str | None = None,
) -> Relationship:
    relationship = Relationship(
        source_component_id=source_component_id,
        target_component_id=target_component_id,
        relationship_type=relationship_type,
        sentiment=sentiment,
        confidence=confidence,
        description=description,
    )
    db_session.add(relationship)
    await db_session.flush()
    return relationship


class TestQueryAPI:
    async def test_post_query_returns_structured_match(self, client, db_session, workspace):
        # Create a connector so SourceDocuments have an owner
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing and packaging")
        enterprise = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise",
            value="Custom pricing, starting $500/seat",
            confidence=0.9,
            authority_source="CEO Slack message",
            last_verified_at=datetime.now(UTC) - timedelta(days=2),
        )
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Starter Plan",
            value="$29/mo",
            confidence=0.95,
            authority_source="Pricing handbook",
            last_verified_at=datetime.now(UTC) - timedelta(days=1),
        )
        await _link_source(
            db_session,
            component_id=enterprise.id,
            connector_id=conn.id,
            connector_type=ConnectorType.SLACK,
            external_id="slack-pricing-1",
            author="CEO",
            url="https://slack.example.com/pricing",
            content="Enterprise pricing starts at $500/seat.",
            created_at_source=datetime.now(UTC) - timedelta(days=1),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is our enterprise pricing?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["question"] == "What is our enterprise pricing?"
        assert body["confidence"] > 0.5
        assert body["freshness"] == "current"
        assert "answeredAt" in body
        assert any(item["name"] == "Enterprise" for item in body["components"])
        assert any(item["model"] == "Pricing" for item in body["components"])
        assert any(source["type"] == "slack" for source in body["sources"])
        assert "$500/seat" in body["answer"]

    async def test_get_query_returns_404_for_missing_workspace(self, client):
        resp = await client.get(
            "/api/query",
            params={
                "q": "What is our pricing?",
                "workspace_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            },
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Workspace not found"

    async def test_query_returns_empty_result_when_no_match_exists(self, client, db_session, workspace):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing and packaging")
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise",
            value="Custom pricing, starting $500/seat",
            confidence=0.9,
            last_verified_at=datetime.now(UTC),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What are our renewal risks?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"] == []
        assert body["sources"] == []
        assert body["confidence"] == 0.0
        assert "could not find matching structured context" in body["answer"].lower()

    async def test_query_marks_results_possibly_stale_after_seven_days(
        self, client, db_session, workspace
    ):
        roadmap = await _create_model(db_session, workspace.id, "Roadmap", "Roadmap work")
        await _create_component(
            db_session,
            model_id=roadmap.id,
            name="Deprecation Plan",
            value="Migration begins next quarter.",
            confidence=0.88,
            last_verified_at=datetime.now(UTC) - timedelta(days=8),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the deprecation plan?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        assert resp.json()["freshness"] == "possibly_stale"

    async def test_query_marks_results_stale_after_thirty_days(
        self, client, db_session, workspace
    ):
        policies = await _create_model(db_session, workspace.id, "Policies", "Legacy policies")
        await _create_component(
            db_session,
            model_id=policies.id,
            name="Legacy Contract Policy",
            value="Legacy contracts renew on prior terms.",
            confidence=0.8,
            last_verified_at=datetime.now(UTC) - timedelta(days=31),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the legacy contract policy?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        assert resp.json()["freshness"] == "stale"

    async def test_query_respects_min_confidence_filter(self, client, db_session, workspace):
        features = await _create_model(db_session, workspace.id, "Features", "Feature decisions")
        await _create_component(
            db_session,
            model_id=features.id,
            name="Analytics Dashboard",
            value="Targeting Q3",
            confidence=0.4,
            last_verified_at=datetime.now(UTC),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the analytics dashboard status?",
                "workspace_id": str(workspace.id),
                "min_confidence": 0.5,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["components"] == []

    async def test_get_query_respects_model_filter(self, client, db_session, workspace):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        customers = await _create_model(
            db_session,
            workspace.id,
            "Customers",
            "Customer segmentation details",
        )
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$500/seat",
            confidence=0.9,
            last_verified_at=datetime.now(UTC),
        )
        await _create_component(
            db_session,
            model_id=customers.id,
            name="Enterprise Segment",
            value="Targeting accounts with >1,000 employees",
            confidence=0.91,
            last_verified_at=datetime.now(UTC),
        )

        resp = await client.get(
            "/api/query",
            params=[
                ("q", "What do we know about enterprise?"),
                ("workspace_id", str(workspace.id)),
                ("models", "Pricing"),
            ],
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"]
        assert {item["model"] for item in body["components"]} == {"Pricing"}

    async def test_get_query_respects_max_age_days(self, client, db_session, workspace):
        roadmap = await _create_model(db_session, workspace.id, "Roadmap", "Roadmap details")
        await _create_component(
            db_session,
            model_id=roadmap.id,
            name="Legacy Launch Date",
            value="Launch moved to next quarter.",
            confidence=0.86,
            last_verified_at=datetime.now(UTC) - timedelta(days=10),
        )

        resp = await client.get(
            "/api/query",
            params={
                "q": "What is the legacy launch date?",
                "workspace_id": str(workspace.id),
                "max_age_days": 7,
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"] == []
        assert body["confidence"] == 0.0

    async def test_query_includes_relationship_context_for_causal_questions(
        self, client, db_session, workspace
    ):
        features = await _create_model(db_session, workspace.id, "Features", "Feature work")
        sso = await _create_component(
            db_session,
            model_id=features.id,
            name="SSO Integration",
            value="Deprioritized due to engineering bandwidth",
            confidence=0.9,
            last_verified_at=datetime.now(UTC) - timedelta(days=2),
        )
        analytics = await _create_component(
            db_session,
            model_id=features.id,
            name="Analytics Dashboard",
            value="In development, Q3 target",
            confidence=0.85,
            last_verified_at=datetime.now(UTC) - timedelta(days=1),
        )
        await _create_relationship(
            db_session,
            source_component_id=sso.id,
            target_component_id=analytics.id,
            relationship_type=RelationshipType.BLOCKED_BY,
            sentiment=RelationshipSentiment.NEGATIVE,
            confidence=0.92,
            description="Analytics Dashboard work is consuming the same engineering bandwidth.",
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "Why is SSO Integration delayed?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"]
        assert body["components"][0]["name"] == "SSO Integration"
        assert "blocked by Analytics Dashboard" in body["answer"]
        assert "engineering bandwidth" in body["answer"]

    async def test_query_deduplicates_identical_component_facts(
        self, client, db_session, workspace
    ):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        sales = await _create_model(db_session, workspace.id, "Sales", "Sales enablement")
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Pro Plan",
            value="$99/mo",
            confidence=0.95,
            last_verified_at=datetime.now(UTC),
        )
        await _create_component(
            db_session,
            model_id=sales.id,
            name="Pro Plan",
            value="$99/mo",
            confidence=0.92,
            last_verified_at=datetime.now(UTC),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the Pro Plan?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200

    async def test_query_ignores_historical_component_versions(
        self, client, db_session, workspace
    ):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        old_component = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$500/seat",
            confidence=0.9,
            last_verified_at=datetime.now(UTC) - timedelta(days=2),
        )
        new_component = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$600/seat",
            confidence=0.86,
            last_verified_at=datetime.now(UTC) - timedelta(days=1),
        )
        old_component.valid_to = datetime.now(UTC) - timedelta(hours=12)
        old_component.superseded_by_id = new_component.id
        db_session.add(
            ReviewItem(
                component_id=old_component.id,
                status="superseded",
                severity="low",
                kind="superseded_fact",
                title="Enterprise Plan is now historical",
                summary="A newer enterprise plan superseded this value.",
                confidence=old_component.confidence,
            )
        )
        await db_session.flush()

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the enterprise plan price?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"]
        assert body["components"][0]["value"] == "$600/seat"
        assert all(component["value"] != "$500/seat" for component in body["components"])

    async def test_query_returns_review_metadata_and_source_documents(
        self, client, db_session, workspace
    ):
        conn = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.SLACK,
            status=ConnectorStatus.CONNECTED,
            config={},
        )
        db_session.add(conn)
        await db_session.flush()

        roadmap = await _create_model(db_session, workspace.id, "Roadmap", "Roadmap work")
        component = await _create_component(
            db_session,
            model_id=roadmap.id,
            name="SSO Launch Target",
            value="Q3",
            confidence=0.55,
            last_verified_at=datetime.now(UTC),
        )
        db_session.add(
            ReviewItem(
                component_id=component.id,
                status="needs_review",
                severity="medium",
                kind="low_confidence",
                title="SSO Launch Target extracted with low confidence",
                summary="The roadmap target still needs human confirmation.",
                confidence=0.55,
            )
        )
        await db_session.flush()

        await _link_source(
            db_session,
            component_id=component.id,
            connector_id=conn.id,
            connector_type=ConnectorType.SLACK,
            external_id="slack-roadmap-1",
            author="PM",
            url="https://slack.example.com/roadmap",
            content="decision: SSO launches in Q3.",
            created_at_source=datetime.now(UTC),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the SSO launch target?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        component_body = resp.json()["components"][0]
        assert component_body["review_status"] == "needs_review"
        assert component_body["review_summary"] == "The roadmap target still needs human confirmation."
        assert component_body["review_item_id"] is not None
        assert component_body["valid_from"] is not None
        assert component_body["valid_to"] is None
        assert component_body["superseded_by"] is None
        assert component_body["temporal_state"] is None
        assert component_body["source_documents"][0]["connector_type"] == "slack"
        assert component_body["source_documents"][0]["label"] is not None

    async def test_query_prefers_higher_authority_fact_when_values_conflict(
        self, client, db_session, workspace
    ):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$450/seat",
            confidence=0.94,
            authority_source="Pricing spec",
            authority_weight=0.95,
            last_verified_at=datetime.now(UTC),
        )
        await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$400/seat",
            confidence=0.97,
            authority_source="Slack thread",
            authority_weight=0.55,
            last_verified_at=datetime.now(UTC),
        )

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the enterprise plan price?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"][0]["value"] == "$450/seat"
        assert body["components"][0]["authority_weight"] == 0.95

    async def test_query_prefers_approved_current_truth_when_scores_are_close(
        self, client, db_session, workspace
    ):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        reviewed = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$600/seat",
            confidence=0.9,
            authority_source="Pricing handbook",
            authority_weight=0.88,
            last_verified_at=datetime.now(UTC),
        )
        pending = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Pricing Notes",
            value="$600/seat provisional",
            confidence=0.95,
            authority_source="Slack thread",
            authority_weight=0.82,
            last_verified_at=datetime.now(UTC),
        )
        db_session.add(
            ReviewItem(
                component_id=reviewed.id,
                status="approved",
                severity="low",
                kind="review_item",
                title="Enterprise pricing approved",
                summary="Pricing handbook is current.",
                confidence=0.9,
            )
        )
        db_session.add(
            ReviewItem(
                component_id=pending.id,
                status="needs_review",
                severity="medium",
                kind="low_confidence",
                title="Slack pricing note still needs review",
                summary="Slack note is not yet approved.",
                confidence=0.55,
            )
        )
        await db_session.flush()

        resp = await client.post(
            "/api/query",
            json={
                "question": "What is the current enterprise plan price?",
                "workspace_id": str(workspace.id),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["components"][0]["id"] == str(reviewed.id)
        assert body["components"][0]["review_status"] == "approved"

    async def test_query_supports_as_of_historical_answers(
        self, client, db_session, workspace
    ):
        pricing = await _create_model(db_session, workspace.id, "Pricing", "Pricing information")
        old_component = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$500/seat",
            confidence=0.9,
            authority_weight=0.9,
            valid_from=datetime(2026, 3, 1, tzinfo=UTC),
            valid_to=datetime(2026, 3, 20, tzinfo=UTC),
            last_verified_at=datetime(2026, 3, 15, tzinfo=UTC),
        )
        new_component = await _create_component(
            db_session,
            model_id=pricing.id,
            name="Enterprise Plan",
            value="$600/seat",
            confidence=0.92,
            authority_weight=0.9,
            valid_from=datetime(2026, 3, 20, tzinfo=UTC),
            last_verified_at=datetime(2026, 3, 20, tzinfo=UTC),
        )
        old_component.superseded_by_id = new_component.id
        db_session.add(
            ReviewItem(
                component_id=old_component.id,
                status="superseded",
                severity="low",
                kind="superseded_fact",
                title="Enterprise Plan is now historical",
                summary="Superseded by a newer plan.",
                confidence=old_component.confidence,
            )
        )
        await db_session.flush()

        current = await client.post(
            "/api/query",
            json={
                "question": "What is the enterprise plan price?",
                "workspace_id": str(workspace.id),
            },
        )
        historical = await client.post(
            "/api/query",
            json={
                "question": "What is the enterprise plan price?",
                "workspace_id": str(workspace.id),
                "as_of": "2026-03-10T00:00:00Z",
            },
        )

        assert current.status_code == 200
        assert historical.status_code == 200
        assert current.json()["components"][0]["value"] == "$600/seat"
        assert historical.json()["components"][0]["value"] == "$500/seat"
        assert historical.json()["answer"].startswith("As of 2026-03-10")
