#!/usr/bin/env python3
"""Run startup-question eval regressions against a workspace."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from app.database import AsyncSessionLocal
from app.evals.gold_set import load_default_cases
from app.evals.harness import StartupEvalHarness
from app.evals.runner import format_report, summary_to_json
from app.schemas.query import QueryFilters
from app.services.query_service import QueryService


async def _run(args) -> int:
    cases = load_default_cases(
        domains=args.domains,
        ids=args.case_ids,
    )
    if not cases:
        print("Eval regression failed: no eval cases matched the requested filters.", file=sys.stderr)
        return 2

    async with AsyncSessionLocal() as session:
        summary = await StartupEvalHarness(
            QueryService(session),
            pass_threshold=args.pass_threshold,
        ).run(
            workspace_id=UUID(args.workspace_id),
            cases=cases,
            filters=QueryFilters(),
        )

    thresholds = {
        "retrieval": args.min_retrieval,
        "facts": args.min_fact_correctness,
        "answer": args.min_answer_correctness,
    }
    failures: list[str] = []
    if summary.average_retrieval_hit_quality < thresholds["retrieval"]:
        failures.append(
            f"retrieval {summary.average_retrieval_hit_quality:.2f} < {thresholds['retrieval']:.2f}"
        )
    if summary.average_extracted_fact_correctness < thresholds["facts"]:
        failures.append(
            f"facts {summary.average_extracted_fact_correctness:.2f} < {thresholds['facts']:.2f}"
        )
    if summary.average_final_answer_correctness < thresholds["answer"]:
        failures.append(
            f"answers {summary.average_final_answer_correctness:.2f} < {thresholds['answer']:.2f}"
        )

    payload = summary_to_json(summary)
    payload["thresholds"] = thresholds
    payload["status"] = "passed" if not failures else "failed"
    payload["failures"] = failures

    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_report(summary))
        if failures:
            print("Threshold failures: " + "; ".join(failures), file=sys.stderr)

    if failures:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run startup-question eval regressions.")
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--domains", nargs="+", default=None)
    parser.add_argument("--case-ids", nargs="+", default=None)
    parser.add_argument("--pass-threshold", type=float, default=0.5)
    parser.add_argument("--min-retrieval", type=float, default=0.8)
    parser.add_argument("--min-fact-correctness", type=float, default=0.8)
    parser.add_argument("--min-answer-correctness", type=float, default=0.8)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
