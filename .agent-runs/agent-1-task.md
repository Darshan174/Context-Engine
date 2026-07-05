# Agent 1 Task - Context Compiler v2 Contract

## Role

You are Agent 1 working in `/Users/darshann/Desktop/context-engine`.

Your job is contract writing, ambiguity removal, merge planning, and acceptance
criteria for Context Compiler v2. Do not implement the backend, MCP tools, repo
indexer, or frontend. Codex is the integration owner.

## Branch

`agent/1-context-compiler-v2-contract`

## Read First

Read:

- `AGENTS.md`
- `TASK_PLAN.md`
- `README.md`
- `docs/architecture.md`
- `docs/mcp.md`
- `docs/ai-context.md`
- `docs/knowledge-graph-contract.md`
- `docs/connectors.md`
- `app/models.py`
- `app/services/query.py`
- `app/agents/context_pack.py`
- `app/mcp/server.py`
- `tests/test_ingestion.py`
- `tests/test_graph_api.py`
- `tests/test_cli.py`

Treat prior reports as leads, not proof. Verify current files.

## Mission

Create the precise implementation contract for:

- Evidence Ledger.
- Claim Graph.
- Context Pack v2 markdown and manifest.
- Context Compiler service.
- ModelCapabilityProfile behavior for small coder models.
- MCP agent runtime bridge.
- Repo intelligence.
- Trust zones and prompt-injection handling.
- Context compiler evals.

## Codex Review Follow-Up

Before this task can be considered done, reconcile the review findings from the
current v2 working tree:

- Decide and document the single source of truth for the `context_pack.v2`
  manifest. Prefer the stricter `docs/context-pack-v2.md` contract unless there
  is a concrete implementation reason to relax it.
- The manifest contract must explicitly settle these fields:
  - `context_pack_id` versus `pack_id`;
  - `created_at` versus `generated_at`;
  - `rendering.markdown_sha256`, `rendering.estimated_tokens`, and
    `rendering.estimation_method`;
  - selected item `item_type`/`type`, `component_id`, `claim_id`,
    `evidence_span_id`, `source_document_id`, and citation shape.
- Add acceptance criteria that `POST /api/context/prepare` commits the
  `ContextPack` and `ContextPackItem` rows it reports.
- Add acceptance criteria that `ctxe prepare` either persists packs/items through
  the configured database or is explicitly documented and tested as a
  file-output-only compatibility mode. Do not leave this ambiguous.
- Add acceptance criteria that the persisted `ContextPack.markdown` and
  `ContextPack.manifest` match the final response after pack identifiers and
  persistence metadata are added.
- Make the merge plan assign these follow-ups clearly:
  - Agent 2 validates runtime table capacity and migration tests.
  - Agent 3 fixes compiler, API, CLI, and persistence tests.
  - Agent 4 updates MCP/docs/evals to the final manifest contract.

## Expanded Workload

In addition to the original contract work, complete these higher-bar planning
items so implementation agents do not invent incompatible shapes:

### A. Final Manifest Schema

Produce a final `context_pack.v2` JSON schema with:

- required top-level fields;
- exact field names for pack ID and timestamps;
- `rendering` metadata fields;
- selected and excluded item schemas;
- citation schema;
- repo-state schema;
- verification command schema;
- persistence metadata schema;
- error/fallback schema for non-persistent compatibility mode.

### B. API/CLI/MCP Equivalence Matrix

Document a matrix that says, for each surface, what must be identical:

- `POST /api/context/prepare`;
- `ctxe prepare`;
- MCP `prepare_task`;
- persisted `ContextPack`;
- persisted `ContextPackItem`.

The matrix must state whether each surface returns/stores:

- markdown;
- manifest;
- durable pack ID;
- context-pack item audit rows;
- health score;
- selected context citations;
- excluded context reasons.

### C. State And Status Contract

Define allowed values and mappings for:

- `Claim.status`;
- `Component.status`;
- `EvidenceSpan.review_status`;
- `ContextPack.pack_version`;
- `AgentRun.status`;
- MCP verification verdicts.

Include a specific rule for resolved blockers so Agent 3 and Agent 4 do not
count resolved work as active blockers.

### D. Test Acceptance Matrix

Create a table of required tests by owner:

- Agent 2 schema/ORM/evidence tests;
- Agent 3 compiler/API/CLI tests;
- Agent 4 MCP/eval/docs tests;
- Codex final integration tests.

Each row must include the file, test name, behavior asserted, and failure mode it
prevents.

### E. Non-Conflict Output

Keep all of this in owned docs and task files. Do not patch app source code,
migrations, tests, CLI, MCP, or frontend.

## Files You Own

Primary:

- `docs/context-compiler-v2.md`
- `docs/context-pack-v2.md`
- `docs/security-context-packs.md`
- relevant contract sections in `docs/mcp.md`
- `.agent-runs/agent-1-task.md`

Allowed if needed:

- `docs/architecture.md` for a short v2 architecture note.
- `docs/oss-readiness.md` for a "not implemented yet" entry.

Do not edit:

- `app/models.py`
- migrations
- `app/services/context_compiler.py`
- `app/mcp/server.py`
- frontend files
- connector code

## Required Contract Detail

### 1. Evidence Ledger Contract

Specify:

- `SourceDocument` immutability rules.
- `content_sha256`, `trust_zone`, and `source_created_at` behavior.
- `EvidenceSpan` fields and validation rules.
- How spans are created from deterministic extraction versus LLM extraction.
- What happens when a span cannot be located exactly.
- How prompt-injection risk is stored and used.

Acceptance criteria must include exact tests Agent 2 should add.

### 2. Claim Graph Contract

Specify:

- `Claim` fields.
- `ClaimRevision` fields.
- Valid `claim_type`, `status`, `temporal`, and `operation` values.
- How `Claim` projects to `Component`.
- How legacy `Component` rows without claims remain readable.
- How contradictions, supersession, and stale claims are represented.

Acceptance criteria must include graph/provenance compatibility checks.

### 3. Context Pack v2 Contract

Specify:

- Manifest JSON schema.
- Markdown section order for `small_coder_model`.
- Required citation shape.
- Selected and excluded context item format.
- Repo state fields.
- Verification command and acceptance criteria format.
- Stop-condition format.
- How untrusted evidence is quoted.
- Final persistence invariants:
  - returned pack ID must identify a durable `ContextPack` row;
  - stored manifest must match the returned final manifest;
  - stored markdown must match the returned final markdown;
  - selected items must persist score, inclusion reason, token cost, and any
    available component/claim/evidence references.

Include a complete golden example for:

```text
finish GitHub connector pagination and add tests
```

Use the attached constraints:

- do not change connector status semantics;
- do not create connected state for unsupported connectors;
- do not ignore failed smoke tests;
- for small models, include rigid file paths, plan, commands, and stop
  conditions.

### 4. Context Compiler Contract

Specify:

- `parse_goal`
- `inspect_repo`
- `infer_task_frame`
- candidate retrieval sources;
- graph expansion rules;
- conflict/staleness resolution;
- scoring weights;
- budgeted diverse selection;
- deterministic token estimation;
- persisted context-pack records.

Do not hand-wave. Provide exact inputs, outputs, and failure modes.

### 5. MCP Contract

Specify tools:

- `prepare_task`
- `record_agent_run_start`
- `record_agent_event`
- `record_decision`
- `record_blocker`
- `record_patch_summary`
- `verify_context_item`
- `close_task`

For each tool, specify:

- input schema;
- output schema;
- source-document side effect;
- claim/component side effect;
- trust zone;
- error cases;
- idempotency expectations.

State clearly that v2 adds no dangerous tools: no code edits, no shell commands,
no git pushes, no provider writes.

### 6. Merge Plan

Produce a merge matrix:

- Agent 2 files and migration ownership.
- Agent 3 files and compiler ownership.
- Agent 4 files and MCP/eval/docs ownership.
- Known conflict files.
- Required order for Codex integration.
- Required post-merge checks for the review follow-ups:
  - API persistence round trip in a fresh session;
  - CLI persistence or explicitly documented no-persistence mode;
  - stored manifest/markdown consistency;
  - MCP `prepare_task` returning the same contract as HTTP prepare.

## Verification

Run markdown/staleness searches only. Do not run the full test suite unless you
change code, which you should not.

Suggested checks:

```bash
rg -n "RAG|enterprise search|connected state|unsupported|context_pack.v2|EvidenceSpan|ClaimRevision" README.md docs TASK_PLAN.md .agent-runs
```

## Final Report

Your final report must include:

- changed files;
- observed current behavior with file citations;
- implemented contract docs;
- proposed but unimplemented items;
- exact acceptance criteria for Agents 2, 3, 4, and Codex;
- risks and remaining gaps.
- explicit status of the persistence/manifest review follow-ups: implemented,
  proposed, or still blocked.

## Stop Conditions

Stop and report if:

- current code contradicts `TASK_PLAN.md` in a way that changes the v2 contract;
- a required doc path conflicts with unmerged user edits you cannot reconcile;
- implementation agents would need to edit the same high-risk file without a
  merge rule.

## Agent 1 Completion Note

Status: contract docs updated; product code intentionally untouched.

Observed current checkout:

- `app/services/context_compiler.py`, `app/api/context.py`, router registration
  for `/api/context/prepare`, and `ctxe prepare` are present as in-progress
  Agent 3 implementation files in this working tree.
- `app/mcp/server.py` registers `prepare_task` import-safely and calls the
  compiler service when present.
- `app/models.py` includes v2 runtime tables, and current `ContextPackItem`
  exposes the final audit fields `item_type`, `claim_id`, `source_document_id`,
  and `created_at`; Agent 2 still owns migration/ORM validation for those
  fields.
- The in-progress compiler still diverges from this final contract: manifest
  health is nested under `context_health`, excluded items use singular
  `citation`, persistence metadata is not the final shape, file-output mode has
  no final `errors` array, and the compiler does not yet populate every
  available selected-item row reference.

Contract outputs written:

- `docs/context-pack-v2.md` is now the single source of truth for the final
  manifest schema, field names, citation shape, persistence metadata, and
  file-output compatibility mode.
- `docs/context-compiler-v2.md` now includes persistence invariants,
  API/CLI/MCP equivalence, status mappings, resolved-blocker behavior, test
  acceptance matrix, and merge follow-up ownership.
- `docs/mcp.md` now points MCP `prepare_task` at the final manifest contract
  and settles `goal` as the input key.

Review follow-up status:

- Manifest naming (`context_pack_id`, `created_at`, `item_type`) is proposed
  and contract-complete; current Agent 3 code is partially aligned but not final.
- Rendering metadata and persistence metadata are proposed and
  contract-complete; current Agent 3 code needs persistence metadata updates.
- API prepare durable commit behavior is partially implemented and still needs
  final manifest/item-row consistency tests.
- CLI prepare persistence/file-output behavior is partially implemented and
  still needs final manifest/error-shape consistency tests.
- Stored/returned manifest and markdown consistency is proposed and assigned to
  Agent 3 and Agent 4 tests.
- Runtime table capacity validation is partially implemented in models and
  remains assigned to Agent 2 for migration/ORM tests.
