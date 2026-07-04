# Context Compiler v2 Contract

Status: proposed implementation contract. This pass does not implement or
modify product code.

This document turns the v2 plan into the contract that implementation agents
must build against. It preserves the current launch baseline:

- current graph reads use `SourceDocument`, `Model`, `Component`,
  `Relationship`, and `UnresolvedRelationship`;
- `query.v1` returns facts-used and relationship traces;
- legacy `Component` rows remain readable even when no v2 `Claim` exists;
- connector status semantics do not change.

## Observed Baseline

- `SourceDocument` stores raw content, source type, external ID, author, URL,
  metadata, workspace scope, ingest time, and process time.
- The contract-time integration worktree contained unmerged additive schema
  stubs for `content_sha256`, `trust_zone`, `source_created_at`,
  `EvidenceSpan`, `Claim`, `ClaimRevision`, `ContextPack`, `ContextPackItem`,
  `AgentRun`, `RunObservation`, and repo-index tables. Treat those as
  in-progress implementation, not proof that the v2 contract is complete.
- `Component` stores the current graph fact projection with `value`,
  `fact_type`, `temporal`, `confidence`, `authority_weight`, `status`,
  `provenance`, `excerpt`, source linkage, and optional entity identity.
- `Relationship` stores typed edges with `confidence`, `evidence`, `status`,
  and `origin`.
- `UnresolvedRelationship` stores extracted relationships whose target cannot
  be resolved yet.
- `QueryService.query()` emits `schema_version = "query.v1"` and persists
  `RetrievalEvent.trace_json`.
- `ContextPackAgent` currently renders a simple markdown handoff from selected
  components plus one-hop relationships. It is not the v2 compiler.
- MCP currently exposes read/query tools only. v2 adds runtime observation tools
  but no dangerous tools.

## Evidence Ledger

### SourceDocument Contract

`SourceDocument` remains the immutable raw source ledger. v2 adds nullable
columns in an additive migration:

| Field | Type | Required for new rows | Rule |
|---|---:|---:|---|
| `content_sha256` | string(64) | yes | Lowercase hex SHA-256 of the exact UTF-8 `content`. |
| `trust_zone` | string(40) | yes | One of the trust zones in `docs/security-context-packs.md`. |
| `source_created_at` | datetime nullable | no | Provider/source creation timestamp, not ingest time. |

Immutability rules:

- After ingest, `content`, `source_type`, `external_id`, `source_url`, `author`,
  `content_sha256`, `trust_zone`, and `source_created_at` are immutable.
- `processed_at` may change from `NULL` to a timestamp during extraction.
- `metadata_json` may receive additive processing metadata only. It must not
  rewrite provider metadata or remove fields.
- Redaction must not edit `content` in place. It creates a replacement
  `SourceDocument` with metadata linking `redacts_source_document_id`, then
  marks claims from the original as `rejected` or `stale`.
- Imports that see the same `(workspace_id, source_type, external_id,
  content_sha256)` are idempotent and return the existing row.
- Imports that see the same `(workspace_id, source_type, external_id)` with a
  different hash create a new row with metadata `revision_of_external_id` unless
  the connector has an explicit provider revision ID.

### EvidenceSpan Table

Purpose: exact quote/range inside a raw `SourceDocument`.

Fields:

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `id` | UUID | yes | Primary key. |
| `workspace_id` | UUID nullable | yes | Mirrors source workspace. |
| `source_document_id` | UUID FK | yes | References immutable source. |
| `start_char` | integer nullable | no | Zero-based Python string offset. |
| `end_char` | integer nullable | no | Exclusive offset; must be `> start_char`. |
| `text` | text nullable | no | Stored only when useful for audit; must equal located text if offsets are set. |
| `text_sha256` | string(64) | yes | SHA-256 of located text or provided evidence text. |
| `evidence_type` | string(40) | yes | See valid values below. |
| `authority_weight` | float | yes | Clamped 0.0 to 1.0. |
| `trust_zone` | string(40) | yes | Copied from source unless explicitly narrowed. |
| `prompt_injection_risk_score` | float | yes | Clamped 0.0 to 1.0. |
| `extraction_method` | string(40) | yes | See valid values below. |
| `review_status` | string(40) | yes | `verified`, `needs_review`, or `rejected`. |
| `created_at` | datetime | yes | Server timestamp. |

Valid `evidence_type`:

- `source_quote`
- `deterministic_match`
- `llm_extracted_quote`
- `tool_observation`
- `command_output`
- `test_output`
- `repo_state`
- `diff_summary`
- `human_note`
- `legacy_component_excerpt`

Valid `extraction_method`:

- `deterministic`
- `llm_exact`
- `llm_fuzzy`
- `manual`
- `mcp_runtime`
- `repo_indexer`
- `legacy_backfill`

Validation:

- If `start_char` and `end_char` are set, `content[start_char:end_char]` must
  exist and `sha256(span_text) == text_sha256`.
- If only `text` is provided, the service must try exact location in
  `SourceDocument.content`.
- Exact single match: store offsets, `review_status = "verified"` unless other
  checks fail.
- Multiple exact matches: store the first deterministic match only if surrounding
  context disambiguates; otherwise store no offsets and set `needs_review`.
- Fuzzy match: store no offsets, store normalized evidence text and hash, set
  `review_status = "needs_review"`, and any downstream claim starts as
  `needs_review`.
- Empty evidence text is invalid.
- Evidence from `untrusted_external` or `hostile_test` may support claims but
  cannot become generated instructions.

Creation rules:

- Deterministic extractors must create spans from exact source ranges.
- LLM extraction must return an evidence quote. The ingestion service then
  locates that quote in the source before any active claim is created.
- If an LLM returns a claim without locatable evidence, create a span with
  `extraction_method = "llm_fuzzy"` and `review_status = "needs_review"` or skip
  the claim. It must never create an `active` claim.
- Relationship evidence uses the same span contract. A relationship may point
  through a claim revision or carry legacy text until Agent 2 adds a direct span
  FK.

Prompt-injection handling:

- `prompt_injection_risk_score` is stored on each `EvidenceSpan`.
- Scores `>= 0.70` prevent the span from being selected as instruction or plan
  text.
- Scores `>= 0.90` exclude the span from default packs unless the objective is a
  security review or prompt-injection test.
- Selected risky evidence must appear only in the evidence section as a quoted
  excerpt with a warning label.

Agent 2 required tests:

- `tests/test_evidence_ledger.py::test_source_document_hash_and_trust_zone_are_set_on_ingest`
- `tests/test_evidence_ledger.py::test_source_document_content_is_not_mutated_by_processing`
- `tests/test_evidence_ledger.py::test_exact_evidence_span_offsets_and_hash_validate`
- `tests/test_evidence_ledger.py::test_llm_fuzzy_evidence_creates_needs_review_span`
- `tests/test_evidence_ledger.py::test_unlocated_evidence_cannot_create_active_claim`
- `tests/test_evidence_ledger.py::test_prompt_injection_risk_is_stored_and_penalized`
- `tests/test_evidence_ledger.py::test_same_external_id_new_hash_creates_new_source_revision`
- `tests/test_evidence_ledger.py::test_redaction_creates_replacement_source_not_in_place_edit`

## Claim Graph

### Claim Table

Purpose: normalized project fact independent of any one graph/UI projection.

Fields:

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `id` | UUID | yes | Primary key. |
| `workspace_id` | UUID nullable | yes | Same workspace scoping as components. |
| `identity_key` | string(255) | yes | Stable key for the claim area. |
| `claim_type` | string(50) | yes | Valid values below. |
| `status` | string(40) | yes | Valid values below. |
| `temporal` | string(20) | yes | Valid values below. |
| `confidence` | float | yes | Current confidence, 0.0 to 1.0. |
| `authority_weight` | float | yes | Current authority, 0.0 to 1.0. |
| `current_revision_id` | UUID nullable | no | Points to latest accepted revision. |
| `created_at` | datetime | yes | Server timestamp. |
| `updated_at` | datetime | yes | Server timestamp. |

Valid `claim_type`:

- `decision`
- `task`
- `blocker`
- `risk`
- `requirement`
- `feature`
- `issue`
- `pull_request`
- `file_reference`
- `repo_state`
- `connector_state`
- `verification`
- `run_event`
- `metric`
- `context_note`

Valid `status`:

- `active`
- `proposed`
- `needs_review`
- `superseded`
- `rejected`
- `stale`
- `resolved`

Valid `temporal`:

- `current`
- `past`
- `future`
- `unknown`

Rules:

- One atomic claim per row.
- `identity_key` groups revisions of the same project fact area, not unrelated
  facts with similar wording.
- A claim with no verified evidence span must be `needs_review` or `proposed`.
- `active` requires at least one verified span or a legacy component explicitly
  marked as backfilled `needs_review = false`.
- Status changes happen through `ClaimRevision`; do not overwrite current value
  without revision history.

### ClaimRevision Table

Purpose: append-only history of how a claim was created, updated, superseded, or
retracted.

Fields:

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `id` | UUID | yes | Primary key. |
| `claim_id` | UUID FK | yes | Parent claim. |
| `evidence_span_id` | UUID FK | yes | Supporting evidence. |
| `value` | text | yes | Atomic claim text after this revision. |
| `operation` | string(40) | yes | Valid values below. |
| `confidence_delta` | float | yes | Signed delta applied to previous confidence. |
| `status_after` | string(40) | yes | Claim status after revision. |
| `supersedes_claim_id` | UUID nullable | no | Explicit supersession target. |
| `contradicts_claim_id` | UUID nullable | no | Explicit contradiction target. |
| `created_by` | string nullable | no | `system`, `mcp:<tool>`, or user/tool label. |
| `created_at` | datetime | yes | Server timestamp. |

Valid `operation`:

- `create`
- `confirm`
- `update`
- `contradict`
- `supersede`
- `reject`
- `resolve`
- `mark_stale`
- `verify`
- `retract`

Rules:

- Revisions are append-only.
- A revision must point to an `EvidenceSpan`.
- `contradict` requires `contradicts_claim_id`.
- `supersede` requires `supersedes_claim_id`.
- `reject`, `resolve`, `mark_stale`, and `retract` must preserve the evidence
  that justified the state change.
- `current_revision_id` points to the latest revision that defines the current
  claim value/status. Contradicting evidence may be appended without changing
  current value when it remains unresolved.

### Component Projection

`Component` remains the graph/UI projection. v2 adds:

- nullable `components.claim_id` FK to `claims.id`.

Projection rules:

- New extraction path is `SourceDocument -> EvidenceSpan -> ClaimRevision ->
  Claim -> Component`.
- Component `name`, `value`, `fact_type`, `temporal`, `confidence`,
  `authority_weight`, `status`, `provenance`, and `excerpt` are derived from the
  current claim revision and source span.
- Component `status` remains compatible with existing API behavior. `Claim`
  statuses map to components as:
  - `active` -> `active`
  - `proposed` -> `proposed`
  - `needs_review` -> `needs_review`
  - `superseded`, `rejected`, `stale`, `resolved` -> same status on component
    when projected, with stale/rejected excluded from default graph reads.
- Legacy components without `claim_id` remain readable through existing graph,
  query, stats, timeline, source-detail, and context-pack endpoints.
- Legacy backfill is opportunistic. Do not block reads or delete components
  because a claim is missing.

Contradictions, supersession, and stale claims:

- Contradictions are represented by `ClaimRevision.operation = "contradict"` and
  a graph `Relationship` of `relationship_type = "contradicts"` between the
  projected components when both claims have components.
- Supersession is represented by `ClaimRevision.operation = "supersede"`,
  `supersedes_claim_id`, component `superseded_by_id` where available, and a
  `supersedes` relationship between projections.
- Stale claims use `Claim.status = "stale"` and a `mark_stale` revision. Stale
  claims are excluded from default selection but may appear in excluded context
  with citations when they conflict with selected current context.
- Resolved blockers use `status = "resolved"` and remain available as history,
  not active blockers.

Agent 2 required tests:

- `tests/test_claim_graph.py::test_claim_revision_requires_evidence_span`
- `tests/test_claim_graph.py::test_claim_projects_to_component_with_claim_id`
- `tests/test_claim_graph.py::test_legacy_component_without_claim_remains_in_graph_and_query`
- `tests/test_claim_graph.py::test_contradiction_revision_creates_claim_link_and_graph_edge`
- `tests/test_claim_graph.py::test_supersede_revision_marks_old_claim_and_projection`
- `tests/test_claim_graph.py::test_stale_claim_is_excluded_from_default_graph_but_available_in_source_diff`
- `tests/test_claim_graph.py::test_resolved_blocker_does_not_count_as_active_blocker`
- `tests/test_graph_api.py::test_graph_provenance_supports_claim_backed_and_legacy_components`

## Context Compiler Service

The compiler is a service, not prompt-only generation.

Suggested module: `app/services/context_compiler.py`.

Primary API:

```python
async def compile_context_pack(
    session: AsyncSession,
    *,
    workspace_id: UUID | None,
    goal: str,
    repo_path: str | None,
    target_model: str,
    token_budget: int | None = None,
    branch: str | None = None,
    base_commit: str | None = None,
    idempotency_key: str | None = None,
) -> CompiledContextPack
```

Return object:

```python
@dataclass
class CompiledContextPack:
    context_pack_id: UUID
    schema_version: str
    markdown: str
    manifest: dict
    selected_items: list[ContextCandidate]
    excluded_items: list[ExcludedContextCandidate]
    health_score: float
```

Failure modes:

- `InvalidGoalError`: empty goal or goal over 2000 chars.
- `InvalidRepoPathError`: repo path is absent, unreadable, or not under the
  allowed workspace root when repo inspection is requested.
- `UnsupportedTargetModelError`: target model cannot be mapped to a capability
  profile.
- `TokenBudgetTooSmallError`: budget cannot fit mandatory sections.
- `DatabaseContractMissingError`: Agent 2 tables are unavailable when persistence
  is required. The service may still run in compatibility mode only when tests
  explicitly request it.

### parse_goal

Input:

```json
{
  "goal": "finish GitHub connector pagination and add tests",
  "workspace_id": "uuid-or-null",
  "target_model": "qwen2.5-coder-7b"
}
```

Output:

```json
{
  "objective": "finish GitHub connector pagination and add tests",
  "normalized_query": "github connector pagination tests",
  "verbs": ["finish", "add"],
  "objects": ["GitHub connector pagination", "tests"],
  "key_terms": ["github", "connector", "pagination", "tests"],
  "candidate_files": ["app/sync/github.py", "app/api/connectors.py", "tests/test_connectors.py"],
  "candidate_symbols": [],
  "constraint_terms": ["connector status", "unsupported connectors", "smoke tests"],
  "task_type": "implementation"
}
```

Rules:

- Use deterministic lexical parsing first. LLM assistance may add terms but
  cannot remove deterministic terms.
- Extract file paths with a conservative path regex and keep only repo-relative
  paths that exist or are plausible new test paths.
- Normalize provider names: `GitHub`, `github`, and `gh` map to `github`.
- Empty or purely generic goals fail.

### inspect_repo

Input:

```json
{
  "repo_path": "/absolute/path",
  "candidate_files": ["app/sync/github.py"],
  "max_changed_files": 80
}
```

Output:

```json
{
  "repo_path": "/absolute/path",
  "branch": "feature/github-pagination",
  "base_commit": "abc123",
  "head_commit": "def456",
  "dirty": true,
  "changed_files": [
    {"path": "app/sync/github.py", "status": "M", "sha256": "hex-or-null"}
  ],
  "untracked_files": [],
  "relevant_files": [
    {"path": "app/sync/github.py", "reason": "goal_term:github"},
    {"path": "tests/test_connectors.py", "reason": "test_for:app/sync/github.py"}
  ],
  "test_files": ["tests/test_connectors.py"],
  "manifest_files": ["pyproject.toml", "frontend/package.json"],
  "env_files": [".env.example"],
  "last_indexed_at": "iso-or-null"
}
```

Rules:

- Use read-only git commands and filesystem inspection.
- Do not run tests, install dependencies, edit files, or call providers.
- If git is unavailable, return `branch = null`, `head_commit = null`, and
  `dirty = null`; do not fail unless repo inspection was required by caller.
- Hash file contents with SHA-256 when files are selected as context.

### infer_task_frame

Input: `GoalFrame`, `RepoFrame`, current graph models and source metadata.

Output:

```json
{
  "task_type": "implementation",
  "domains": ["connectors", "github", "tests"],
  "files": ["app/sync/github.py", "app/api/connectors.py", "tests/test_connectors.py"],
  "symbols": ["sync_github", "GitHubClient"],
  "verification_commands": ["python3 -m pytest tests/test_connectors.py -q"],
  "non_negotiables": [
    "Do not change connector status semantics.",
    "Do not create connected state for unsupported connectors.",
    "Do not ignore failed smoke tests."
  ]
}
```

Rules:

- Verification commands are suggestions in the pack, not executed by the
  compiler.
- Include project non-negotiables from `TASK_PLAN.md`, connector docs, and
  source-backed decisions.
- Do not infer unsupported connector behavior as available.

### Candidate Retrieval Sources

The compiler retrieves candidates from:

1. Exact file/path mentions in claims, components, source metadata, and repo
   index records.
2. `query.v1` compatible lexical and vector retrieval using the goal frame.
3. Claim graph: active claims matching terms, files, domains, entities, and
   recent decisions.
4. Legacy components: active and needs-review components matching the goal.
5. Relationships: selected candidate neighbors by conservative graph expansion.
6. Open blockers, risks, unresolved relationships, and recent failed
   verification observations.
7. Recent agent runs and patch summaries for the same repo branch/files.
8. Repo intelligence: files, symbols, routes, manifests, config/env files, and
   tests.
9. Connector contracts and launch docs when the goal touches connectors.

Candidate shape:

```json
{
  "id": "stable-string",
  "item_type": "claim|component|relationship|source|repo_file|repo_symbol|verification|decision|blocker|run_observation",
  "title": "short title",
  "summary": "compact current-state text",
  "value": "full value if needed",
  "claim_id": "uuid-or-null",
  "component_id": "uuid-or-null",
  "evidence_span_id": "uuid-or-null",
  "source_document_id": "uuid-or-null",
  "file_path": "repo/relative/path-or-null",
  "symbol_name": "name-or-null",
  "status": "active",
  "temporal": "current",
  "trust_zone": "trusted_repo",
  "confidence": 0.91,
  "authority_weight": 0.8,
  "prompt_injection_risk_score": 0.0,
  "created_at": "iso-or-null",
  "source_created_at": "iso-or-null"
}
```

### Graph Expansion Rules

- Expand up to two hops from high-scoring claims/components.
- Always include direct `blocks`, `blocked_by`, `depends_on`, `contradicts`,
  `supersedes`, `fixes`, `resolved_by`, `implements`, `implemented_in`, and
  `touches_file` edges touching selected files or claims.
- Include `related_to` and `mentions` only for one hop, only when confidence is
  `>= 0.75`, and only if the target also matches goal terms or selected files.
- Exclude `rejected` relationships.
- Keep unresolved relationships as risks or excluded items, never as resolved
  dependencies.

### Conflict And Staleness Resolution

- If active claims contradict each other, include both in `risks` and mark
  selected items with `conflict_state = "unresolved"`.
- If an active claim supersedes another claim, select only the active/current
  claim and put the old claim in `excluded_context` with reason `superseded`.
- If a claim/component is `stale`, include it only in `excluded_context` unless
  it explains a contradiction or the goal asks for history.
- If evidence trust is lower than selected generated instructions, keep it in
  evidence only.
- Human-verified and trusted-repo evidence outrank LLM-only or untrusted
  external evidence.

### Scoring

The first implementation must use these exact weights:

```text
score =
  0.24 * goal_similarity
+ 0.18 * code_relevance
+ 0.14 * graph_centrality
+ 0.12 * confidence
+ 0.10 * authority_weight
+ 0.08 * recency
+ 0.08 * task_or_blocker_priority
+ 0.06 * human_verified_bonus
- 0.20 * stale_penalty
- 0.25 * contradiction_unresolved_penalty
- 0.15 * prompt_injection_risk_penalty
```

All feature values are clamped 0.0 to 1.0. The final score is clamped 0.0 to
1.0 after penalties.

Minimum feature definitions:

- `goal_similarity`: lexical/token overlap plus vector score where available.
- `code_relevance`: exact file path, symbol, route, config, or test match.
- `graph_centrality`: normalized count of non-rejected high-value edges.
- `confidence`: stored claim/component confidence.
- `authority_weight`: stored authority.
- `recency`: 1.0 for source created in last 7 days, linearly decays to 0.0 at
  180 days; unknown recency is 0.3.
- `task_or_blocker_priority`: blocker/risk/task/verification relevance.
- `human_verified_bonus`: 1.0 only for human-verified claim/evidence.
- `stale_penalty`: 1.0 for `stale`, 0.5 for `past` temporal unless history is
  requested.
- `contradiction_unresolved_penalty`: 1.0 when unresolved contradiction exists.
- `prompt_injection_risk_penalty`: stored risk score.

### Budgeted Diverse Selection

Selection constraints:

- Fit within target pack token budget.
- Include mandatory sections, repo state, objective, verification commands, and
  stop conditions before optional evidence.
- Include at least one current-state or objective summary when available.
- Include relevant files/symbols for implementation tasks.
- Include all active blockers above score `0.70`.
- Include unresolved contradictions touching selected files.
- Include direct decisions touching selected files.
- Include verification commands when known.
- Deduplicate by `claim_id`, `identity_key`, or file path.
- Prefer diversity across decision, blocker, file, verification, and prior-run
  categories over repeating the same source.
- Keep untrusted content out of plan/instruction sections.

Deterministic token estimation:

- Normalize CRLF to LF.
- Count markdown tokens as `ceil(len(text) / 4)` after collapsing runs of more
  than two blank lines.
- Count JSON manifest tokens as `ceil(len(json.dumps(manifest, sort_keys=True)) / 4)`.
- Store `token_cost` per selected item.

### Persisted Context Pack Records

Agent 2 owns schema; Agent 3 consumes it.

`ContextPack` fields:

- `id`
- `workspace_id`
- `objective`
- `target_model`
- `model_profile`
- `token_budget`
- `pack_version` default `context_pack.v2`
- `health_score`
- `markdown`
- `manifest`
- `repo_state_json`
- `idempotency_key`
- `created_at`

`ContextPackItem` fields:

- `id`
- `context_pack_id`
- `item_type`
- `claim_id`
- `component_id`
- `evidence_span_id`
- `source_document_id`
- `score`
- `inclusion_reason`
- `token_cost`
- `created_at`

Idempotency:

- If `(workspace_id, objective, target_model, repo_head_commit,
  token_budget, idempotency_key)` matches an existing pack, return the existing
  pack.
- Without idempotency key, always create a new pack because repo/context state
  may have changed.

## ModelCapabilityProfile

Profiles live in `app/services/model_profiles.py`.

Required profile:

```json
{
  "name": "small_coder_model",
  "max_pack_tokens": 12000,
  "needs_explicit_file_paths": true,
  "needs_stepwise_plan": true,
  "max_open_questions": 3,
  "include_verification_commands": true,
  "include_raw_excerpts": "short",
  "avoid_long_narrative": true,
  "format": "strict_markdown",
  "max_evidence_quote_chars": 600,
  "max_selected_items": 24
}
```

Behavior:

- Small models get rigid markdown order, explicit file paths, narrow plan
  steps, concrete commands, and stop conditions.
- Open questions are capped at three. Excess uncertainty becomes stop
  conditions or excluded context.
- Evidence excerpts are short and cited. Long raw source dumps are forbidden.
- Do not claim small models become frontier models. The contract claim is that
  compiled context narrows avoidable context gaps.

## Repo Intelligence

Agent 3 owns first implementation.

Tables proposed by Agent 2:

- `code_files`: workspace, repo root, path, language, sha256, last commit, size.
- `code_symbols`: file, type, name, qualified name, lines, docstring,
  signature.
- `code_edges`: source symbol, target symbol, edge type.
- `repo_events`: commit, branch, author, message, changed files.

First implementation:

- Python: parse with `ast` for classes, functions, imports, routes, and tests.
- TypeScript/JavaScript: lightweight regex/parser for exports, imports, route
  declarations, React components, and tests.
- Manifests: `pyproject.toml`, `package.json`, compose files, env examples.
- Do not overbuild static analysis. Useful file/symbol hints matter more than
  perfect call graphs.

Agent 3 required tests:

- `tests/test_repo_indexer.py::test_indexes_python_files_symbols_and_import_edges`
- `tests/test_repo_indexer.py::test_indexes_typescript_exports_routes_and_tests`
- `tests/test_repo_indexer.py::test_repo_indexer_records_sha256_and_changed_files`
- `tests/test_context_compiler.py::test_parse_goal_extracts_github_connector_files_and_constraints`
- `tests/test_context_compiler.py::test_compile_pack_persists_manifest_markdown_and_items`
- `tests/test_context_compiler.py::test_scoring_uses_exact_weights_and_penalties`
- `tests/test_context_compiler.py::test_budgeted_selection_keeps_required_sections_under_budget`
- `tests/test_context_compiler.py::test_stale_and_contradictory_items_move_to_excluded_context`
- `tests/test_context_compiler.py::test_small_coder_profile_outputs_paths_steps_commands_and_stop_conditions`
- `tests/test_cli.py::test_cli_prepare_calls_context_prepare_endpoint`

## Merge Matrix

| Agent | Files owned | Must not own | Notes |
|---|---|---|---|
| Agent 1 | `docs/context-compiler-v2.md`, `docs/context-pack-v2.md`, `docs/security-context-packs.md`, contract sections in `docs/mcp.md`, `.agent-runs/agent-1-task.md` | code, migrations, frontend | Contract lands first. |
| Agent 2 | `app/models.py`, `app/migrations.py`, `app/alembic/versions/*`, `app/services/ingest.py`, `app/processing/extractor.py`, `app/processing/source_extractors.py`, `app/taxonomy.py`, evidence/claim tests | compiler, MCP tools, frontend | Owns additive schema and extraction grounding. |
| Agent 3 | `app/services/context_compiler.py`, `app/services/model_profiles.py`, `app/services/repo_indexer.py`, `app/agents/context_pack.py`, context API route, `app/cli/main.py`, compiler/repo/CLI tests | migrations, MCP write tools, connector semantics | Uses Agent 2 tables, preserves legacy pack endpoint. |
| Agent 4 | `app/mcp/server.py`, MCP examples, `app/evals/context_compiler/**`, `docs/mcp.md` runtime usage, `docs/oss-readiness.md`, MCP/eval tests | migrations, core compiler internals, connector OAuth | Calls Agent 3 service; adds eval proof. |
| Codex | integration review, conflict resolution, final smoke | n/a | Merges and verifies in order. |

Known conflict files:

- `docs/mcp.md`: Agent 1 writes contract; Agent 4 later adds runtime usage.
- `app/agents/context_pack.py`: current v1 pack generator; Agent 3 may adapt or
  wrap it. Agent 4 must not duplicate compiler logic here.
- `app/cli/main.py`: Agent 3 owns `ctxe prepare`; Agent 4 should not edit.
- `app/models.py`: Agent 2 owns all v2 schema changes.
- `tests/test_cli.py`: Agent 3 owns prepare CLI tests; Codex resolves overlap.

Required integration order:

1. Agent 1 contract docs.
2. Agent 2 schema, migrations, evidence spans, claims, projections.
3. Agent 3 compiler, repo indexer, API, CLI.
4. Agent 4 MCP bridge, evals, docs updates.
5. Codex final review, conflict resolution, focused tests, full smoke.

Stop condition: if an implementation branch needs to change connector status
semantics or make unsupported connectors appear connected, stop and escalate to
Codex instead of coding around the contract.
