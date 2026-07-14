# Kimi Task — Founder Oversight Contract

## Role

You are Kimi K2.6, contract writer and dependency coordinator. Do not implement
product code in this slice.

## Mission

Turn the active `2026-07-14 YC Fall 2026 founder-oversight milestone` in
`TASK_PLAN.md` into one exact, implementation-ready contract for the focused task,
observed run, scrutiny finding, and UI flows.

## Read first

- `AGENTS.md`
- `TASK_PLAN.md`
- `app/models.py`
- `app/schemas.py`
- `app/api/context.py`
- `app/api/context_digest.py`
- `app/mcp/server.py`
- `app/services/context_compiler.py`
- `frontend/src/pages/ContextMapPage.jsx`
- `frontend/src/context-map/components/ContextInspector.jsx`
- `frontend/src/context-map/components/DigestBoard.jsx`
- relevant compiler, MCP, digest, and frontend tests

## Required decisions

1. Specify how a selected Component becomes a context-pack focus while preserving
   trusted objective origin and avoiding a premature universal WorkItem model.
2. Specify stable runtime event identity, retry behavior, source revision behavior,
   and which durable observations enter the extraction pipeline.
3. Define the run-timeline payload and factual state vocabulary.
4. Define scrutiny finding inputs, outputs, source links, severities, and wording.
5. Define the minimal frontend changes and responsive states without adding a route.
6. Map migrations, backend ownership, frontend ownership, tests, and merge order.

## Truth vocabulary

Use only states supported by observations:

- `not_attempted`
- `no_completion_evidence`
- `verification_missing`
- `verification_failed`
- `blocked`
- `completed_unverified`
- `verified`
- `stale_source`
- `conflicting_evidence`

Do not use `ignored`, `slop`, `bad code`, or `complete` as inferred judgements.

## Deliverable

Create or refresh one contract document under `docs/` with:

- Observed baseline with file/function evidence;
- exact schema and API changes;
- example request/response payloads;
- UI state and placement contract;
- migration and rollback considerations;
- focused fixtures and acceptance tests;
- explicit Proposed and Not implemented yet sections.

Do not edit implementation files. Report changed files, evidence, risks, and gaps.
