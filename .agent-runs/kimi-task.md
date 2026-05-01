# Kimi K2.6 Task

## Role

You are the task planner and connector/graph contract writer.

Work in this repo:

```text
/Users/darshann/Desktop/context-engine
```

Preferred branch:

```bash
agent/kimi-connectors-graph-plan
```

## Focus

Update the connector/graph contract for the next OSS-hardening round.

The contract must distinguish:

- `Observed`: verified current behavior with file evidence.
- `Implemented`: tested behavior already in the repo.
- `Proposed`: next work.
- `Not implemented yet`: provider or graph claims that must not be advertised as working.

## Required Workload

1. Fix stale contract claims from the latest Codex review:
   - Zoom/GDrive/Wispr are now backend catalog stubs, not absent backend entries.
   - `/connectors/zoom/connect` is handled by the generic connect endpoint and should fail honestly as coming soon, not 404.
   - Latest known backend verification is `pytest -q` -> 107 passed.
2. Define a connector state matrix for every catalogued type:
   - `ai_context`
   - `local`
   - `discord`
   - `slack`
   - `zoom`
   - `gdrive`
   - `gmail`
   - `wispr_flow`
3. For each connector, state:
   - catalog availability;
   - whether real sync is implemented;
   - supported connect modes;
   - whether UI should show connect/setup controls;
   - expected backend response for unsupported connect/sync attempts;
   - tests that should prove the claim.
4. Add a short merge order for GLM, Qwen, Xiaomi, and Codex.
5. Add a contributor note explaining that catalog presence does not equal real provider support.

## Current Contract Areas

- connector catalog and frontend/backend response shape;
- AI context import source types and metadata;
- connector processing summary counts;
- unsupported Slack/Discord/Gmail/Zoom/GDrive/Wispr states;
- graph `proposed` component visibility;
- SQLite migration/backfill behavior.
- relationship evidence and confidence rules.

## Boundaries

- Do not edit source code for this task unless the docs cannot be made correct without a tiny reference update.
- Do not claim provider OAuth exists unless there is a tested endpoint and ingestion path.
- Do not remove known risks; rewrite them as current, precise risks.

## Final Report

Include files changed, contract decisions, evidence files, the connector state matrix, risks, and recommended next implementation order.
