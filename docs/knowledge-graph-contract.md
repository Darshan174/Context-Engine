# Knowledge Graph 10x Contract

> **Scope:** Models, components, relationships, GitHub issues/PRs, AI markdown sessions, display semantics, provenance, temporal state, and context-pack readiness.  
> **Not in scope:** Connector availability, provider OAuth, sync workers.  
> **Branch:** `agent/kimi-knowledge-graph-contract`  
> **Agent:** Kimi K2.6  
> **Date:** 2026-05-04

> **Current status note, refreshed 2026-06-18:** This is a historical contract
> review, not launch copy. Several proposed items below are now implemented:
> relationship `origin`, component `provenance`/`excerpt`, deterministic GitHub
> issue/PR extraction, deterministic agent-session extraction, evidence-backed
> inferred relationships, Board/Explore graph UX, Work/Gaps lens presets, and
> selection-scoped context packs.

---

## 1. Observed Current Behavior (with evidence)

### 1.1 Database Schema

**Observed:** `app/models.py` (lines 83–193) defines five knowledge-graph tables:

- `SourceDocument` — raw ingested content with `source_type`, `external_id`, `content`, `author`, `source_url`, `metadata_json`.
- `Model` — domain bucket with `name` (unique) and `description`.
- `Component` — atomic fact with `model_id`, `source_document_id`, `name`, `value`, `fact_type`, `temporal`, `confidence`, `authority_weight`, `embedding`, `status`, `valid_from`, `valid_to`, `superseded_by_id`.
- `Relationship` — directed edge with `source_component_id`, `target_component_id`, `relationship_type`, `confidence`, `evidence`, `status`.

**Current status:** The `Component` table still derives `source_url` and
`source_external_id` through `source_document`, but it now stores component-level
`provenance` and `excerpt` fields for extracted evidence.

**Current status:** `Relationship` now stores `origin` and the graph UI can
approve/reject proposed relationships through the review endpoint.

### 1.2 Taxonomy

**Observed:** `app/taxonomy.py` (lines 5–121) defines:

- `CANONICAL_MODEL_NAMES` — 21 names including `Agent Session`, `Context Pack`, `Decision`, `Document`, `Feature`, `GitHub`, `Issue`, `Metric`, `Person`, `PR`, `Repo`, `Risk`, `Task`, `Team`, `User`.
- `_MODEL_ALIASES` — maps plural and lowercase inputs to canonical names.
- `VALID_RELATIONSHIP_TYPES` — 16 types: `assigned_to`, `blocked_by`, `blocks`, `caused_by`, `co_occurs`, `confirms`, `contains`, `contradicts`, `created_from`, `decides`, `depends_on`, `discussed_in`, `duplicates`, `enables`, `generated_by_agent`, `implemented_in`, `mentions`, `owned_by`, `part_of`, `related_to`, `solves`, `supersedes`, `verified_by_human`.

**Current status:** `VALID_RELATIONSHIP_TYPES` now includes `implements`,
`fixes`, `resolved_by`, `conflicts_with`, `touches_file`, and
`verified_by_human`.

### 1.3 Extraction

**Observed:** `app/processing/extractor.py` (lines 35–112) defines `EXTRACTION_PROMPT` which:

- Enumerates canonical entity types (`CORE`, `WORK`, `STRATEGY`, `AI WORK`).
- Returns JSON with `facts[].model_name`, `name`, `value`, `fact_type`, `temporal`, `confidence`, `relationships[]`.
- Relationship types in the prompt: `created_from`, `mentions`, `decides`, `blocks`, `solves`, `depends_on`, `assigned_to`, `owned_by`, `implemented_in`, `discussed_in`, `caused_by`, `supersedes`, `generated_by_agent`, `verified_by_human`, `contradicts`, `part_of`.

**Observed:** Regex fallback (`_regex_extract`, lines 178–275) detects decisions, tasks, blockers, features, metrics, meeting outcomes, and agent steps. It does **not** create relationships.

**Evidence:** `tests/test_extraction.py` (lines 63–68) asserts `test_regex_extractor_no_relationships`.

### 1.4 Ingestion / Graph Building

**Observed:** `app/services/ingest.py` (`IngestionService`):

- `process_document` (lines 27–59) calls extractor, creates/upserts components, generates embeddings, and creates relationships.
- `_upsert_component` (lines 70–104) sets `status = "needs_review"` if `confidence < 0.6`; sets `status = "proposed"` if `temporal == "future"`; sets `status = "needs_review"` if `temporal == "past"`.
- `_create_relationship` (lines 106–157) skips relationships with `confidence < 0.6`, resolves target by name (same-model preferred, cross-model fallback), prevents duplicates and self-loops, and stores `evidence` (template-generated if absent).

**Evidence:** `tests/test_ingestion.py` covers cross-model relationships (lines 13–65), confidence thresholds (lines 109–146), duplicate/self-loop prevention (lines 187–261), temporal status mapping (lines 264–320), and relationship evidence storage (lines 418–496).

**Current status:** `Relationship.origin` is present and ingestion sets
deterministic/extracted/proposed origins through `canonical_origin()`.

### 1.5 Graph API

**Observed:** `app/api/graph.py`:

- `GET /api/graph` (lines 65–143) returns `GraphResponse` with models, components (including provenance fields `source_type`, `source_url`, `ingested_at`), and relationships (including `confidence`, `evidence`).
- Filters: `model_id`, `source_type`, `workspace_id`.
- Status filter includes `active`, `needs_review`, `proposed` (line 80). Excludes `stale`.
- `PATCH /api/components/{component_id}` (lines 146–158) updates component status.
- `GET /api/stats` (lines 171–198) counts `pending_review`, `proposed`, `stale`.
- `GET /api/timeline` (lines 251–289) returns source-ingest and component-created events.
- `POST /api/graph/build` (lines 219–227) delegates to `GraphBuilderAgent`.

**Evidence:** `tests/test_graph_api.py` (lines 10–501) proves provenance fields, source-type filtering, workspace filtering, stats, timeline, proposed visibility, and stale exclusion.

### 1.6 Cross-Document Inference

**Current status:** `app/agents/graph_builder.py` scans component values for
names of other components and creates review-oriented `related_to` candidates
when found across documents.

**Current status:** Cross-document inference now writes review-oriented
evidence and `origin = "ai_proposed"` for candidate relationships.

### 1.7 AI Agents

**Observed:** Four agent surfaces exist:

1. `ContextPackAgent` (`app/agents/context_pack.py`, lines 43–153) — rule-based or LLM-generated handoff document. Groups by model bucket, outputs Current State, Open Decisions, Active Blockers, Past AI Agent Attempts, Next 5 Tasks, Key Relationships.
2. `GapDetectorAgent` (`app/agents/gap_detector.py`, lines 72–281) — rule-based or LLM analysis for missing owners, unimplemented decisions, blocked items, orphaned entities.
3. `RelationshipAgent` (`app/agents/relationship_agent.py`, lines 69–198) — LLM-suggested hidden relationships. Persists suggestions with `status = "proposed"` and `confidence >= 0.6`.
4. `GraphBuilderAgent` (`app/agents/graph_builder.py`, lines 15–147) — processes pending docs and infers cross-doc relationships.

**Evidence:** `tests/test_agents.py` (lines 10–111) tests gap detector normalization and relationship agent persistence.

### 1.8 Frontend Display

**Observed:** `frontend/src/pages/GraphView.jsx` (lines 1–1651):

- Cytoscape canvas with model compound nodes and component card nodes.
- Status → border color mapping (`CARD_STATUS`, lines 23–35).
- Temporal → chip badge (`TEMPORAL_BADGE`, lines 52–53; `TEMPORAL_META`, lines 55–60).
- CEO Views: `all`, `birdsEye`, `gaps`, `decisions`, `aiSessions` (lines 89–101).
- Filters: model, source_type, status, temporal (lines 130–135).
- Selected node inspector shows provenance, confidence, connections (lines 1135–1244).
- Edge labels reveal on hover/selection (lines 706–719).
- Agents sidebar panel with Gap Detector, Relationship Agent, Context Pack (lines 1392–1651).

**Current status:** Board is the default graph mode, Explore is available for
local connection traversal, lens presets include work/gaps-style filters, and
context packs can be generated from the selected component plus 1-hop neighbors.

---

## 2. Proposed Contract

### 2.1 Graph Ontology Contract

#### 2.1.1 Model Types

Canonical model names **must** be drawn from this set:

| Model | Purpose |
|-------|---------|
| `Feature` | Product capabilities, user-facing functionality |
| `Task` | Action items, todos, follow-ups, things to build |
| `Issue` | Bug reports, feature requests, tickets |
| `PR` | Pull requests, code reviews, merges |
| `Decision` | Choices made, options selected, directions set |
| `Risk` | Blockers, concerns, unknowns, dependencies at risk |
| `Repo` | Code repositories, modules, services |
| `Document` | Specs, RFCs, design docs, runbooks, wikis |
| `Agent Session` | AI coding/conversation sessions |
| `Context Pack` | Curated context bundles for AI sessions |
| `Person` | Individuals, authors, assignees, reviewers |
| `Team` | Engineering teams, functional groups |
| `Metric` | Numbers, KPIs, success criteria, targets |

**Observed:** All except `Context Pack` are already in `CANONICAL_MODEL_NAMES`. `Context Pack` is already present in `app/taxonomy.py` line 8.

#### 2.1.2 Component Types

Each component **must** carry a `fact_type` drawn from this vocabulary:

| `fact_type` | Meaning | Typical Model |
|-------------|---------|---------------|
| `github_issue` | GitHub issue title/body/state/labels | `Issue` |
| `github_pr` | GitHub PR title/body/state/merged | `PR` |
| `pr_review_finding` | PR review comment or approval finding | `Risk`, `Issue`, `Task` |
| `commit_reference` | Commit hash or reference | `Repo` |
| `changed_file` | File or module changed in a PR | `Repo` |
| `ai_session` | Root of an AI markdown session | `Agent Session` |
| `ai_task` | Actionable task extracted from AI session | `Task` |
| `ai_decision` | Decision extracted from AI session | `Decision` |
| `ai_blocker` | Blocker extracted from AI session | `Risk` |
| `open_question` | Unresolved question from any source | `Document` |
| `extracted_fact` | Generic source-backed fact | any |
| `decision` | Human-made decision | `Decision` |
| `task` | Human-created task | `Task` |
| `blocker` | Human-identified blocker | `Risk` |
| `feature` | Human-identified feature | `Feature` |
| `metric` | Human-identified metric | `Metric` |
| `meeting_note` | Meeting outcome or note | `Meeting` |
| `ai_step` | AI session step or attempt | `Agent Session` |

**Current status:** The `fact_type` column is still a `String(50)`, but
`app/taxonomy.py` now defines `VALID_FACT_TYPES` and helper normalization for
extractors/API code.

#### 2.1.3 Required Component Fields

Every component row **must** populate:

| Field | Source | Contract |
|-------|--------|----------|
| `name` | Extractor or deterministic rule | Stable, unique within model, max 255 chars. Must be specific (bad: "Auth decision", good: "OAuth2 rate limit auth decision Q1-2025"). |
| `value` | Source text or excerpt | Full description or exact quote from source, max text. |
| `fact_type` | Deterministic rule or extractor | From 2.1.2 vocabulary. |
| `source_document_id` | Ingestion service | FK to `source_documents`. |
| `source_type` | Derived from `SourceDocument.source_type` | Must be present in API response (observed). |
| `source_url` | Derived from `SourceDocument.source_url` | Must be present in API response (observed). |
| `excerpt` | Implemented field | Source quote or compact evidence excerpt that justifies this component. |
| `provenance` | Implemented field | JSON/string metadata describing source family, external ID, tool, repo, or session context. |
| `confidence` | Extractor or rule | 0.0–1.0. `< 0.6` → `needs_review`. |
| `temporal` | Extractor or `_detect_temporal_hint` | One of `current`, `past`, `future`, `unknown`. |
| `status` | Ingestion rule | `active`, `needs_review`, `proposed`, `stale`. Future temporal → `proposed`. Past temporal → `needs_review`. Low confidence → `needs_review`. |
| `metadata_json` | SourceDocument metadata + extraction metadata | JSON blob with keys: `source_external_id`, `extractor_version`, `extraction_method` (`llm` or `regex`). |

#### 2.1.4 Required Relationship Fields

Every relationship row **must** populate:

| Field | Contract |
|-------|----------|
| `source_component_id` | FK to components. |
| `target_component_id` | FK to components. Must not equal source (self-loop forbidden). |
| `relationship_type` | From 2.2 taxonomy. |
| `evidence` | Non-null, non-empty string. Direct quote or deterministic rule description. Max 2048 chars. |
| `confidence` | 0.0–1.0. `< 0.6` → row rejected. |
| `status` | `active`, `proposed`, `rejected`. |
| `origin` | Implemented field. Current normalized values include `deterministic`, `extracted`, `ai_proposed`, `human_verified`, and `proposed`. |

**Current status:** `origin` exists on `Relationship`; ingestion and graph
builders set origin and evidence for deterministic, extracted, and proposed
edges.

---

## 3. Relationship Taxonomy Contract

### 3.1 Canonical Types

The following types **must** be supported. New types require a migration and a display mapping.

| Type | Inverse | Allowed Source → Target | Deterministic Evidence | AI May Propose? | Min Conf | Display Label | Visible by Default |
|------|---------|------------------------|------------------------|-----------------|----------|---------------|-------------------|
| `implements` | `implemented_in` | `Task` → `Feature`, `PR` → `Feature` | PR body contains "implements #123" or task title references feature | No (deterministic) | 0.85 | Implements | Yes |
| `implemented_in` | `implements` | `Feature` → `PR`, `Decision` → `PR` | Same as above, reversed | No | 0.85 | Implemented in | Yes |
| `fixes` | `resolved_by` | `PR` → `Issue` | PR body contains "fixes #123" or "closes #123" | No | 0.90 | Fixes | Yes |
| `resolved_by` | `fixes` | `Issue` → `PR` | Same as above, reversed | No | 0.90 | Resolved by | Yes |
| `blocks` | `blocked_by` | `Risk` → `Task`, `Issue` → `PR`, `Decision` → `Task` | Explicit blocker statement in source | Yes, if wording is ambiguous | 0.75 | Blocks | Yes |
| `blocked_by` | `blocks` | `Task` → `Risk`, `PR` → `Issue` | Same as above, reversed | Yes | 0.75 | Blocked by | Yes |
| `depends_on` | — | any → any | Explicit "depends on", "requires", "blocked until" | Yes | 0.70 | Depends on | Yes |
| `conflicts_with` | `conflicts_with` | `Decision` → `Decision`, `PR` → `PR` | Source explicitly states conflict or contradiction | Yes | 0.80 | Conflicts with | Yes |
| `supersedes` | — | `Decision` → `Decision`, `Task` → `Task` | Source says "replaces", "deprecates", "old approach" | Yes | 0.80 | Supersedes | Yes |
| `duplicates` | `duplicates` | `Issue` → `Issue`, `Task` → `Task` | Same title or explicit "duplicate of #123" | Yes | 0.75 | Duplicates | No (hidden, review queue) |
| `mentions` | — | any → any | Name or ID appears in source text | No (deterministic) | 0.60 | Mentions | No |
| `discussed_in` | — | `Decision` → `Meeting`, `Issue` → `Meeting` | Decision/issue referenced in meeting transcript | Yes | 0.70 | Discussed in | Yes |
| `generated_by_agent` | — | `Decision` → `Agent Session`, `Task` → `Agent Session` | Session output contains the decision/task text | No (deterministic) | 0.85 | Generated by agent | Yes |
| `touches_file` | — | `PR` → `Repo`, `Commit` → `Repo` | PR changed-files list or commit diff | No | 0.90 | Touches file | Yes |
| `created_from` | — | `PR` → `Issue`, `Task` → `Decision` | Source explicitly says "created from #123" | No | 0.85 | Created from | Yes |
| `verified_by_human` | — | any → `Person` | Human comment says "confirmed" or "verified" | No | 0.90 | Verified by human | Yes |
| `related_to` | — | any → any | Cross-document name match or AI suggestion with reasoning | Yes | 0.60 | Related to | No (low-confidence default hidden) |

**Current status:** `fixes`, `resolved_by`, `conflicts_with`, `touches_file`,
`implements`, and `implemented_in` are all in `VALID_RELATIONSHIP_TYPES`.

### 3.2 Relationship Creation Rules

1. **Deterministic relationships** (`origin = "deterministic"`) **must** have evidence that is a direct quote from the source text, or a generated string that includes the exact quote. They are created with `status = "active"`.
2. **AI-proposed relationships** (`origin = "ai_proposed"`) **must** have evidence that is the AI's reasoning string. They are created with `status = "proposed"`.
3. **No relationship may be created with `evidence = NULL` or empty string.** Current deterministic and cross-document inference paths populate evidence.
4. **Self-loops are forbidden.** (Observed: enforced in `app/services/ingest.py`, line 120.)
5. **Duplicate edges** (same source, target, type) are forbidden. (Observed: enforced in `app/services/ingest.py`, lines 136–144.)

---

## 4. GitHub Issue/PR Knowledge Contract

### 4.1 Source Document Ingestion

When a `SourceDocument` has `source_type = "github_issue"` or `source_type = "github_pull_request"`:

**Observed:** The backend has no dedicated GitHub ingestion parser. The generic `IngestionService.process_document` treats GitHub content as plain text and runs the LLM/regex extractor.

**Proposed:** A deterministic `GitHubExtractor` must run **before** the generic LLM extractor for GitHub sources.

### 4.2 Issue Components

From a GitHub issue source document, the following components **must** be created deterministically:

| Component | `fact_type` | `name` | `value` | `temporal` |
|-----------|-------------|--------|---------|------------|
| Issue root | `github_issue` | `Issue #{n}: {title}` | Body text | `current` if open, `past` if closed |
| Issue state | `github_issue` | `Issue #{n} state` | `open` / `closed` | derived |
| Each label | `github_issue` | `Label: {name}` | `{name}` | `current` |
| Assignee (if any) | `github_issue` | `Assignee: {login}` | `{login}` | `current` |
| Milestone (if any) | `github_issue` | `Milestone: {title}` | `{title}` | `current` |

**Metadata expectations:**
```json
{
  "repo_full_name": "owner/repo",
  "issue_number": 42,
  "issue_state": "open",
  "labels": ["bug", "priority-high"],
  "assignee": "octocat",
  "milestone": "v1.0",
  "created_at": "2026-04-01T10:00:00Z",
  "updated_at": "2026-04-01T12:00:00Z",
  "closed_at": null
}
```

### 4.3 PR Components

From a GitHub PR source document:

| Component | `fact_type` | `name` | `value` |
|-----------|-------------|--------|---------|
| PR root | `github_pr` | `PR #{n}: {title}` | Body text |
| PR state | `github_pr` | `PR #{n} state` | `open` / `closed` / `merged` |
| Merged status | `github_pr` | `PR #{n} merged` | `true` / `false` |
| Each review finding | `pr_review_finding` | `Review: {excerpt}` | Full comment text |
| Each changed file | `changed_file` | `File: {path}` | `+{additions}/-{deletions}` |
| Commit reference | `commit_reference` | `Commit: {sha}` | Message or URL |

### 4.4 Deterministic Relationships from GitHub

| Source | Target | Type | Evidence Rule |
|--------|--------|------|---------------|
| PR root | Issue root | `fixes` | PR body or title contains `fixes #N`, `closes #N`, `resolves #N` |
| Issue root | PR root | `resolved_by` | Inverse of above |
| PR root | Changed file | `touches_file` | PR changed-files list |
| Changed file | Repo model component | `part_of` | File path prefix matches repo name |
| Review finding → Risk wording | Issue root | `blocks` | Review says "blocked by #N" |
| Review finding → Task wording | Task component | `implements` | Review says "should implement X" |

### 4.5 Edge Cases

| Case | Rule |
|------|------|
| Duplicate issue and PR names | Deduplicate by `repo_full_name` + number. If same title, link with `duplicates` and queue for review. |
| Stale closed issues referenced by current sessions | Issue component gets `temporal = "past"`, `status = "needs_review"`. Current session component gets `mentions` relationship to issue. |
| PRs touching many files | Cap at 50 `changed_file` components per PR. Store full list in `metadata_json`. |
| Comments mentioning unrelated nouns | Only create `mentions` relationships when the exact component `name` appears in the comment text. |
| AI-generated PR descriptions | Treat description as lower-confidence (`confidence = 0.6`). Do not create deterministic `fixes` edges from AI-generated closing keywords unless verified by human. |

---

## 5. AI Markdown Session Knowledge Contract

### 5.1 Session Root Component

When a `SourceDocument` has `source_type` in `ai_context`, `ai_context_codex`, `ai_context_claude_code`, `ai_context_opencode`:

**Observed:** The backend maps tools to source types in `app/api/connectors.py` (lines 529–535): `codex` → `ai_context_codex`, `claude_code` → `ai_context_claude_code`, `opencode` → `ai_context_opencode`, generic → `ai_context`.

**Proposed:** A deterministic `AISessionExtractor` must run before generic extraction.

The session root component:

| Field | Value |
|-------|-------|
| `model_name` | `Agent Session` |
| `fact_type` | `ai_session` |
| `name` | `{tool} session {session_id}` or `{tool} session {started_at}` |
| `value` | First 2000 chars of content |
| `temporal` | `past` if `ended_at` present and > 24h ago, else `current` |

### 5.2 Section Rules

- **Headings (`#`, `##`)** → Add to session context in `metadata_json.sections[]`. Do **not** create components automatically.
- **Task lists (`- [ ]` or `- [x]`)** → Create `Task` components **only** when:
  - Checkbox is unchecked (`[ ]`) and text is actionable (contains a verb).
  - `temporal = "future"` for unchecked, `"past"` for checked.
- **Final recommendations** → Create `Decision` or `Risk` components **only** when the recommendation is backed by a direct quote from the session text.
- **Review findings** → Create `Risk` or `Issue` components when the session explicitly flags a problem.
- **File references** (`app/models.py`, `docs/contract.md`) → Create `Document` or `Repo` components with `fact_type = "extracted_fact"`.

### 5.3 Metadata Expectations

```json
{
  "session_id": "uuid",
  "tool": "codex",
  "model": "claude-sonnet-4",
  "branch": "agent/kimi-knowledge-graph-contract",
  "commit": "abc1234",
  "author": "Kimi K2.6",
  "started_at": "2026-05-04T10:00:00Z",
  "ended_at": "2026-05-04T12:00:00Z",
  "sections": ["Graph Ontology", "Relationship Taxonomy"]
}
```

### 5.4 Must Not Extract

| Category | Rule |
|----------|------|
| Generic narration | Skip sentences that are purely procedural ("Now I will read the file"). |
| Duplicate restatements | Skip if the same fact was already extracted from an earlier session by the same author within 24h. |
| Low-specificity claims | Skip claims without nouns or proper names ("things are improving"). |
| Uncited market claims | Skip market size, competitor moves unless a source URL is provided in the session. |
| Agent speculation | Skip "I think", "maybe", "perhaps" statements with no supporting evidence in the text. |

---

## 6. Display Contract

### 6.1 Source-to-Knowledge Diff

**Proposed new view.** When a source document is selected, the UI must show:

- Source document metadata (type, URL, ingested_at).
- List of components created from this source.
- List of relationships created from this source.
- For each relationship, highlight whether it is `deterministic` or `ai_suggested`.

**Implementation:** Add `GET /api/sources/{source_document_id}/diff` endpoint.

### 6.2 Model Overview

**Observed:** `GET /api/graph` already returns `component_count` per model (line 122). `GET /api/stats` returns totals.

**Proposed enhancement:** Model overview card must show:
- Component count.
- Count of components by status (`active`, `needs_review`, `proposed`, `stale`).
- Average confidence.
- Count of isolated components (no relationships).

### 6.3 Component Inspector

**Observed:** `GraphView.jsx` selected node panel (lines 1135–1244) shows `fact_type`, `status`, `temporal`, `confidence`, `source_type`, `source_url`, and connected nodes.

**Proposed enhancement:** Add:
- `evidence_excerpt` (when implemented).
- `authority_weight`.
- `valid_from` / `valid_to`.
- `superseded_by` link.
- Temporal state badge with explicit label (`Current`, `Past`, `Future`, `Unknown`).

### 6.4 Relationship Inspector

**Proposed enhancement:** When an edge is selected, show:
- `relationship_type` with human-readable label.
- `evidence` (the full evidence string).
- `confidence` bar.
- `origin` badge (`deterministic` vs `ai_suggested`).
- `status` badge (`active`, `proposed`, `rejected`).
- Action buttons: "Approve" (proposed → active), "Reject" (proposed → rejected).

### 6.5 Graph Canvas

**Observed:** `GraphView.jsx` uses Cytoscape with:
- Model compound nodes (colored borders).
- Component card nodes (status-colored borders, temporal chips).
- Edge opacity 0.45, label revealed on hover.

**Proposed contract:**
- **Clusters:** Group by `model_id` (compound nodes) — already implemented.
- **Shape/icon by source type:** Not yet implemented. Proposed:
  - `github_issue` / `github_pr` → GitHub icon node shape.
  - `slack` / `discord` → Message bubble.
  - `ai_context_*` → Bot/robot icon.
  - `local` / `document` → Document icon.
- **Edge style by relationship status:**
  - `active` → solid, full opacity.
  - `proposed` → dashed, 60% opacity, muted color.
  - `rejected` → not rendered (filtered out).

### 6.6 Work Lens

**Current status:** Graph lens presets now include work/gaps-style filters that
surface high-signal blockers, decisions, questions, and active tasks.

The intended dedicated work lens shows only:

- Blockers: `Risk` components with `status = "active"` and `temporal = "current"`.
- Open decisions: `Decision` components with `status = "active"` and no outgoing `implemented_in` relationship.
- Unresolved questions: `Document` components with `fact_type = "open_question"`.
- Active tasks: `Task` components with `status = "active"` and `temporal = "current"`.

### 6.7 Context-Pack Lens

**Current status:** `ContextPackAgent` can generate from the full graph or from
selected `component_ids`.

Implemented selected-slice behavior:

1. User selects one or more components on the canvas.
2. Frontend POSTs `component_ids` to `/api/agents/context-pack`.
3. Backend fetches the selected components plus 1-hop neighbors.
4. Context pack includes only the selected slice.

---

## 7. Acceptance Criteria

These criteria are verifiable by GLM, DeepSeek, Qwen, MiMo, and Codex.

### 7.1 GitHub Issue/PR Imports

- [ ] A `SourceDocument` with `source_type = "github_issue"` produces at least one `Component` with `fact_type = "github_issue"`.
- [ ] A `SourceDocument` with `source_type = "github_pull_request"` produces a `github_pr` component and `changed_file` components for each modified file.
- [ ] PRs containing `fixes #N` create a deterministic `fixes` relationship to the matching issue component.
- [ ] All GitHub-derived components have `source_url` pointing to the GitHub URL.
- [ ] Tests prove deterministic relationships are created with `origin = "deterministic"` and non-empty `evidence`.

### 7.2 AI Markdown Sessions

- [ ] A `SourceDocument` with `source_type = "ai_context_codex"` produces an `ai_session` root component.
- [ ] Actionable unchecked task list items produce `Task` components with `fact_type = "ai_task"`.
- [ ] Source-backed recommendations produce `Decision` or `Risk` components.
- [ ] File references produce `Document` or `Repo` components.
- [ ] Tests prove generic narration is **not** extracted (assert count of `Document` components from a purely procedural session is ≤ 1).

### 7.3 Relationship Quality

- [ ] No relationship row has `evidence = NULL` after any agent or ingestion run.
- [ ] Deterministic relationships have `status = "active"` and `origin = "deterministic"`.
- [ ] AI-suggested relationships have `status = "proposed"` and `origin = "ai_suggested"`.
- [ ] `RelationshipAgent` persists only suggestions with `confidence >= 0.6`.
- [ ] Tests prove no hallucinated relationships are created from unrelated facts (e.g., a pricing fact and a security fact with no textual overlap must not get a `related_to` edge).

### 7.4 Display Quality

- [ ] The graph canvas explains why every visible edge exists (hover or selection reveals `evidence`).
- [ ] Low-confidence (`< 0.7`) or `proposed` relationships are visually distinct (dashed, muted, or hidden by default).
- [ ] A "Work Lens" filter exists that shows only blockers, open decisions, unresolved questions, and active tasks.
- [ ] Context packs can be generated from a selected subset of the graph.

### 7.5 Temporal State

- [ ] Components with `temporal = "future"` have `status = "proposed"`.
- [ ] Components with `temporal = "past"` have `status = "needs_review"` (or `stale` if superseded).
- [ ] The timeline endpoint includes temporal state transitions.

---

## 8. Implementation Order

### Phase 1 — Schema & Taxonomy (GLM + Qwen)
1. Add `fixes`, `resolved_by`, `conflicts_with`, `touches_file` to `VALID_RELATIONSHIP_TYPES`.
2. Add `origin` column to `Relationship` model (enum: `deterministic`, `ai_suggested`).
3. Add `evidence_excerpt` column to `Component` model (optional, 500 chars).
4. Update `app/taxonomy.py` with bidirectional aliases (`implements` ↔ `implemented_in`, `fixes` ↔ `resolved_by`).

### Phase 2 — Deterministic Extractors (GLM)
5. Create `app/processing/github_extractor.py` — deterministic GitHub issue/PR parser.
6. Create `app/processing/ai_session_extractor.py` — deterministic AI markdown session parser.
7. Update `IngestionService.process_document` to route by `source_type` to specialized extractors before generic LLM fallback.

### Phase 3 — Relationship Enforcement (Qwen)
8. Enforce non-null `evidence` in `_create_relationship` (raise or skip if missing).
9. Update `GraphBuilderAgent._infer_cross_doc_relationships` to populate `evidence` with the matching substring and set `origin = "ai_suggested"`.
10. Update `RelationshipAgent` to set `origin = "ai_suggested"` on persisted suggestions.

### Phase 4 — Display Frontend (MiMo + Codex)
11. Add `origin` and `evidence` to `RelationshipRead` schema.
12. Add edge style mapping by `status` and `origin` in `GraphView.jsx`.
13. Implement "Work Lens" CEO view filter.
14. Implement context-pack-from-selection API and UI.

### Phase 5 — Tests & Verification (Codex)
15. Add tests for GitHub deterministic extraction.
16. Add tests for AI session extraction rules (must / must-not).
17. Add tests that assert `evidence IS NOT NULL` on all relationships after build.
18. Run full test suite: `pytest -q` and `cd frontend && npm run build`.

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Schema migration for `origin` and `evidence_excerpt` breaks SQLite dev environments | Use the existing lightweight migration pattern in `app/migrations.py` (startup guard). |
| Deterministic GitHub extractor misses edge cases (e.g., "fixes #123 and #124") | Regex + parsing fallback; cap at first match, log warnings. |
| AI session extractor creates too many `Task` components from trivial checkboxes | Require actionable verb + minimum length (10 chars). |
| Non-null `evidence` breaks existing cross-doc inference | Update inference to include the matching substring as evidence before enforcement. |
| Frontend edge-style changes conflict with dark-mode styling | Maintain `isDark` check and test both themes. |
| `fixes` / `resolved_by` bidirectional aliases may confuse canonicalization | Add explicit test that `canonical_relationship_type("fixes") == "fixes"` and `"resolved_by" == "resolved_by"`. |

---

## 10. Non-Goals

- **Connector OAuth or provider sync.** Slack, Discord, Gmail, Zoom, Google Drive, and Wispr Flow connectors are explicitly out of scope. The task assumes `SourceDocument` rows already exist.
- **Embedding model training or fine-tuning.** The `embedding` column exists but its generation is unchanged.
- **Real-time graph updates via WebSocket.** Polling-based refresh is sufficient.
- **Multi-tenancy beyond `workspace_id` filtering.** Already observed in `app/api/graph.py` lines 92–106.
- **Alembic migration framework.** Continue using lightweight startup guards.

---

## 11. Evidence Files

| File | Lines | Purpose |
|------|-------|---------|
| `app/models.py` | 83–193 | Core schema |
| `app/taxonomy.py` | 5–121 | Canonical names and relationship types |
| `app/processing/extractor.py` | 35–112, 178–275 | LLM prompt and regex fallback |
| `app/services/ingest.py` | 27–157 | Ingestion, upsert, relationship creation |
| `app/api/graph.py` | 65–143, 171–198, 251–289 | Graph read, stats, timeline |
| `app/agents/context_pack.py` | 43–153 | Context pack agent |
| `app/agents/gap_detector.py` | 72–281 | Gap detector agent |
| `app/agents/relationship_agent.py` | 69–198 | Relationship agent |
| `app/agents/graph_builder.py` | 104–147 | Cross-doc inference |
| `frontend/src/pages/GraphView.jsx` | 1–1651 | Canvas, inspector, filters, agents panel |
| `frontend/src/pages/AgentsView.jsx` | 1–396 | Agent cards and results |
| `tests/test_ingestion.py` | 1–856 | Ingestion behavior suite |
| `tests/test_graph_api.py` | 1–501 | Graph API behavior suite |
| `tests/test_extraction.py` | 1–183 | Extraction behavior suite |
| `tests/test_agents.py` | 1–111 | Agent behavior suite |
| `docs/connectors-graph-contract.md` | 1–286 | Prior contract (connectors focus) |

---

## 12. Changed Files

| File | Action | Reason |
|------|--------|--------|
| `docs/knowledge-graph-contract.md` | **Created** | This document |
| `.agent-runs/kimi-task.md` | **Updated** | Final report per task requirements |

**No source code files were modified** in this contract-writing pass. Implementation is delegated to GLM, Qwen, MiMo, and Codex per Phase 1–5 above.
