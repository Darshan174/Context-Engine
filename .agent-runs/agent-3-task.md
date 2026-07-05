# Agent 3 Task - Context Compiler, Repo Intelligence, Health Engine

## Role

You are Agent 3 working in `/Users/darshann/Desktop/context-engine`.

You are the graph reasoning, schema/API consistency, and hard-bug solver for
the v2 compiler layer. Your task is to build the service that compiles a goal
into a model-specific context pack using graph evidence and repo state.

## Branch

`agent/3-context-compiler-repo-index`

## Read First

Read:

- `AGENTS.md`
- `TASK_PLAN.md`
- `.agent-runs/agent-3-task.md`
- Agent 1's contract docs if present
- `app/models.py`
- `app/services/query.py`
- `app/services/reranker.py`
- `app/services/vector_search.py`
- `app/agents/context_pack.py`
- `app/api/query.py`
- `app/api/graph.py`
- `app/api/repo.py`
- `app/cli/main.py`
- `tests/test_cli.py`
- `tests/test_graph_api.py`
- `tests/test_adversarial_graph.py`

If Agent 2's migration branch is not present, code against interfaces documented in
`TASK_PLAN.md` and isolate compatibility assumptions.

## Mission

Implement:

- `ContextCompiler` service.
- `ModelCapabilityProfile`.
- Context Pack v2 renderer and manifest builder.
- Minimal repo indexer.
- Context health, conflict, and staleness scoring.
- `ctxe prepare`.
- `POST /api/context/prepare`.

## Codex Review Follow-Up - Must Fix Before Done

The current v2 working tree passed tests but still had persistence and manifest
contract gaps. Your implementation is not done until these are fixed:

- `POST /api/context/prepare` must commit the `ContextPack` and
  `ContextPackItem` rows for the pack ID it returns. A response-only flush is
  insufficient.
- `ctxe prepare` must either:
  - persist a `ContextPack` and `ContextPackItem` rows through the configured
    database when persistence is available; or
  - be explicitly documented and tested as file-output-only. Do not silently
    return `pack_id = null` while the product contract says packs are persisted.
- The compiler must persist the final manifest and final markdown after adding
  pack ID and persistence metadata. Stored rows must match returned payloads.
- The manifest emitted by the compiler must align with Agent 1's final
  `docs/context-pack-v2.md` contract. Do not leave a split between documented
  keys and implementation keys.
- Add tests that would have caught the review findings:
  - API prepare returns a pack ID that is readable from a fresh session;
  - stored manifest equals the returned final manifest;
  - stored markdown equals the returned final markdown;
  - CLI prepare either persists and can be queried back, or proves/documented
    file-output-only mode;
  - selected `ContextPackItem` rows are created for selected context.

## Expanded Compiler Workload

This is the largest missing slice. Build the compiler product surface end to end
inside your owned files, while consuming Agent 1 contracts and Agent 2 schema.

### A. Core Service

Implement `app/services/context_compiler.py` with:

- `ContextCompiler`;
- `compile_context_pack`;
- `parse_goal`;
- `inspect_repo`;
- `infer_task_frame`;
- candidate collection;
- scoring;
- budgeted selection;
- context health;
- manifest builder;
- persistence writer.

Required behavior:

- accepts an optional `AsyncSession`;
- refuses empty objectives;
- handles missing repo path with a clear error;
- supports compatibility mode only when explicitly requested or documented;
- returns markdown, manifest, pack ID, health score, selected items, and excluded
  items in a typed result object.

### B. Model Profiles

Implement `app/services/model_profiles.py` with:

- `small_coder_model`;
- `general_coder_model`;
- `frontier_coder_model`;
- target-model name mapping for common small coder model names;
- max open questions and excerpt limits;
- strict markdown requirements for small models.

### C. Repo Indexer

Implement `app/services/repo_indexer.py` with:

- Python `ast` symbols;
- TypeScript/JavaScript lightweight import/function/component detection;
- route/API hints;
- package manifests;
- test files;
- config/env files;
- recent git commit metadata when available;
- safe behavior outside a git repo.

Persist repo index rows only through Agent 2's existing tables. Do not modify
migrations. If persistence columns are missing, return an in-memory repo frame
and mark persistence unavailable.

### D. API Surface

Implement `POST /api/context/prepare` in an owned route file and register it in
`app/api/router.py`.

Required behavior:

- uses the request-scoped database session;
- persists pack and items;
- commits before returning success;
- returns a durable pack ID;
- returns a structured error if persistence fails;
- includes final markdown and final manifest.

Add a test that reads the returned pack from a fresh session or fresh connection
after the HTTP response.

### E. CLI Surface

Implement `ctxe prepare` and `ctxe repo index`.

Required behavior:

- writes markdown to `--out`;
- writes manifest to `--manifest-out` when provided;
- supports `--json`;
- uses the same compiler service as API;
- either persists via configured database or marks file-output-only mode
  explicitly in the manifest;
- never silently claims persistence when no durable row exists.

### F. Final Manifest And Markdown Consistency

The persisted and returned outputs must match:

- `ContextPack.manifest` JSON equals returned manifest;
- `ContextPack.markdown` equals returned markdown;
- `ContextPackItem` rows match returned selected items by score, inclusion
  reason, token cost, and references.

Use deterministic token estimation and deterministic ordering so repeated tests
are stable.

### G. Non-Conflict Boundaries

- Do not edit migrations or model columns.
- Do not edit MCP server code.
- Do not edit connector behavior.
- Do not edit frontend files.
- Do not change README/product copy except CLI help text if necessary.

## Files You Own

Primary:

- new `app/services/context_compiler.py`
- new `app/services/model_profiles.py`
- new `app/services/repo_indexer.py`
- `app/agents/context_pack.py`
- new `app/api/context.py` or equivalent
- `app/api/router.py` only for route registration
- `app/cli/main.py`
- `tests/test_context_compiler.py`
- `tests/test_repo_indexer.py`
- `tests/test_cli.py`

Allowed if needed:

- `app/services/query.py` only for reusable retrieval helpers.
- `app/api/repo.py` only if current repo API already provides useful hooks.

Do not edit:

- migrations except to consume Agent 2's models;
- MCP server implementation;
- connector code;
- frontend files;
- README positioning.

## Required Implementation

### 1. ModelCapabilityProfile

Implement profiles:

- `small_coder_model`
- `general_coder_model`
- `frontier_coder_model`

`small_coder_model` must enforce:

- explicit file paths;
- stepwise plan;
- maximum 3 open questions;
- verification commands;
- short raw excerpts;
- strict markdown format;
- no long narrative;
- stop conditions.

### 2. Goal And Repo Frames

Implement:

- `parse_goal(goal: str)`
- `inspect_repo(repo_path: str)`
- `infer_task_frame(goal_frame, repo_frame)`

Repo frame should include:

- branch;
- base commit;
- dirty state;
- changed files;
- package manifests;
- likely test commands;
- relevant symbols/files when detected.

Do not require perfect static analysis.

### 3. Repo Indexer

Add `ctxe repo index .` support if practical, but `ctxe prepare --repo .` must
be useful even without a prior index.

Index:

- Python imports/classes/functions using `ast`;
- TypeScript/JS imports/functions/components using lightweight parsing;
- package manifests;
- test files;
- routes/API endpoint hints;
- config/env files;
- recent commits if available.

Store results using Agent 2's repo tables when present. If not present, return an
in-memory repo frame and document the limitation.

### 4. Candidate Retrieval

Use existing query/retrieval primitives where possible.

Candidate sources:

- embedding retrieval;
- lexical retrieval;
- file/path/symbol matches;
- active tasks;
- blockers and risks;
- recent agent runs;
- related decisions;
- relationships within two hops;
- conflicting or superseding claims touching selected files.

### 5. Conflict, Staleness, And Readiness

Implement deterministic checks for:

- active blocker count;
- unresolved conflict count;
- stale high-authority claim count;
- missing verification commands;
- low-confidence core claim count;
- file paths that no longer exist;
- old decisions superseded by newer decisions.

Readiness score:

```text
100
- unresolved_blockers * 20
- unresolved_conflicts * 25
- stale_high_authority_claims * 15
- missing_verification * 10
- low_confidence_core_claims * 10
```

Clamp to `0..100`.

### 6. Scoring And Selection

Implement scoring:

```text
0.24 goal_similarity
0.18 code_relevance
0.14 graph_centrality
0.12 confidence
0.10 authority_weight
0.08 recency
0.08 task_or_blocker_priority
0.06 human_verified_bonus
-0.20 stale_penalty
-0.25 contradiction_unresolved_penalty
-0.15 prompt_injection_risk_penalty
```

Selection must:

- respect `token_budget`;
- include active blockers above threshold;
- include direct decisions touching selected files;
- include unresolved conflicts touching selected files;
- include verification commands if known;
- diversify by entity/identity key;
- exclude ungrounded low-confidence claims unless explicitly needed and marked.

### 7. Context Pack v2 Output

Render:

- markdown;
- manifest JSON;
- `ContextPack` row;
- `ContextPackItem` rows for selected items.

Manifest must include:

- `schema_version = context_pack.v2`;
- durable pack identifier using Agent 1's final key name;
- creation timestamp using Agent 1's final key name;
- objective;
- target model;
- repo state;
- selected context;
- excluded context;
- risks;
- verification commands and acceptance criteria.
- rendering metadata if required by Agent 1:
  - markdown SHA-256;
  - deterministic token estimate;
  - token estimation method.

Markdown must be rigid for small models:

- objective;
- current repo state;
- relevant files;
- non-negotiable decisions;
- known blockers;
- implementation plan;
- verification commands;
- evidence citations;
- stop conditions.

Persistence rules:

- Build the final manifest before writing it, or update the persisted
  `ContextPack` row after adding generated IDs and persistence metadata.
- Persisted `ContextPack.manifest` must JSON-round-trip to the same value
  returned from API/MCP/CLI.
- Persisted `ContextPack.markdown` must equal the returned markdown exactly.
- Create `ContextPackItem` rows for selected items and include score, inclusion
  reason, token cost, and any available component/evidence references.

### 8. CLI And API

Implement:

```bash
ctxe prepare "finish GitHub connector pagination and add tests" \
  --repo . \
  --target-model qwen2.5-coder-7b \
  --budget 12000 \
  --out AGENT_CONTEXT.md
```

Also implement:

- `POST /api/context/prepare`

API should return the same manifest plus markdown and persisted pack ID.

API persistence requirements:

- Commit the database transaction before returning success.
- Return an error rather than a fake persisted pack ID if persistence fails.
- Add a test that opens a fresh session after the request and reads the pack.

CLI persistence requirements:

- Prefer using the same compiler persistence path as the API.
- If the CLI intentionally supports no-database local output, expose that as an
  explicit mode or manifest `persistence.available = false` reason and cover it
  with tests and docs.

## Tests To Add

Add tests for:

- model profile selection;
- small-model rigid markdown;
- manifest schema;
- token-budget exclusion;
- stale/conflict exclusion;
- prompt-injection risk penalty;
- active blocker forced inclusion;
- relevant file detection from goal text;
- Python repo symbol indexing;
- TypeScript file indexing smoke;
- CLI writes markdown output;
- API returns `context_pack.v2`.
- API commits the returned pack and items durably.
- stored manifest/markdown match the returned final payload.
- CLI persistence behavior is tested and matches the documented mode.

## Verification

Run:

```bash
pytest -q tests/test_context_compiler.py tests/test_repo_indexer.py tests/test_cli.py
pytest -q tests/test_graph_api.py tests/test_adversarial_graph.py
```

Run full backend tests if shared query or CLI behavior changes:

```bash
pytest -q
```

## Final Report

Your final report must include:

- changed files;
- compiler algorithm implemented;
- manifest example;
- persistence behavior for API and CLI;
- tests run and exact results;
- any compatibility assumptions made because Agent 2 schema was unavailable;
- risks and remaining gaps for Agent 4 and Codex.

## Stop Conditions

Stop and report if:

- compiler output would need to treat untrusted evidence as instructions;
- schema assumptions are too uncertain to persist packs safely;
- CLI changes would break existing commands;
- `ctxe prepare` cannot produce a deterministic result on a small fixture.
- API prepare cannot commit the returned pack and item rows.
- stored and returned manifests cannot be made identical under the current
  schema.
