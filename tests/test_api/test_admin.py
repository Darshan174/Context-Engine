"""Tests for workspace bootstrap and health endpoints."""

from __future__ import annotations

from uuid import uuid4

import app.main as main_module


class TestWorkspaceEndpoints:
    async def test_create_workspace(self, client):
        resp = await client.post(
            "/api/workspaces",
            json={
                "name": "Acme Demo",
                "description": "Local workspace bootstrap test",
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Acme Demo"
        assert body["description"] == "Local workspace bootstrap test"
        assert "id" in body

    async def test_list_workspaces(self, client):
        created = await client.post(
            "/api/workspaces",
            json={"name": "Listed Workspace"},
        )
        assert created.status_code == 201

        resp = await client.get("/api/workspaces")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert any(item["name"] == "Listed Workspace" for item in body)

    async def test_get_workspace(self, client):
        created = await client.post(
            "/api/workspaces",
            json={"name": "Fetchable Workspace"},
        )
        workspace_id = created.json()["id"]

        resp = await client.get(f"/api/workspaces/{workspace_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == workspace_id
        assert body["name"] == "Fetchable Workspace"

    async def test_get_missing_workspace_returns_404(self, client):
        resp = await client.get(f"/api/workspaces/{uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Workspace not found"


class DummyConnection:
    async def execute(self, _statement):
        return 1


class DummyConnectContext:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail

    async def __aenter__(self):
        if self.should_fail:
            raise RuntimeError("database unavailable")
        return DummyConnection()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyEngine:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail

    def connect(self):
        return DummyConnectContext(should_fail=self.should_fail)


class DummyRedisClient:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.closed = False

    async def ping(self):
        if self.should_fail:
            raise RuntimeError("redis unavailable")
        return True

    async def aclose(self):
        self.closed = True


class TestHealthEndpoints:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readiness_returns_ready_when_dependencies_are_healthy(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "engine", DummyEngine())
        monkeypatch.setattr(
            main_module.redis,
            "from_url",
            lambda *_args, **_kwargs: DummyRedisClient(),
        )

        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json() == {
            "status": "ready",
            "checks": {"database": "ok", "redis": "ok"},
        }

    async def test_readiness_returns_503_when_database_check_fails(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "engine", DummyEngine(should_fail=True))
        monkeypatch.setattr(
            main_module.redis,
            "from_url",
            lambda *_args, **_kwargs: DummyRedisClient(),
        )

        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["status"] == "degraded"
        assert detail["checks"] == {"database": "error", "redis": "ok"}
        assert "database" in detail["errors"]

    async def test_readiness_returns_503_when_redis_check_fails(self, client, monkeypatch):
        monkeypatch.setattr(main_module, "engine", DummyEngine())
        monkeypatch.setattr(
            main_module.redis,
            "from_url",
            lambda *_args, **_kwargs: DummyRedisClient(should_fail=True),
        )

        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["status"] == "degraded"
        assert detail["checks"] == {"database": "ok", "redis": "error"}
        assert "redis" in detail["errors"]
