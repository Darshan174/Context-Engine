# Task Plan

## Intended Outcome

Build `context-engine` into an OSS-grade state-of-work engine for AI-native
builders.

The first user is a solo founder or tiny team moving between Codex, Claude Code,
OpenCode, GitHub, chat, and local files. The product must answer:

- What changed?
- What is blocked or unresolved?
- Which agent decisions did not reach code, issues, or docs?
- What should happen next?
- What context should the next agent receive?

It should ingest project activity from local files, AI-agent sessions, and
provider connectors, then use a precise knowledge graph of:

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
- AI Context, local import, Slack, GitHub, Gmail, and Google Drive have source-document ingestion paths covered by tests or mocked sync tests.
- Discord, Zoom, Wispr Flow, and Notion should not be described as working launch connectors.
- Graph includes provenance, relationship evidence/confidence, and proposed context.
- Graph UX has a Board default with source clusters, Explore mode with force-layout logo nodes, right-rail inspector, trust styling toggle, refine drawer, search, minimap, local 1-hop/2-hop panel, and edge review.
- Board default opens at readable card zoom when whole-graph fit would hide labels; the minimap keeps overview context.
- Query API now exposes `query.v1`, retrieval knobs (`top_k`, `min_confidence`, `hybrid`), relationship expansion, and facts-used trace.
- Query now returns a deterministic source-backed answer summary when no AI answer model is configured.
- Query status/confidence filtering now happens in SQL before semantic/lexical ranking.
- Context packs can be generated from a selected graph component plus 1-hop neighbors, or from the full graph.
- MCP now exposes `query_context`, which returns the same `query.v1` trace contract for AI-agent consumers.
- MCP examples now cover installed CLI and local checkout configs plus an agent grounding prompt.
- Dashboard now includes an I/O card showing what feeds Context Engine and what agents consume.
- `/api/seed-demo` now creates an idempotent source-backed demo workspace from launch-available sources: GitHub, Slack, Gmail, Google Drive, and Codex.
- Generic extracted facts inherit document-level provenance when source-specific extractors did not already provide it.
- SQLite/SQLAlchemy schemas now include idempotent compound indexes for source-document sync lookup, pending extraction, component filtering, and relationship traversal.
- Docs were updated to distinguish unknown connectors, coming-soon stubs, and missing setup routes.
- Launch-facing docs now cover architecture, connectors, AI Context, Board vs Explore, and MCP.
- Docker build/start/health smoke passes through `docker-compose.smoke.yml` on port 18080.
- Source Manager now uses the shared frontend API client, separates unsupported/historical provider records from supported document imports, and has focused component coverage.
- Landing/mock frontend copy now uses launch-available sources only, and the Connectors page no longer exposes dormant Notion/Zoom manual-connect actions.
- Landing frontend smoke coverage now guards launch-source claims against stale unsupported-provider copy.
- AgentsView frontend smoke coverage now guards agent source claims against stale unsupported-provider copy.
- Frontend connector smoke tests now verify coming-soon providers stay disabled and launch connectors expose only backend-backed actions.
- Backend connector tests now verify direct Zoom setup and Notion token routes cannot create fake connected state.
- Community health files now include a security policy, issue forms, and a PR template aligned with provenance/evidence/connector-honesty rules.
- `scripts/smoke.sh` now provides the local launch gate plus optional Docker/API smoke for release tags.
- `scripts/doctor.sh` now provides read-only first-run diagnostics for Docker
  and bare-metal paths, and smoke syntax checks cover it.
- Bare-metal setup now creates `.venv`, validates Python versions robustly, uses `npm ci`, and the start/dev/smoke scripts reuse that interpreter.
- CLI ingest now honors `--sync` for single-file and bulk directory imports, with focused CLI/API coverage.
- README quick-start clone commands now use the real GitHub remote and a stable lowercase checkout directory, with docs coverage preventing placeholder regression.
- README now includes real seeded-demo screenshots and a linked demo walkthrough for first-time GitHub visitors.
- PyPI/installer metadata now includes MIT license, repository/issues URLs, keywords, and classifiers, with docs coverage preventing metadata drift.
- Dockerfile copies `LICENSE` before package install so license-file metadata works during container builds.
- Docker/API smoke now verifies demo seed, stats, query, and Zoom/Notion setup guardrails.
- CI now runs frontend tests and smoke-compose config validation in addition to backend tests, Ruff, frontend build, and Docker image build.
- Slack connector tests now match the current contract: OAuth/setup-backed availability, generic direct-connect rejection.
- OSS basics now include `LICENSE` and `CONTRIBUTING.md`.

## 5x Workload

### Phase 1: Contract and Product Shape

- Define the connector state machine: `available`, `coming_soon`, `unsupported`, `configured`, `connected`, `syncing`, `failed`.
- Define the graph ontology: model types, component fact types, relationship types, temporal statuses, confidence rules.
- Define AI Context import schema for Codex, Claude Code, OpenCode, Cursor, generic agent logs, diffs, plans, reviews, and terminal output.
- Define provider roadmap contracts for Slack, Discord, Gmail, Google Drive, Zoom, GitHub, Notion, Wispr Flow.
- Add explicit non-goals: no fake OAuth, no provider marked working without tested sync, no hallucinated graph edges.

### Phase 2: Connector Honesty and UX

- Keep Slack honest: available through OAuth/setup and tested sync paths, but not through generic direct connect.
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
- Keep graph/query/source indexes aligned with the read paths as the graph grows.
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
- Maintain CONTRIBUTING, architecture overview, connector guide, AI Context guide, graph contract docs, and release smoke instructions.
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
- Slack must appear available only through OAuth/setup and tested sync paths; generic direct connect must stay rejected.
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
