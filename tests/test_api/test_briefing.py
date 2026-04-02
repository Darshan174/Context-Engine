from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.connector import Connector, ConnectorStatus
from app.models.job import SyncJob, SyncJobStatus
from app.models.knowledge import (
    Component,
    ComponentSource,
    KnowledgeModel,
    Relationship,
    RelationshipType,
)
from app.models.review import ReviewDecision, ReviewItem
from app.models.source import ConnectorType, SourceDocument


async def _seed_connector(db_session, workspace, *, connector_type=ConnectorType.SLACK):
    connector = Connector(
        workspace_id=workspace.id,
        connector_type=connector_type,
        status=ConnectorStatus.CONNECTED,
        config={},
    )
    db_session.add(connector)
    await db_session.flush()
    return connector


async def _seed_model(db_session, workspace, name="Decisions"):
    model = KnowledgeModel(
        workspace_id=workspace.id,
        name=name,
        description=f"{name} model",
    )
    db_session.add(model)
    await db_session.flush()
    return model


async def _seed_source_document(
    db_session,
    connector,
    *,
    external_id: str,
    content: str,
    metadata: dict,
    created_at_source: datetime | None = None,
    ingested_at: datetime | None = None,
):
    doc = SourceDocument(
        connector_id=connector.id,
        connector_type=connector.connector_type,
        external_id=external_id,
        content=content,
        author="founder@example.com",
        source_url=f"https://example.com/{external_id}",
        created_at_source=created_at_source,
        ingested_at=ingested_at or datetime.now(timezone.utc),
        metadata_json=metadata,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


async def _link_component_source(db_session, component, document, *, extracted_value: str):
    db_session.add(
        ComponentSource(
            component_id=component.id,
            source_document_id=document.id,
            extraction_context=f"Extracted from {document.label}",
            extracted_value=extracted_value,
            extractor_name="regex",
            extractor_kind="regex",
            extractor_schema_version="fact_extraction.v1",
        )
    )
    await db_session.flush()


class TestDecisionRegisterApi:
    async def test_list_decisions_returns_current_decisions_with_rationale_and_review_history(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace)

        historical_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:history",
            content="decision: ship onboarding this Friday",
            metadata={"channel_name": "product-history"},
            created_at_source=datetime.now(timezone.utc) - timedelta(days=7),
        )
        current_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:current",
            content="decision: ship onboarding next Tuesday",
            metadata={"channel_name": "weekly-product-review"},
            created_at_source=datetime.now(timezone.utc) - timedelta(days=1),
        )

        current = Component(
            model_id=model.id,
            name="Decision in Weekly Product Review",
            value="Ship onboarding next Tuesday.",
            confidence=0.93,
            authority_weight=0.90,
            valid_from=datetime.now(timezone.utc) - timedelta(days=1),
            last_verified_at=datetime.now(timezone.utc),
        )
        db_session.add(current)
        await db_session.flush()

        historical = Component(
            model_id=model.id,
            name="Decision in Weekly Product Review",
            value="Ship onboarding this Friday.",
            confidence=0.81,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(days=8),
            valid_to=datetime.now(timezone.utc) - timedelta(days=1),
            superseded_by_id=current.id,
            last_verified_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_stale=True,
        )
        db_session.add(historical)
        await db_session.flush()

        review = ReviewItem(
            component_id=current.id,
            status="approved",
            severity="low",
            kind="fact_update",
            title="Decision approved",
            summary="Operator confirmed the current launch decision.",
            confidence=0.93,
        )
        db_session.add(review)
        await db_session.flush()
        db_session.add(
            ReviewDecision(
                review_item_id=review.id,
                previous_status="needs_review",
                new_status="approved",
                actor_type="operator",
                note="Reviewed and confirmed.",
            )
        )
        await db_session.flush()

        await _link_component_source(
            db_session,
            current,
            current_doc,
            extracted_value="Ship onboarding next Tuesday.",
        )
        await _link_component_source(
            db_session,
            historical,
            historical_doc,
            extracted_value="Ship onboarding this Friday.",
        )
        blocker = Component(
            model_id=model.id,
            name="Blocker in Weekly Product Review",
            value="Need legal sign-off before launch.",
            confidence=0.88,
            authority_weight=0.90,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=20),
            last_verified_at=datetime.now(timezone.utc),
        )
        db_session.add(blocker)
        await db_session.flush()
        db_session.add(
            Relationship(
                source_component_id=blocker.id,
                target_component_id=current.id,
                relationship_type=RelationshipType.BLOCKED_BY,
                confidence=0.9,
                description="Launch decision is blocked by legal sign-off.",
            )
        )
        await db_session.commit()

        response = await client.get(
            "/api/decisions",
            params={"workspace_id": str(workspace.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == str(current.id)
        assert body[0]["is_current"] is True
        assert body[0]["summary"] == "Operator confirmed the current launch decision."
        assert body[0]["source_document_id"] == str(current_doc.id)
        assert body[0]["source_label"] == "weekly-product-review"
        assert body[0]["connector_type"] == "slack"
        assert body[0]["related_blocker"] == "Need legal sign-off before launch."
        assert body[0]["decision_history"][0]["new_status"] == "approved"
        assert body[0]["rationale_sources"][0]["label"] == "weekly-product-review"

    async def test_decision_history_returns_current_and_superseded_versions(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace)

        historical_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:history",
            content="decision: use Auth0",
            metadata={"channel_name": "product-history"},
        )
        current_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:current",
            content="decision: use Auth0",
            metadata={"channel_name": "product"},
        )

        current = Component(
            model_id=model.id,
            name="Decision in Product",
            value="Use Auth0.",
            confidence=0.95,
            authority_weight=0.90,
            valid_from=datetime.now(timezone.utc) - timedelta(days=2),
            last_verified_at=datetime.now(timezone.utc),
        )
        db_session.add(current)
        await db_session.flush()

        historical = Component(
            model_id=model.id,
            name="Decision in Product",
            value="Use Okta.",
            confidence=0.70,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(days=10),
            valid_to=datetime.now(timezone.utc) - timedelta(days=2),
            superseded_by_id=current.id,
            last_verified_at=datetime.now(timezone.utc) - timedelta(days=2),
            is_stale=True,
        )
        db_session.add(historical)
        await db_session.flush()

        await _link_component_source(db_session, current, current_doc, extracted_value="Use Auth0.")
        await _link_component_source(
            db_session,
            historical,
            historical_doc,
            extracted_value="Use Okta.",
        )

        response = await client.get(
            f"/api/decisions/{current.id}/history",
            params={"workspace_id": str(workspace.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["current_decision_id"] == str(current.id)
        assert [entry["value"] for entry in body["entries"]] == [
            "Use Auth0.",
            "Use Okta.",
        ]
        assert body["entries"][1]["is_current"] is False

    async def test_decision_history_supports_cursor_pagination(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace)

        versions: list[Component] = []
        for index, value in enumerate(("Use Auth0.", "Use Okta.", "Use Clerk."), start=1):
            doc = await _seed_source_document(
                db_session,
                connector,
                external_id=f"slack:decision:{index}",
                content=f"decision: {value}",
                metadata={"channel_name": f"decision-{index}"},
            )
            component = Component(
                model_id=model.id,
                name="Auth Provider Decision",
                value=value,
                confidence=0.8 + (index * 0.05),
                authority_weight=0.8,
                valid_from=datetime.now(timezone.utc) - timedelta(days=4 - index),
                valid_to=None if index == 3 else datetime.now(timezone.utc) - timedelta(days=3 - index),
                last_verified_at=datetime.now(timezone.utc),
                is_stale=index != 3,
            )
            db_session.add(component)
            await db_session.flush()
            versions.append(component)
            await _link_component_source(db_session, component, doc, extracted_value=value)

        versions[0].superseded_by_id = versions[1].id
        versions[1].superseded_by_id = versions[2].id
        await db_session.commit()

        first = await client.get(
            f"/api/decisions/{versions[2].id}/history",
            params={"workspace_id": str(workspace.id), "limit": 2},
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["total_versions"] == 3
        assert first_body["has_more"] is True
        assert len(first_body["entries"]) == 2
        assert first_body["next_cursor"] is not None

        second = await client.get(
            f"/api/decisions/{versions[2].id}/history",
            params={
                "workspace_id": str(workspace.id),
                "limit": 2,
                "cursor": first_body["next_cursor"],
            },
        )
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["has_more"] is False
        assert [entry["value"] for entry in second_body["entries"]] == ["Use Auth0."]


class TestFounderBriefApi:
    async def test_founder_brief_summarizes_changed_facts_conflicts_risks_and_failures(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace, name="Ops")
        source_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:ops",
            content="decision: launch next Tuesday\nblocker: need audit approval",
            metadata={"channel_name": "ops"},
        )

        changed = Component(
            model_id=model.id,
            name="Decision in #ops",
            value="Launch next Tuesday.",
            confidence=0.92,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=12),
            last_verified_at=datetime.now(timezone.utc),
        )
        blocker = Component(
            model_id=model.id,
            name="Blocker in #ops",
            value="Need audit approval.",
            confidence=0.84,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=8),
            last_verified_at=datetime.now(timezone.utc),
        )
        risky = Component(
            model_id=model.id,
            name="Decision in #ops",
            value="Change billing backend this week.",
            confidence=0.42,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=4),
            last_verified_at=datetime.now(timezone.utc),
            is_stale=True,
        )
        conflicting = Component(
            model_id=model.id,
            name="Decision in #ops",
            value="Enterprise is $500/seat.",
            confidence=0.66,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=2),
            last_verified_at=datetime.now(timezone.utc),
        )
        db_session.add_all([changed, blocker, risky, conflicting])
        await db_session.flush()

        for component in (changed, blocker, risky, conflicting):
            await _link_component_source(db_session, component, source_doc, extracted_value=component.value)

        review = ReviewItem(
            component_id=conflicting.id,
            status="needs_review",
            severity="high",
            kind="conflict",
            title="Pricing conflict",
            summary="Slack pricing statement conflicts with higher-authority pricing.",
            confidence=0.66,
            suggested_action="Review before repeating externally.",
        )
        db_session.add(review)
        db_session.add(
            SyncJob(
                connector_id=connector.id,
                job_type="sync",
                status=SyncJobStatus.FAILED,
                error_type="AuthenticationError",
                error_message="Token expired",
                completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        await db_session.commit()

        response = await client.get(
            "/api/founder-brief",
            params={"workspace_id": str(workspace.id), "lookback_days": 7},
        )

        assert response.status_code == 200
        body = response.json()
        assert any(item["name"] == "Decision in #ops" for item in body["changed_facts"])
        assert any(item["name"] == "Blocker in #ops" for item in body["new_blockers"])
        assert body["open_conflicts"][0]["title"] == "Pricing conflict"
        assert any(item["reason"] for item in body["stale_high_risk_items"])
        assert body["recent_connector_failures"][0]["error_type"] == "AuthenticationError"


class TestTimelineApi:
    async def test_timeline_includes_decisions_reviews_ingests_and_failures(
        self, client, workspace, db_session
    ):
        now = datetime.now(timezone.utc)
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace, name="Timeline")
        older_document = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:timeline-old",
            content="decision: launch next Friday",
            metadata={"channel_name": "timeline-old"},
            ingested_at=now - timedelta(hours=2),
        )
        document = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:timeline",
            content="decision: launch next Tuesday",
            metadata={"channel_name": "timeline"},
            ingested_at=now - timedelta(hours=1),
        )

        decision = Component(
            model_id=model.id,
            name="Decision in #timeline",
            value="Launch next Tuesday.",
            confidence=0.9,
            authority_weight=0.75,
            valid_from=now - timedelta(hours=3),
            last_verified_at=now - timedelta(hours=1, minutes=50),
        )
        db_session.add(decision)
        await db_session.flush()
        await _link_component_source(
            db_session,
            decision,
            older_document,
            extracted_value="Launch next Friday.",
        )
        await _link_component_source(
            db_session,
            decision,
            document,
            extracted_value="Launch next Tuesday.",
        )

        review_item = ReviewItem(
            component_id=decision.id,
            status="approved",
            severity="low",
            kind="fact_update",
            title="Launch decision approved",
            summary="Operator approved the launch timing.",
            confidence=0.9,
        )
        db_session.add(review_item)
        await db_session.flush()
        db_session.add(
            ReviewDecision(
                review_item_id=review_item.id,
                previous_status="needs_review",
                new_status="approved",
                actor_type="operator",
                note="Approved for release comms.",
                created_at=now - timedelta(minutes=20),
            )
        )
        db_session.add(
            SyncJob(
                connector_id=connector.id,
                job_type="sync",
                status=SyncJobStatus.FAILED,
                error_type="RateLimitError",
                error_message="Retry later",
                completed_at=now - timedelta(minutes=10),
            )
        )
        await db_session.commit()

        response = await client.get(
            "/api/timeline",
            params={"workspace_id": str(workspace.id), "limit": 20},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total_events"] == 5
        assert len(body["items"]) == 5
        assert body["has_more"] is False
        assert body["next_cursor"] is None
        assert all(item["event_id"] for item in body["items"])
        assert [item["event_type"] for item in body["items"]] == [
            "connector_failure",
            "review_transition",
            "source_ingest",
            "source_ingest",
            "decision_change",
        ]
        assert body["items"][0]["summary"] == "Retry later"
        assert body["items"][4]["source_label"] == "timeline"
        assert body["items"][0]["payload"]["error_type"] == "RateLimitError"
        assert body["items"][1]["payload"]["new_status"] == "approved"
        assert body["items"][2]["payload"]["external_id"] == "slack:timeline"
        assert body["items"][4]["payload"]["is_current"] is True

    async def test_timeline_enriches_zoom_ingests_with_meeting_outcomes_and_action_owners(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(
            db_session,
            workspace,
            connector_type=ConnectorType.ZOOM,
        )
        await _seed_source_document(
            db_session,
            connector,
            external_id="zoom:555:transcript-file-1",
            content=(
                "Founder: meeting outcome: launch pricing page on April 15.\n"
                "Alice: action item: prepare demo environment.\n"
                "Bob: todo: draft launch email.\n"
            ),
            metadata={
                "meeting_id": 555,
                "meeting_uuid": "meeting-555",
                "meeting_topic": "Weekly Product Review",
                "participants": ["Founder", "Alice", "Bob"],
                "recording_date": "2026-04-01",
                "source_type": "zoom_transcript",
            },
        )
        await db_session.commit()

        response = await client.get(
            "/api/timeline",
            params={"workspace_id": str(workspace.id), "limit": 10},
        )

        assert response.status_code == 200
        body = response.json()
        ingest = next(item for item in body["items"] if item["event_type"] == "source_ingest")
        assert ingest["event_id"].startswith("source_ingest:")
        assert ingest["payload"]["workflow_key"] == "zoom:555"
        assert ingest["payload"]["meeting_topic"] == "Weekly Product Review"
        assert ingest["payload"]["meeting_outcome_summary"] == "launch pricing page on April 15"
        assert ingest["payload"]["action_owners"] == ["Alice", "Bob"]
        assert ingest["payload"]["action_items"] == [
            {"owner": "Alice", "action": "prepare demo environment"},
            {"owner": "Bob", "action": "draft launch email"},
        ]

    async def test_timeline_enriches_github_ingests_with_review_linkage(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(
            db_session,
            workspace,
            connector_type=ConnectorType.GITHUB,
        )
        await _seed_source_document(
            db_session,
            connector,
            external_id="github:acme/context-engine:pull_review_comment:8001",
            content="Decision: ship after merge.\nRationale: closes issue #31 after commit abc1234.",
            metadata={
                "repo_full_name": "acme/context-engine",
                "title": "Review Comment on Pull Request #77: Add eval CLI",
                "item_type": "pull_request_review_comment",
                "parent_item_type": "pull_request",
                "parent_number": 77,
                "parent_title": "Add eval CLI",
                "parent_external_id": "github:acme/context-engine:pull_request:77",
                "pull_request_references": ["acme/context-engine#13"],
                "issue_references": ["acme/context-engine#31"],
                "commit_references": ["abc1234", "deadbeef1"],
                "commit_id": "deadbeef1",
                "original_commit_id": "cafebabe2",
                "path": "app/evals/runner.py",
                "line": 236,
                "side": "RIGHT",
                "source_type": "github_pull_request_review_comment",
            },
        )
        await db_session.commit()

        response = await client.get(
            "/api/timeline",
            params={"workspace_id": str(workspace.id), "limit": 10},
        )

        assert response.status_code == 200
        body = response.json()
        ingest = next(item for item in body["items"] if item["event_type"] == "source_ingest")
        assert ingest["payload"]["workflow_key"] == "github:acme/context-engine:pull_request:77"
        assert ingest["payload"]["repo_full_name"] == "acme/context-engine"
        assert ingest["payload"]["item_type"] == "pull_request_review_comment"
        assert ingest["payload"]["parent_number"] == 77
        assert ingest["payload"]["pull_request_references"] == ["acme/context-engine#13"]
        assert ingest["payload"]["issue_references"] == ["acme/context-engine#31"]
        assert ingest["payload"]["commit_references"] == ["abc1234", "deadbeef1"]
        assert ingest["payload"]["commit_id"] == "deadbeef1"
        assert ingest["payload"]["path"] == "app/evals/runner.py"
        assert ingest["payload"]["line"] == 236
        assert ingest["payload"]["side"] == "RIGHT"

    async def test_timeline_supports_cursor_pagination(
        self, client, workspace, db_session
    ):
        now = datetime.now(timezone.utc)
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace, name="Timeline Pagination")

        documents = []
        for offset in range(4):
            documents.append(
                await _seed_source_document(
                    db_session,
                    connector,
                    external_id=f"slack:timeline:{offset}",
                    content=f"decision: timeline entry {offset}",
                    metadata={"channel_name": f"timeline-{offset}"},
                    ingested_at=now - timedelta(minutes=offset),
                )
            )

        component = Component(
            model_id=model.id,
            name="Decision in #timeline-pagination",
            value="Keep paginating timeline.",
            confidence=0.9,
            authority_weight=0.8,
            valid_from=now - timedelta(hours=1),
            last_verified_at=now,
        )
        db_session.add(component)
        await db_session.flush()
        await _link_component_source(
            db_session,
            component,
            documents[-1],
            extracted_value="Keep paginating timeline.",
        )
        await db_session.commit()

        first = await client.get(
            "/api/timeline",
            params={"workspace_id": str(workspace.id), "limit": 2},
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["has_more"] is True
        assert len(first_body["items"]) == 2
        assert first_body["next_cursor"] is not None

        second = await client.get(
            "/api/timeline",
            params={
                "workspace_id": str(workspace.id),
                "limit": 2,
                "cursor": first_body["next_cursor"],
            },
        )
        assert second.status_code == 200
        second_body = second.json()
        assert len(second_body["items"]) >= 1
        first_event_ids = {item["event_id"] for item in first_body["items"]}
        second_event_ids = {item["event_id"] for item in second_body["items"]}
        assert first_event_ids.isdisjoint(second_event_ids)


class TestLaunchGuardApi:
    async def test_launch_guard_flags_supported_stale_and_contradicted_claims(
        self, client, workspace, db_session
    ):
        connector = await _seed_connector(db_session, workspace)
        model = await _seed_model(db_session, workspace, name="GTM")

        current_pricing_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="notion:pricing-current",
            content="decision: enterprise price is $600/seat",
            metadata={"page_title": "Pricing"},
        )
        historical_pricing_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:pricing-old",
            content="decision: enterprise price is $450/seat",
            metadata={"channel_name": "pricing"},
        )
        auth_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="slack:auth",
            content="decision: auth provider is Auth0",
            metadata={"channel_name": "auth"},
        )
        launch_doc = await _seed_source_document(
            db_session,
            connector,
            external_id="zoom:launch",
            content="decision: launch timing is next Tuesday",
            metadata={"meeting_topic": "Weekly Product Review"},
        )

        current_pricing = Component(
            model_id=model.id,
            name="Decision in Pricing",
            value="Enterprise price is $600/seat.",
            confidence=0.95,
            authority_weight=0.95,
            valid_from=datetime.now(timezone.utc) - timedelta(days=2),
            last_verified_at=datetime.now(timezone.utc),
        )
        old_pricing = Component(
            model_id=model.id,
            name="Decision in Pricing",
            value="Enterprise price is $450/seat.",
            confidence=0.72,
            authority_weight=0.75,
            valid_from=datetime.now(timezone.utc) - timedelta(days=10),
            valid_to=datetime.now(timezone.utc) - timedelta(days=2),
            last_verified_at=datetime.now(timezone.utc) - timedelta(days=2),
            is_stale=True,
        )
        auth = Component(
            model_id=model.id,
            name="Auth Provider Decision",
            value="Auth0 selected.",
            confidence=0.91,
            authority_weight=0.90,
            valid_from=datetime.now(timezone.utc) - timedelta(days=1),
            last_verified_at=datetime.now(timezone.utc),
        )
        launch = Component(
            model_id=model.id,
            name="Decision in Weekly Product Review",
            value="Launch timing is next Tuesday.",
            confidence=0.89,
            authority_weight=0.90,
            valid_from=datetime.now(timezone.utc) - timedelta(hours=6),
            last_verified_at=datetime.now(timezone.utc),
        )
        db_session.add_all([current_pricing, old_pricing, auth, launch])
        await db_session.flush()
        old_pricing.superseded_by_id = current_pricing.id
        await db_session.flush()

        await _link_component_source(
            db_session,
            current_pricing,
            current_pricing_doc,
            extracted_value="Enterprise price is $600/seat.",
        )
        await _link_component_source(
            db_session,
            old_pricing,
            historical_pricing_doc,
            extracted_value="Enterprise price is $450/seat.",
        )
        await _link_component_source(db_session, auth, auth_doc, extracted_value="Auth0 selected.")
        await _link_component_source(
            db_session,
            launch,
            launch_doc,
            extracted_value="Launch timing is next Tuesday.",
        )
        await db_session.commit()

        response = await client.post(
            "/api/launch-guard/check",
            json={
                "workspace_id": str(workspace.id),
                "draft": (
                    "Enterprise price is $450/seat.\n"
                    "Auth provider is Okta.\n"
                    "Launch timing is next Tuesday."
                ),
            },
        )

        assert response.status_code == 200
        body = response.json()
        by_claim = {item["claim"]: item for item in body["claims"]}
        assert by_claim["Enterprise price is $450/seat."]["status"] == "stale"
        assert by_claim["Auth provider is Okta."]["status"] == "contradicted"
        assert by_claim["Launch timing is next Tuesday."]["status"] == "supported"
        assert body["stale_count"] == 1
        assert body["contradicted_count"] == 1
        assert body["supported_count"] == 1
