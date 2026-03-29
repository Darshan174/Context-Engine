"""Tests for the Phase 1 knowledge CRUD endpoints (app.api.knowledge)."""

from __future__ import annotations

from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# POST /api/models
# ---------------------------------------------------------------------------


class TestCreateModel:
    async def test_create_model(self, client, model_payload):
        resp = await client.post("/api/models", json=model_payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Pricing"
        assert body["workspace_id"] == model_payload["workspace_id"]
        assert body["description"] == "All pricing info"
        assert body["status"] == "active"
        assert body["auto_generated"] is False
        assert "id" in body

    async def test_create_model_missing_workspace_returns_404(self, client):
        resp = await client.post(
            "/api/models",
            json={
                "workspace_id": str(uuid4()),
                "name": "Orphan",
            },
        )
        assert resp.status_code == 404

    async def test_duplicate_model_name_returns_409(self, client, created_model, model_payload):
        resp = await client.post("/api/models", json=model_payload)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/models?workspace_id=...
# ---------------------------------------------------------------------------


class TestListModels:
    async def test_list_models(self, client, created_model, model_payload):
        ws_id = model_payload["workspace_id"]
        resp = await client.get("/api/models", params={"workspace_id": ws_id})
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert any(m["id"] == created_model["id"] for m in body)

    async def test_list_models_unknown_workspace_returns_404(self, client):
        resp = await client.get(
            "/api/models",
            params={"workspace_id": str(uuid4())},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/models/{model_id}
# ---------------------------------------------------------------------------


class TestGetModel:
    async def test_get_model_with_components(self, client, created_model):
        resp = await client.get(f"/api/models/{created_model['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created_model["id"]
        assert "components" in body

    async def test_get_missing_model_returns_404(self, client, workspace):
        resp = await client.get(f"/api/models/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/components/{component_id}
# ---------------------------------------------------------------------------


class TestGetComponent:
    async def test_get_component(self, client, created_component):
        resp = await client.get(f"/api/components/{created_component['id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == created_component["id"]
        assert body["name"] == created_component["name"]
        assert body["value"] == created_component["value"]

    async def test_get_missing_component_returns_404(self, client, workspace):
        resp = await client.get(f"/api/components/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/models/{model_id}/components
# ---------------------------------------------------------------------------


class TestAddComponent:
    async def test_add_component(self, client, created_model, component_payload):
        resp = await client.post(
            f"/api/models/{created_model['id']}/components",
            json=component_payload,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Enterprise Price"
        assert body["value"] == "$600/seat"
        assert body["confidence"] == pytest.approx(0.92)
        assert body["model_id"] == created_model["id"]
        assert body["is_stale"] is False

    async def test_add_component_to_missing_model_returns_404(self, client, workspace):
        resp = await client.post(
            f"/api/models/{uuid4()}/components",
            json={"name": "X", "value": "Y", "confidence": 0.5},
        )
        assert resp.status_code == 404

    async def test_component_appears_in_model_detail(
        self, client, created_model, created_component
    ):
        resp = await client.get(f"/api/models/{created_model['id']}")
        body = resp.json()
        ids = [c["id"] for c in body["components"]]
        assert created_component["id"] in ids


# ---------------------------------------------------------------------------
# PATCH /api/components/{component_id}
# ---------------------------------------------------------------------------


class TestUpdateComponent:
    async def test_update_value(self, client, created_component):
        resp = await client.patch(
            f"/api/components/{created_component['id']}",
            json={"value": "$700/seat"},
        )
        assert resp.status_code == 200
        assert resp.json()["value"] == "$700/seat"

    async def test_update_confidence(self, client, created_component):
        resp = await client.patch(
            f"/api/components/{created_component['id']}",
            json={"confidence": 0.99},
        )
        assert resp.status_code == 200
        assert resp.json()["confidence"] == pytest.approx(0.99)

    async def test_empty_patch_returns_400(self, client, created_component):
        resp = await client.patch(
            f"/api/components/{created_component['id']}",
            json={},
        )
        assert resp.status_code == 400

    async def test_update_missing_component_returns_404(self, client, workspace):
        resp = await client.patch(
            f"/api/components/{uuid4()}",
            json={"value": "nope"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/components/{component_id}
# ---------------------------------------------------------------------------


class TestDeleteComponent:
    async def test_delete_component(self, client, created_component, created_model):
        cid = created_component["id"]
        resp = await client.delete(f"/api/components/{cid}")
        assert resp.status_code == 204

        # Verify it's gone from the model detail
        detail = await client.get(f"/api/models/{created_model['id']}")
        assert cid not in [c["id"] for c in detail.json()["components"]]

    async def test_delete_missing_component_returns_404(self, client, workspace):
        resp = await client.delete(f"/api/components/{uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/relationships
# ---------------------------------------------------------------------------


class TestCreateRelationship:
    @pytest.fixture
    async def two_components(self, client, created_model):
        """Create two components so we can relate them."""
        r1 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "Starter Plan", "value": "$29/mo", "confidence": 0.95},
        )
        r2 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "AI Chat Widget", "value": "Shipped Q1", "confidence": 0.90},
        )
        return r1.json(), r2.json()

    async def test_create_relationship(self, client, two_components):
        c1, c2 = two_components
        resp = await client.post(
            "/api/relationships",
            json={
                "source_component_id": c1["id"],
                "target_component_id": c2["id"],
                "relationship_type": "enables",
                "sentiment": "positive",
                "confidence": 0.85,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["source_component_id"] == c1["id"]
        assert body["source_component_name"] == c1["name"]
        assert body["target_component_id"] == c2["id"]
        assert body["target_component_name"] == c2["name"]
        assert body["relationship_type"] == "enables"
        assert body["sentiment"] == "positive"

    async def test_self_relationship_returns_400(self, client, created_component):
        cid = created_component["id"]
        resp = await client.post(
            "/api/relationships",
            json={
                "source_component_id": cid,
                "target_component_id": cid,
                "relationship_type": "related_to",
                "confidence": 0.5,
            },
        )
        assert resp.status_code == 400

    async def test_relationship_with_missing_component_returns_404(self, client, created_component):
        resp = await client.post(
            "/api/relationships",
            json={
                "source_component_id": created_component["id"],
                "target_component_id": str(uuid4()),
                "relationship_type": "depends_on",
                "confidence": 0.7,
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/models/{model_id}/relationships
# ---------------------------------------------------------------------------


class TestModelRelationships:
    async def test_get_model_relationships(self, client, created_model):
        # Create two components and a relationship
        r1 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "A", "value": "a", "confidence": 0.8},
        )
        r2 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "B", "value": "b", "confidence": 0.8},
        )
        c1, c2 = r1.json(), r2.json()

        await client.post(
            "/api/relationships",
            json={
                "source_component_id": c1["id"],
                "target_component_id": c2["id"],
                "relationship_type": "depends_on",
                "confidence": 0.75,
            },
        )

        resp = await client.get(f"/api/models/{created_model['id']}/relationships")
        assert resp.status_code == 200
        rels = resp.json()
        assert len(rels) >= 1
        assert any(
            r["source_component_id"] == c1["id"]
            and r["source_component_name"] == c1["name"]
            and r["target_component_id"] == c2["id"]
            and r["target_component_name"] == c2["name"]
            for r in rels
        )

    async def test_relationships_for_missing_model_returns_404(self, client, workspace):
        resp = await client.get(f"/api/models/{uuid4()}/relationships")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/components/{component_id}/relationships
# ---------------------------------------------------------------------------


class TestComponentRelationships:
    async def test_get_component_relationships(self, client, created_model):
        r1 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "X", "value": "x", "confidence": 0.8},
        )
        r2 = await client.post(
            f"/api/models/{created_model['id']}/components",
            json={"name": "Y", "value": "y", "confidence": 0.8},
        )
        c1, c2 = r1.json(), r2.json()

        await client.post(
            "/api/relationships",
            json={
                "source_component_id": c1["id"],
                "target_component_id": c2["id"],
                "relationship_type": "blocked_by",
                "sentiment": "negative",
                "confidence": 0.6,
            },
        )

        # Query from source side
        resp = await client.get(f"/api/components/{c1['id']}/relationships")
        assert resp.status_code == 200
        assert any(
            rel["source_component_name"] == c1["name"]
            and rel["target_component_name"] == c2["name"]
            for rel in resp.json()
        )

        # Query from target side
        resp = await client.get(f"/api/components/{c2['id']}/relationships")
        assert resp.status_code == 200
        assert any(
            rel["source_component_name"] == c1["name"]
            and rel["target_component_name"] == c2["name"]
            for rel in resp.json()
        )

    async def test_relationships_for_missing_component_returns_404(self, client, workspace):
        resp = await client.get(f"/api/components/{uuid4()}/relationships")
        assert resp.status_code == 404
