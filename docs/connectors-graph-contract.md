# Connector And Knowledge Graph Contract

Last updated: 2026-05-01

## Current State

### Implemented

- `GET /api/connectors` returns a wrapped object with `connectors` and `setupStatus`.
- Connector records include `connector_type` for frontend normalization.
- AI Context import is supported through `POST /api/connectors/ai-context/import`.
- AI-context source types are grouped in processing summaries:
  - `ai_context`
  - `ai_context_codex`
  - `ai_context_claude_code`
  - `ai_context_opencode`
- Slack, Discord, and Gmail do not have working external-provider sync paths.
- Slack connect is rejected instead of creating a fake connected state.
- `/api/graph` includes `active`, `needs_review`, and `proposed` components.
- SQLite startup migration adds `relationships.confidence` and `relationships.evidence` for existing local databases.

### Not Implemented Yet

- Slack OAuth install/callback and Slack API sync.
- Discord API sync.
- Gmail OAuth and mailbox sync.
- Zoom, Google Drive, Notion, GitHub, and Wispr provider backends.
- Alembic-based production migration management.
- A dedicated frontend AI Context import form.

## Connector Catalog Rules

Backend catalog lives in `app/api/connectors.py`.

Frontend catalog lives in `frontend/src/api/hooks.js`.

The catalogs must not contradict each other:

- implemented connector types must appear in the frontend catalog;
- frontend-only future connectors must use `coming_soon`;
- unsupported providers must not expose a working connect/sync UX;
- backend responses must include enough fields for `normalizeConnectors`.

Current backend connector types:

- `slack`: available in catalog, unsupported for connect/sync until OAuth exists.
- `discord`: coming soon.
- `gmail`: coming soon.
- `ai_context`: available through import endpoint.
- `local`: available through Sources workflow.

## AI Context Contract

AI context import accepts one or more documents with:

- `external_id`
- `content`
- optional `author`
- optional `tool`
- optional `session_type`
- optional `session_id`
- optional timestamps
- optional metadata

Tool mapping:

- `codex` -> `ai_context_codex`
- `claude_code` -> `ai_context_claude_code`
- `opencode` -> `ai_context_opencode`
- unknown or generic tools -> `ai_context`

Metadata must preserve `tool`, `session_type`, `session_id`, branch/task details, and `ingested_via=ai_context_import` when provided.

## Graph Contract

Graph responses must include:

- models with component counts;
- components with model ID/name, value, fact type, confidence, status, source document ID, source type, source URL, and ingestion time;
- relationships with source component, target component, type, confidence, and evidence.

Graph status visibility:

- `active`: current accepted context;
- `needs_review`: low-confidence or past context that needs review;
- `proposed`: future/planned context;
- stale/deprecated values stay hidden from default graph responses unless a future filter explicitly requests them.

## Relationship Rules

Relationships are optional.

Create relationships only when:

- the extractor returns an explicit relationship with confidence at or above threshold;
- a target component can be resolved without ambiguity;
- duplicate relationship rows are avoided;
- self-loops are rejected.

Do not create relationships from weak semantic similarity alone.

## SQLite Migration Contract

Startup runs `Base.metadata.create_all()` and then `run_migrations()`.

Current migration:

- no-ops when the `relationships` table does not exist;
- adds `relationships.confidence FLOAT NOT NULL DEFAULT 0.7` when missing;
- adds `relationships.evidence TEXT` when missing;
- backfills missing confidence/evidence values;
- is idempotent;
- does not overwrite existing custom values.

## Verification

Current expected checks:

```bash
pytest -q
cd frontend && npm run build
```

Latest verified result:

- `pytest -q`: 99 passed
- `npm run build`: passed

