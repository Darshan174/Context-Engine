# Task Plan

## Intended Outcome

Build `context-engine` into an OSS-grade developer context system.

It should ingest project knowledge from local files, AI-agent sessions, and future provider connectors, then produce a precise knowledge graph of:

- models: first-class concepts such as Pricing, Roadmap, Security, Customer Segment, Integration, Feature, Constraint;
- components: facts inside models, such as `$20 plan`, `Slack connector`, `SOC2 requirement`, `Q3 launch`;
- relationships: optional, evidence-backed links within or across models;
- temporal state: past decisions, current truth, proposed/future work;
- provenance: every fact and relationship should point back to source evidence.

## Realistic Timeline

- OSS alpha: 2-3 focused weeks with the four-agent workflow.
- Strong beta: 6-8 weeks.
- Polished ecosystem-ready release: 3+ months.

## Current State

- Backend has connector catalog/status/sync contracts.
- AI Context and local import are the first real ingestion paths.
- External providers are stubs unless tested.
- Graph includes provenance, relationship evidence/confidence, and proposed context.
- Docs were updated to distinguish unknown connectors, coming-soon stubs, and missing setup routes.

## 5x Workload

### Phase 1: Contract and Product Shape

- Define the connector state machine: `available`, `coming_soon`, `unsupported`, `configured`, `connected`, `syncing`, `failed`.
- Define the graph ontology: model types, component fact types, relationship types, temporal statuses, confidence rules.
- Define AI Context import schema for Codex, Claude Code, OpenCode, Cursor, generic agent logs, diffs, plans, reviews, and terminal output.
- Define provider roadmap contracts for Slack, Discord, Gmail, Google Drive, Zoom, GitHub, Notion, Wispr Flow.
- Add explicit non-goals: no fake OAuth, no provider marked working without tested sync, no hallucinated graph edges.

### Phase 2: Connector Honesty and UX

- Fix Slack so unsupported setup cannot look available.
- Hide or disable frontend actions that call missing or unavailable provider setup paths.
- Ensure catalogued coming-soon connectors return honest API errors.
- Add tests for connect/sync behavior across all connector states.
- Add UI copy that tells contributors what is missing without promising working integrations.

### Phase 3: AI Context Ingestion

- Add robust import validation, dedupe rules, metadata preservation, and source typing.
- Support session-level metadata: tool, branch, commit, agent, task, started/ended timestamps.
- Extract task plans, decisions, diffs, review findings, blockers, and unresolved questions.
- Preserve raw source content and parsed structured fields.
- Add fixtures for Codex, Claude Code, OpenCode, Cursor, and generic logs.

### Phase 4: Knowledge Graph Core

- Harden model/component extraction with conservative rules.
- Add relationship taxonomy: `depends_on`, `conflicts_with`, `implements`, `replaces`, `blocks`, `supports`, `mentions`, `priced_as`, `owned_by`.
- Ensure relationship creation requires explicit evidence or high-confidence structured extraction.
- Add temporal handling for past/current/future/proposed/deprecated facts.
- Add graph stats, filters, and source-backed drilldowns.

### Phase 5: Storage, Migrations, and Scale

- Add migration coverage for connector and graph schema changes.
- Ensure existing SQLite installs upgrade safely.
- Add indexes for graph queries and connector status queries.
- Define a future Postgres path without breaking SQLite default.
- Add import idempotency tests.

### Phase 6: API and MCP Surface

- Add stable API contracts for graph reads, connector status, processing summary, AI context import, and provenance lookup.
- Ensure MCP/query responses preserve evidence and source IDs.
- Add error contracts for unsupported connectors and malformed imports.
- Add examples for consumers and AI agents.

### Phase 7: Frontend Experience

- Make Connectors page state-driven from backend truth.
- Add AI Context import UI or a clear path through Sources.
- Improve GraphView filters for model, status, source type, confidence, and time.
- Add empty/error/loading states for connector and graph workflows.
- Prevent UI actions that cannot succeed.

### Phase 8: Tests and Quality Gates

- Backend tests for connectors, ingestion, graph extraction, migrations, API contracts.
- Frontend build plus targeted component tests where patterns exist.
- Fixtures for realistic startup/product context.
- Adversarial tests against hallucinated relationships.
- CI should run backend tests and frontend build.

### Phase 9: OSS Readiness

- Add LICENSE.
- Add CONTRIBUTING, architecture overview, connector guide, AI Context guide, graph contract docs.
- Add setup/run/test commands that work from a clean checkout.
- Document unsupported provider status honestly.
- Keep readiness score tied to verified commands.

## Agent Order

1. Kimi K2.6: write contracts, matrix, merge order, and acceptance criteria.
2. GLM 5.1: implement connector honesty, AI-context hardening, tests, and UI guards.
3. DeepSeek V4 Pro: stress-test graph reasoning, migrations, edge cases, and API contracts.
4. Xiaomi MiMo V2.5 Pro: long-context review, docs, OSS readiness, stale-claim cleanup.
5. Codex: final review, integrate best diffs, run verification, decide what merges.

## Paste Prompts

### 1. Kimi K2.6

```text
You are Kimi K2.6 working in /Users/darshann/Desktop/context-engine on branch agent/kimi-connectors-graph-plan.

Read AGENTS.md, TASK_PLAN.md, app/api/connectors.py, app/models.py, app/services/ingest.py, app/api/graph.py, frontend/src/api/hooks.js, docs/connectors-graph-contract.md, and docs/oss-readiness.md.

Do not edit source code unless absolutely necessary. Your job is to expand the connector/knowledge-graph contract for the 5x workload. Update docs and .agent-runs/kimi-task.md with:
- connector state machine and matrix for slack, discord, gmail, ai_context, local, zoom, gdrive, wispr_flow, github, notion, wispr;
- AI Context import contract for Codex, Claude Code, OpenCode, Cursor, generic logs, plans, diffs, reviews, terminal output;
- graph ontology: model types, component fact types, relationship types, temporal statuses, confidence/evidence rules;
- exact acceptance criteria and merge order for GLM, DeepSeek, Xiaomi, Codex;
- risks and non-goals: no fake OAuth, no unsupported connector marked working, no hallucinated edges.

Run markdown/staleness searches. Final report: files changed, contract decisions, risks, recommended next order.
```

### 2. GLM 5.1

```text
You are GLM 5.1 working in /Users/darshann/Desktop/context-engine on branch agent/glm-connector-ai-context-implementation.

Read AGENTS.md, TASK_PLAN.md, .agent-runs/glm-task.md, app/api/connectors.py, tests/test_connectors.py, frontend/src/api/hooks.js, frontend/src/pages/Connectors.jsx, app/services/ingest.py, app/processing/extractor.py.

Implement connector honesty and AI-context hardening. Scope:
- Slack must not appear available/setup-complete while unsupported.
- Coming-soon providers must not connect or sync as working integrations.
- Frontend must hide/disable actions that call missing or unavailable setup paths.
- AI Context import must preserve metadata, source type, session fields, and processing summary counts.
- Add focused backend/frontend tests where patterns exist.

Do not implement real Slack/Discord/Gmail/Zoom/GDrive OAuth. Do not fake provider sync.

Run pytest -q and npm run build if frontend changes. Final report: files changed, behavior changed, tests run, remaining gaps.
```

### 3. DeepSeek V4 Pro

```text
You are DeepSeek V4 Pro working in /Users/darshann/Desktop/context-engine on branch agent/deepseek-graph-reasoning-validation.

Read AGENTS.md, TASK_PLAN.md, .agent-runs/deepseek-task.md, app/models.py, app/migrations.py, app/processing/extractor.py, app/services/ingest.py, app/api/graph.py, app/mcp/server.py, tests/test_ingestion.py, tests/test_graph_api.py, tests/test_migrations.py.

Your job is hard bug solving and reasoning validation for the knowledge graph:
- add adversarial tests so unrelated facts do not create relationships;
- require evidence/confidence for relationships;
- verify cross-model relationships only when explicitly supported by source evidence;
- test past/current/future/proposed/deprecated facts;
- verify migrations are idempotent and preserve old SQLite installs;
- verify graph/MCP/query surfaces preserve provenance.

Do not touch provider OAuth. Do not create broad refactors. Prefer tests first, then minimal implementation fixes.

Run pytest -q. Final report: bugs found, fixes made, tests added, risks left.
```

### 4. Xiaomi MiMo V2.5 Pro

```text
You are Xiaomi MiMo V2.5 Pro working in /Users/darshann/Desktop/context-engine on branch agent/xiaomi-repo-review-docs.

Read the whole repo at high level, especially README.md, project.md, TASK_PLAN.md, AGENTS.md, docs/, app/api/connectors.py, app/api/graph.py, frontend/src/pages/Connectors.jsx, frontend/src/pages/GraphView.jsx, tests/.

After Kimi, GLM, and DeepSeek have worked, perform long-context review:
- find stale claims, unsupported-provider overclaims, broken setup commands, missing docs, missing tests;
- update OSS readiness, connector docs, AI Context docs, graph contract docs;
- verify docs match code and latest test results;
- give an OSS readiness score with exact blockers.

Run pytest -q and npm run build if practical. Final report: findings by severity, docs changed, verification, launch blockers.
```

## Acceptance Criteria

- `pytest -q` passes.
- `npm run build` passes when frontend files change.
- Connector UI and backend agree on supported/unavailable states.
- AI Context import is useful for agent sessions and preserves provenance.
- Graph relationships are optional, conservative, evidence-backed, and temporal.
- Existing SQLite installs migrate safely.
- Docs describe what works, what is stubbed, and what is not implemented.
- Final Codex review can merge without guessing.
