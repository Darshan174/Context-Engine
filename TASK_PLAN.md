# Task Plan

## Current Feature

Build the connectors and knowledge graph foundation for OSS use.

Current implemented direction:

- Connector backend exists for catalog/status/sync contracts.
- AI context import is the first real connector-like ingestion path.
- Slack, Discord, and Gmail are not real provider integrations yet and must not be represented as working.
- Graph responses include source provenance and `proposed` future components.
- SQLite startup migrations cover new relationship fields.

## Branches

- `agent/kimi-connectors-graph-plan`
- `agent/glm-connector-ai-context-implementation`
- `agent/qwen-graph-reasoning-validation`
- `agent/xiaomi-repo-review-docs`

## Agent Assignments

### Kimi K2.6

Task file: `.agent-runs/kimi-task.md`

Owns the connector/graph contract. Keep it current with implemented behavior, especially connector response shape, AI-context source types, migration behavior, and unsupported provider states.

### GLM 5.1

Task file: `.agent-runs/glm-task.md`

Owns implementation of connector backend/UI contract fixes and AI-context ingestion. Do not implement fake external provider support.

### Qwen

Task file: `.agent-runs/qwen-task.md`

Owns graph reasoning, schema compatibility, relationship correctness, and tests that prevent hallucinated graph edges or hidden future context.

### Xiaomi MiMo V2.5 Pro

Task file: `.agent-runs/xiaomi-task.md`

Owns long-context review, docs, UX consistency, and OSS readiness. Docs must reflect the current implementation, not stale findings.

## Acceptance Criteria

- `pytest -q` passes.
- Frontend build passes when frontend files change.
- AI Context appears in connector UI data and backend summaries.
- Unsupported connectors cannot be shown as working integrations.
- README/project docs mention six current tables.
- `docs/connectors-graph-contract.md` and `docs/oss-readiness.md` match current code and test results.

