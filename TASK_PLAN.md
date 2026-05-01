# Task Plan

## Current Feature

Harden the connectors and knowledge graph foundation for an OSS-ready release.

This round has two goals:

1. Resolve the latest Codex review findings.
2. Expand the implementation/docs/test workload so the repo is harder for agents and contributors to misunderstand.

Current implemented direction:

- Connector backend exists for catalog/status/sync contracts.
- AI Context and local import are the first real ingestion paths.
- External providers must be honest: catalogued provider stubs are allowed, fake working integrations are not.
- Graph responses include source provenance, relationship evidence, relationship confidence, and `proposed` future components.
- SQLite startup migrations cover new relationship fields.
- Docs must describe the current code, not previous review findings.

## Current Review Findings To Fix

- Slack is catalogued as available while unsupported, and the UI can reach setup paths that call missing backend endpoints.
- `docs/oss-readiness.md` still reports old backend/frontend catalog drift after the backend added coming-soon catalog stubs.
- `docs/connectors-graph-contract.md` still says Zoom/GDrive/Wispr are absent from the backend catalog and that `/connectors/zoom/connect` does not exist.
- `docs/connectors-graph-contract.md` has a stale test count; latest known result is `pytest -q` -> 107 passed.

## Branches

- `agent/kimi-connectors-graph-plan`
- `agent/glm-connector-ai-context-implementation`
- `agent/qwen-graph-reasoning-validation`
- `agent/xiaomi-repo-review-docs`

## Agent Assignments

### Kimi K2.6

Task file: `.agent-runs/kimi-task.md`

Owns the connector/graph contract and task sequencing. Update the contract to distinguish real ingestion, catalogued stubs, unsupported states, and proposed provider integrations. Produce a short merge order for the other agents.

### GLM 5.1

Task file: `.agent-runs/glm-task.md`

Owns implementation of connector honesty and AI-context/local connector behavior. Fix Slack availability/setup behavior without implementing fake Slack support. Add or update focused tests.

### Qwen

Task file: `.agent-runs/qwen-task.md`

Owns graph reasoning, schema compatibility, migration safety, and tests that prevent hallucinated graph edges or hidden future context. Add adversarial cases for relationship creation and temporal status.

### Xiaomi MiMo V2.5 Pro

Task file: `.agent-runs/xiaomi-task.md`

Owns long-context review, docs, UX consistency, and OSS readiness. Refresh docs after implementation and verify contributor-facing claims against code/tests.

## Acceptance Criteria

- `pytest -q` passes.
- Frontend build passes when frontend files change.
- AI Context appears in connector UI data and backend summaries.
- Unsupported connectors cannot be shown as working integrations.
- Slack cannot enter a connected/setup-complete state unless a tested Slack backend setup and sync path exists.
- Provider stubs such as Zoom/GDrive/Wispr/Gmail are clearly represented as `coming_soon` or otherwise disabled until implemented.
- README/project docs mention six current tables and connector storage accurately.
- `docs/connectors-graph-contract.md` and `docs/oss-readiness.md` match current code and test results.
- Graph API keeps current, review-needed, and proposed future context visible.
- Relationships remain optional, source-backed, and conservative.
- Final agent reports include changed files, tests run, evidence, risks, and remaining gaps.

## Suggested Integration Order

1. Kimi updates the contract and confirms the expected connector state matrix.
2. GLM fixes connector honesty and tests.
3. Qwen validates graph/migration behavior and adds adversarial graph tests.
4. Xiaomi refreshes docs and performs OSS readiness review.
5. Codex reviews all diffs, runs verification, and merges the best changes.
