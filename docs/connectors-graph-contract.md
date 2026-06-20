# Connector / Knowledge Graph Contract

Last updated: 2026-06-17

This is the current connector-to-graph contract for launch. Older audit details
were consolidated into this file so contributors do not have to reconcile stale
connector states with the current backend catalog.

## Non-Negotiables

- A connector is launch-available only when it can create `SourceDocument` rows
  through a tested route or mocked sync path.
- Coming-soon providers must never return placeholder success or appear
  configured.
- Demo seed data must not mark provider connectors as authenticated,
  configured, or connected.
- Every extracted graph fact should carry source provenance.
- Every relationship should carry evidence, origin, confidence, and status.
- MCP, query, and context packs must consume the structured graph, not a
  separate vector-only knowledge base.

## Connector Matrix

| Source | Launch status | Source document path | Graph behavior |
|---|---|---|---|
| Local files | Available | `/api/sources/upload`, `/api/sources`, CLI ingest | Regex/LLM extraction with source provenance. |
| AI sessions | Available | `/api/connectors/ai-context/import`, `/api/connectors/ai-session/ingest` | Deterministic session root, tasks, decisions, risks, file refs. |
| Slack | Available | OAuth/setup plus sync worker | Message roots anchor extracted facts through `discussed_in`. |
| GitHub | Available | PAT connect plus issue/PR sync | Deterministic issue, PR, file, review, `fixes`/`solves` edges. |
| Gmail | Available | Google OAuth plus Gmail sync path | Email/thread source docs with extracted facts and provenance. |
| Google Drive | Available | Google OAuth plus Drive sync path | Document source docs with extracted facts and provenance. |
| Discord | Coming soon | None | Catalog stub only. |
| Zoom | Coming soon | Unsupported sync path | Setup routes are guarded; do not imply transcript ingestion works at launch. |
| Wispr Flow | Coming soon | None | Catalog stub only. |
| Notion | Not catalogued | None | Do not describe as a current connector. |

## State Machine

| State | Meaning |
|---|---|
| `disconnected` | No workspace connector config exists. |
| `connected` | Workspace credentials/config exist for a launch-available connector. |
| `syncing` | A sync job is queued or running. |
| `failed` | Setup or sync failed with an error payload. |
| `coming_soon` | Visible roadmap item with no working sync path. |

Frontend actions must be derived from backend truth. If a connector is
`coming_soon`, the UI may explain what is missing but must not show a primary
action that appears to sync provider data.

## Source Document Requirements

Every connector-created source document should include:

- `source_type`
- `external_id`
- raw `content`
- `author` when known
- `source_url` when available
- metadata with workspace ID and provider identifiers

Source metadata should remain display-safe. Prefer IDs, titles, URLs, provider
state, repo names, channel names, thread IDs, session IDs, branch names, and
commit SHAs. Do not store secrets in metadata.

## Graph Requirements

Components should be atomic and typed. Preferred launch models include:

- `Decision`
- `Task`
- `Risk`
- `Feature`
- `Metric`
- `Issue`
- `PR`
- `Repo`
- `Message`
- `Email`
- `Document`
- `Agent Session`

Relationship origin must communicate trust:

| Origin | Use for |
|---|---|
| `deterministic` | Structured source evidence such as GitHub PR references and file changes. |
| `extracted` | Conservative source extraction from known source types. |
| `human_verified` | User-reviewed accepted edges. |
| `ai_proposed` | AI-suggested edges that need review. |
| `proposed` | Low-certainty or review-pending edges. |

Relationships without evidence should not be shown as trustworthy. If an edge is
created from a template fallback, the evidence should say that plainly.

## Query, MCP, And Context Packs

`POST /api/query` and MCP `query_context` share the `query.v1` response contract:

- retrieval controls: `top_k`, `min_confidence`, `hybrid`
- `trace.facts_used`
- `trace.relationships_used`
- source IDs and provenance fields
- relationship expansion from top matches

Context packs can be generated from the full graph or a selected component plus
one-hop neighbors. They should preserve source evidence and relationship
context so AI agents can act without rereading the whole workspace.

## Demo Seed

`POST /api/seed-demo` creates example source documents for GitHub, Slack, Gmail,
Google Drive, and Codex, then processes them immediately. It is intentionally
separate from connector auth and must not create fake connected provider states.

## Verification

Current launch verification:

- `python3 -m pytest tests/ -q`
- `ruff check app tests`
- `cd frontend && npm test`
- `cd frontend && npm run build`
