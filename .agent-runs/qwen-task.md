# Qwen 3.6 Task

## Coding Capability Rank

4 of 5.

Qwen is a senior schema, API, display, and integration engineer for this round. Use it for graph data modeling, display-readiness, API contracts, and cross-surface consistency.

## Branch

`agent/qwen-graph-display-api`

## Mission

Engineer the knowledge display layer for models, components, and relationships so GitHub issues/PRs and AI markdown sessions are understandable in the product.

Do not work on connector availability or provider OAuth.

## Current Repo Facts To Verify First

- `frontend/src/pages/GraphView.jsx` is the main graph screen.
- `frontend/src/api/hooks.js` and `frontend/src/api/client.js` define data access patterns.
- `app/api/graph.py` exposes graph data.
- `app/api/models_api.py` exposes model-specific data.
- `app/models.py` and `app/taxonomy.py` define persisted graph semantics.

If the current frontend graph has moved, report the actual files.

## 10x Workload

### 1. Display Data Contract

Make the backend/frontend contract explicit for graph display:

- component display title;
- model name;
- component/fact type;
- source type;
- source ID/URL;
- temporal state;
- status;
- confidence;
- evidence excerpt;
- metadata summary;
- relationship count;
- inbound/outbound relationship counts.

For relationships:

- source node;
- target node;
- type;
- display label;
- confidence;
- evidence;
- status;
- origin: deterministic, extracted, AI-proposed, human-verified if available.

### 2. Knowledge Display Modes

Design and implement, or prepare implementation-ready specs for:

- model overview;
- component table/inspector;
- relationship table/inspector;
- source-to-knowledge diff;
- work lens: blockers, open decisions, active tasks, unresolved questions;
- graph canvas with filters;
- context-pack selection lens.

The table/inspector view should be treated as first-class because it is easier to debug than a graph canvas.

### 3. Graph UI Behavior

Ensure the UI can show:

- GitHub issue nodes;
- GitHub PR nodes;
- changed file/module nodes;
- AI session nodes;
- extracted task/decision/risk nodes;
- deterministic edges as solid;
- proposed/candidate edges as dashed or visually secondary;
- low-confidence edges hidden by default;
- selected edge evidence in a side panel.

### 4. Filtering and Search

Add or specify filters for:

- source type: GitHub issue, GitHub PR, AI markdown session, local file, docs;
- model;
- component type;
- relationship type;
- relationship status;
- confidence threshold;
- temporal;
- source document.

### 5. Source-to-Knowledge Diff

Implement or specify a view that answers:

- What did this source add?
- Which models changed?
- Which components were created?
- Which relationships were created?
- Which edges are proposed/candidate?
- Which components are duplicates or updates?
- What evidence backs each item?

This is the trust-building workflow for newly imported GitHub and AI-session sources.

### 6. API and State Management

If existing `/api/graph` is too broad, add or specify:

- graph slice endpoint;
- source diff endpoint;
- component detail endpoint;
- relationship detail endpoint;
- work lens endpoint;
- context-pack input endpoint.

Reuse existing FastAPI/Pydantic and React Query patterns.

### 7. Verification

Run:

- `npm run build` if frontend files change;
- relevant backend tests if API files change;
- `pytest -q` if backend graph contracts change broadly.

## Deliverables

Final report must include:

- files changed;
- display/API contracts added;
- screenshots or payload examples if practical;
- frontend build result;
- backend test result if applicable;
- unresolved UX/data risks.

## Rules

- No connector/OAuth work.
- Do not hide missing data with vague UI copy.
- Do not make unsupported relationship claims in display text.
- Display provenance and evidence close to every selected node/edge.
- Prefer dense, debuggable engineering UI over marketing-style graph visuals.
