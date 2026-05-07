# Knowledge Graph Display Strategy

This document is the implementation contract for the graph UI. It is based on the current backend schema, taxonomy, extractors, graph API, and tests in this repository. It should not be treated as a product wish list; every field and category below must be backed by ingested connector data or by an explicit AI-proposed relationship with evidence.

## Verified Current State

- Components are the graph nodes. They represent decisions, tasks, blockers, risks, metrics, features, issues, PRs, changed files, agent sessions, AI steps, open questions, and generic facts.
- Relationships are the graph edges. They include deterministic links such as `solves`, `fixes`, `created_from`, `part_of`, `generated_by_agent`, `implemented_in`, `duplicates`, `supersedes`, `touches_file`, and `resolved_by`.
- Edge origin is part of the trust model. Valid origins are `deterministic`, `extracted`, `ai_proposed`, `human_verified`, and `proposed`.
- Source types must be canonicalized for filtering and grouping. API provenance should preserve the raw connector source label when tests or consumers rely on it.
- Agent-session aliases such as Codex, Claude, OpenCode, and `ai_context_*` normalize to `agent_session` for graph filtering.
- GitHub source payloads resolve to `github_issue` or `github_pr` using metadata when the raw connector source is `github`.

## Display Goal

The graph must answer three questions at a glance:

1. What is the project made of?
2. What work is active, blocked, planned, completed, or stale?
3. Which connector or agent produced the evidence behind each node and edge?

The UI should optimize for project comprehension, not for showing every raw entity at once.

## Node Organization

Use model/domain grouping as the first layout layer:

- Product and feature nodes: capabilities, user-facing work, project areas.
- GitHub work nodes: issues, PRs, changed files, review findings.
- Agent-session nodes: Claude, Codex, OpenCode, Kimi, GLM, and other imported AI sessions when present in source metadata.
- Decision nodes: explicit project decisions and accepted constraints.
- Risk and blocker nodes: unresolved blockers, review findings, stale items, security or quality risks.
- Task nodes: pending implementation, documentation, testing, and follow-up work.
- Context-source nodes: source documents, context packs, imported local files, chats, and connector records when a source needs to be visible.

Do not create a visual group unless the backend can identify the grouping from `model_name`, `fact_type`, `source_type`, metadata, or an explicit relationship.

## Edge Organization

Edges must communicate both relationship meaning and trust:

- Line label: canonical relationship type display label.
- Line style: origin.
- Line confidence: opacity or thickness.
- Line evidence: available on click or hover, never hidden behind AI-only wording.

Recommended style mapping:

- `deterministic`: solid blue.
- `extracted`: solid violet.
- `ai_proposed`: dashed amber.
- `human_verified`: solid green.
- `proposed`: dotted gray.

The graph should never visually imply certainty for `ai_proposed` or `proposed` edges.

## Layout Modes

### CEO View

Use this as the default. Show clusters for decisions, active tasks, blockers/risks, GitHub work, and agent sessions. Surface only the highest-confidence and highest-authority nodes first. Collapse low-confidence or stale items behind count badges.

### Bird's Eye

Show all major clusters with light detail. Use this to reveal disconnected areas, overloaded components, and source coverage gaps.

### Gap Detector

Prioritize missing links, isolated nodes, stale active work, unresolved blockers, unowned tasks, and PRs/issues without clear implementation or review status.

### Decision Trail

Start from decision nodes, then show what created them, what tasks or PRs implemented them, and which risks or blockers remain attached.

### AI Sessions

Group by agent/tool/session. Show what each session generated, touched, proposed, blocked, or verified. This view must distinguish agent-produced claims from deterministic connector facts.

## Connector Placement

Connector data should enter the graph as evidence-backed source nodes and typed components:

- GitHub issues: issue/task/risk nodes, linked to PRs through `solves`, `fixes`, `mentions`, or `blocks`.
- GitHub PRs: PR nodes linked to issues, changed files, review findings, commits, and implementation tasks.
- Agent sessions: session root nodes linked to decisions, tasks, blockers, changed files, and generated context.
- Local files and context packs: document/source nodes linked to extracted facts with `created_from` or `part_of`.
- Communication connectors: message, meeting, task, blocker, and decision nodes with provenance metadata.

No connector should bypass provenance. Every displayed item needs source type, source URL or external id when available, ingested time, and metadata summary.

## Backend Contract

The API must provide enough data for the UI to render without lazy lookups:

- `ComponentRead.relationship_count` must be precomputed from fetched relationships.
- `ComponentRead.source_type` must preserve the source document label; UI grouping should canonicalize it client-side or use a separate backend grouping field.
- `ComponentRead.source_metadata_summary` must include only display-safe summary fields such as session id, tool, model, branch, commit, author, number, state, title, item type, repo, and merged state.
- Relationship origins must be assigned in ingestion and returned unchanged by the API.
- Filters must operate on canonical source type, model, status, temporal state, confidence, and relationship origin.

## Frontend Contract

The graph UI should make these states visually unambiguous:

- Node status: active, needs review, proposed, stale, deprecated.
- Time horizon: current, future, past, unknown.
- Source family: GitHub, agent session, local/context pack, communication connector, other.
- Edge origin: deterministic, extracted, AI proposed, human verified, proposed.
- Confidence: low confidence must be visible and filterable.

Clicking a node should show source metadata, evidence excerpts, connected components, relationship count, and unresolved questions. Clicking an edge should show relationship type, origin, confidence, evidence, and source provenance.

## Anti-Hallucination Rules

- Do not display inferred relationships as deterministic.
- Do not label a node as GitHub PR, GitHub issue, Claude, Codex, OpenCode, Kimi, or GLM unless the source type or metadata supports it.
- Do not invent owners, blockers, PR statuses, merge status, or connector coverage.
- Do not merge duplicate-looking nodes unless canonical identity rules or explicit relationships support the merge.
- Do not hide stale, proposed, or low-confidence status behind color alone.

## Required Validation

Before shipping graph UI changes, run tests that cover:

- Source type canonicalization and GitHub item resolution.
- GitHub PR to issue relationship extraction.
- Review finding extraction.
- Relationship origin assignment.
- Graph API serialization under async sessions.
- Filters for model, source, status, temporal state, confidence, and edge origin.
- UI rendering of node groups, edge styles, metadata panels, and empty states.
