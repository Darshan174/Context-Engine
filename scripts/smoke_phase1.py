from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any
from urllib import error, parse, request


def api_request(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    data = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except error.HTTPError as exc:  # pragma: no cover - CLI script
        body = exc.read().decode("utf-8")
        detail = body or exc.reason
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {detail}") from exc
    except error.URLError as exc:  # pragma: no cover - CLI script
        raise RuntimeError(f"Unable to reach {url}: {exc.reason}") from exc


def create_workspace(base_url: str) -> dict[str, Any]:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return api_request(
        base_url,
        "POST",
        "/api/workspaces",
        {
            "name": f"Smoke Test Workspace {timestamp}",
            "description": "Workspace created by scripts/smoke_phase1.py",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Phase 1 API smoke test.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the FastAPI app (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

    try:
        health = api_request(base_url, "GET", "/health")
        ready = api_request(base_url, "GET", "/health/ready")
        workspace = create_workspace(base_url)

        model = api_request(
            base_url,
            "POST",
            "/api/models",
            {
                "workspace_id": workspace["id"],
                "name": f"Smoke Pricing {timestamp}",
                "description": "Model created by Phase 1 smoke test",
            },
        )

        component_a = api_request(
            base_url,
            "POST",
            f"/api/models/{model['id']}/components",
            {
                "name": "Starter Plan",
                "value": "$29/mo",
                "confidence": 0.95,
                "authority_source": "smoke-test",
            },
        )
        component_b = api_request(
            base_url,
            "POST",
            f"/api/models/{model['id']}/components",
            {
                "name": "Pro Plan",
                "value": "$99/mo",
                "confidence": 0.95,
                "authority_source": "smoke-test",
            },
        )

        relationship = api_request(
            base_url,
            "POST",
            "/api/relationships",
            {
                "source_component_id": component_b["id"],
                "target_component_id": component_a["id"],
                "relationship_type": "supersedes",
                "sentiment": "neutral",
                "confidence": 0.8,
                "description": "Pro supersedes starter for the smoke test",
            },
        )

        models = api_request(
            base_url,
            "GET",
            f"/api/models?{parse.urlencode({'workspace_id': workspace['id']})}",
        )
        model_detail = api_request(base_url, "GET", f"/api/models/{model['id']}")
        relationships = api_request(base_url, "GET", f"/api/models/{model['id']}/relationships")
        query_result = api_request(
            base_url,
            "POST",
            "/api/query",
            {
                "question": "What is the Pro Plan?",
                "workspace_id": workspace["id"],
            },
        )

        component_names = {item["name"] for item in model_detail["components"]}
        relationship_names = {
            relationship.get("source_component_name"),
            relationship.get("target_component_name"),
        }
        queried_component_names = {item["name"] for item in query_result["components"]}

        assert health["status"] == "ok"
        assert ready["status"] == "ready"
        assert any(item["id"] == model["id"] for item in models)
        assert {"Starter Plan", "Pro Plan"}.issubset(component_names)
        assert {"Starter Plan", "Pro Plan"}.issubset(relationship_names)
        assert any(item["id"] == relationship["id"] for item in relationships)
        assert "Pro Plan" in queried_component_names
        assert "$99/mo" in query_result["answer"]
        assert query_result["freshness"] == "current"

        print("Phase 1 smoke test passed.")
        print(f"Workspace: {workspace['id']}")
        print(f"Model: {model['id']}")
        print(f"Components: {component_a['id']}, {component_b['id']}")
        print(f"Relationship: {relationship['id']}")
        print(f"Query answer: {query_result['answer']}")
        return 0
    except Exception as exc:  # pragma: no cover - CLI script
        print(f"Phase 1 smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
