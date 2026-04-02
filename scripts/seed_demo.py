#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json

from app.database import AsyncSessionLocal
from app.evals.demo_seed import DEFAULT_WORKSPACE_NAME, seed_demo_workspace


async def _run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as session:
        result = await seed_demo_workspace(
            session,
            workspace_name=args.workspace_name,
            replace_existing=args.replace_existing,
        )

    payload = {
        "workspace_id": str(result.workspace_id),
        "workspace_name": result.workspace_name,
        "status": result.status,
        "seeded_case_count": result.seeded_case_count,
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"{result.status}: {result.workspace_name} "
            f"({result.workspace_id}) with {result.seeded_case_count} eval cases"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a deterministic demo workspace.")
    parser.add_argument(
        "--workspace-name",
        default=DEFAULT_WORKSPACE_NAME,
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete and recreate an existing workspace with the same name.",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
