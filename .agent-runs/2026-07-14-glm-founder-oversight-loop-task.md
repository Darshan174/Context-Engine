# GLM Task — Focused Task and Observed Run Loop

## Role

You are GLM 5.1, primary implementation agent. Work only after the Kimi contract is
accepted by Codex.

## Mission

Implement one complete, source-backed founder workflow from a selected Project-map
record to a prepared agent pack and an inspectable observed outcome.

## Required behavior

### Focused preparation

- A supported selected task, requirement, decision, or blocker can become the focus
  of `context_pack.v2`.
- Objective origin is stored as trusted human input or explicit source evidence.
- Arbitrary project content cannot silently become a task objective.
- Existing HTTP, MCP, CLI, and compiler paths continue to share one compiler.

### Retry-safe observation

- Runtime write tools accept or deterministically derive a stable event identity.
- Retrying an event does not create duplicate source evidence or observations.
- Raw source evidence is persisted before extraction/projection.
- Durable outcomes, checks, blockers, and patch summaries are reconciled through the
  normal evidence pipeline; routine noise remains only in the source ledger.

### UI

- The existing inspector exposes `Prepare for agent` for supported focused records.
- The no-objective toolbar action is labelled `Copy project brief`.
- The Project bar shows current focus and the latest factual outcome compactly.
- The inspector shows an accessible run timeline with files, checks, blockers,
  outcome, timestamps, and source links.
- No new top-level route, large form, raw terminal stream, readiness percentage, or
  speculative agent-quality judgement is introduced.

## Likely files

Verify the contract before touching these:

- `app/models.py` and a migration
- `app/schemas.py`
- `app/api/context.py`
- `app/api/context_digest.py` or a focused run endpoint
- `app/mcp/server.py`
- `app/services/context_compiler.py`
- `frontend/src/pages/ContextMapPage.jsx`
- `frontend/src/context-map/components/ContextInspector.jsx`
- `frontend/src/context-map/components/DigestBoard.jsx`
- focused backend/frontend tests

Preserve unrelated active frontend and ingestion changes.

## Acceptance gates

- A selected evidenced task produces a persisted pack linked to that focus.
- A repeated runtime event is idempotent.
- A terminal outcome remains source-backed and becomes visible in the focused run
  timeline after normal processing.
- Missing data is displayed as unknown, never filled with demo assumptions.
- Evidence is one action away from every timeline assertion.
- Focused tests, full backend/frontend suites, production build, and desktop/mobile
  visual checks pass.

## Report

Separate Observed, Implemented, Proposed, and Not implemented yet. Include changed
files, tests, evidence, risks, migration impact, and remaining gaps.
