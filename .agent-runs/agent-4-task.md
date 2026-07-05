# Agent 4 Task - MCP Bridge, Evals, Docs, OSS Review

## Role

You are Agent 4 working in
`/Users/darshann/Desktop/context-engine`.

You are the long-context repo reviewer, docs/UX/OSS readiness reviewer, and MCP
runtime bridge implementer for Context Compiler v2. Your work must stay honest:
no unsupported connector claims, no unverified benchmark claims, no vague
product copy.

## Branch

`agent/4-mcp-evals-oss-readiness`

## Read First

Read:

- `AGENTS.md`
- `TASK_PLAN.md`
- `.agent-runs/agent-4-task.md`
- Agent 1 contract docs if present
- `README.md`
- `docs/architecture.md`
- `docs/mcp.md`
- `docs/ai-context.md`
- `docs/connectors.md`
- `docs/oss-readiness.md`
- `app/mcp/server.py`
- `app/services/query.py`
- `app/agents/context_pack.py`
- Agent 3's compiler service if present
- Agent 2's models/migrations if present
- `tests/`

Do not trust prior reports without checking files.

## Mission

Implement or prepare the agent-facing runtime bridge and proof layer:

- MCP `prepare_task`.
- MCP run-observation write tools.
- Context compiler eval fixtures and metrics.
- Docs that explain v2 without overclaiming.
- OSS readiness review after Agent 2 and Agent 3 changes are available.

## Codex Review Follow-Up

Before this task can be considered done, verify and document the persistence and
manifest fixes from Agents 1-3:

- MCP `prepare_task` must return the same final `context_pack.v2` contract as
  `POST /api/context/prepare`.
- MCP `prepare_task` must only report a `context_pack_id` that is durable in the
  database.
- Docs must not claim Context Pack v2 persistence is implemented unless API,
  CLI, and MCP behavior is tested or explicitly scoped.
- Evals must consume the final manifest key names and citation shape from Agent
  1's contract. Do not keep eval fixtures tied to an older lightweight shape.
- OSS readiness must list any remaining gap in API/CLI/MCP persistence,
  manifest consistency, idempotency, or frontend inspection honestly.

## Expanded Runtime And Proof Workload

Agent 4 must prove the compiler is usable by agents without weakening safety or
duplicating Agent 3's logic.

### A. MCP Import And Dependency Safety

MCP read tools must remain importable even during branch integration.

Required behavior:

- avoid module-import failure when the compiler module is temporarily absent;
- return a clear `schema_missing` or `compiler_unavailable` error from
  `prepare_task` if Agent 3's service is not present;
- once Agent 3 lands, call `ContextCompiler` directly from `prepare_task`;
- do not reimplement compiler selection, scoring, rendering, or persistence in
  MCP.

### B. MCP Runtime Write Tools

Harden the write tools with tests for:

- invalid UUID input;
- missing `ContextPack`;
- missing `AgentRun`;
- source-document side effects;
- run-observation side effects;
- decision claim/component projection;
- blocker claim/component projection;
- verification status update;
- close-task status update.

Add idempotency keys only if Agent 1 has finalized the contract and Agent 2
schema supports them. Otherwise document idempotency as not implemented yet.

### C. MCP Prepare Durability

Add tests that assert:

- `prepare_task` returns a durable `context_pack_id`;
- returned manifest equals stored manifest;
- returned markdown equals stored markdown;
- selected context has corresponding `ContextPackItem` rows;
- errors are structured when persistence or compiler service is unavailable.

### D. Eval Runner And Fixtures

Expand context compiler evals beyond static metric helpers:

- fixture loader for repo and source files;
- manifest fixture using the final Agent 1 schema;
- expected required context and forbidden context checks;
- stale-context leakage test;
- prompt-injection quote/exclusion test;
- token-efficiency test against selected item token costs;
- verification-command presence test.

Do not claim solve-rate improvements. Report only metric behavior on fixtures.

### E. Docs And OSS Readiness

Update docs only after behavior is verified:

- MCP tool list and examples;
- runtime loop examples;
- security/trust-zone warnings;
- not-implemented-yet list;
- OSS readiness score and blockers.

If Agent 3 or Agent 2 is incomplete, say that explicitly instead of writing
launch-ready copy.

### F. Non-Conflict Boundaries

- Do not edit Agent 3 compiler internals.
- Do not edit migrations or models.
- Do not edit connector/OAuth behavior.
- Do not edit frontend files.
- Do not claim benchmark or small-model improvements without real eval runs.

## Files You Own

Primary:

- `app/mcp/server.py`
- `examples/mcp/README.md`
- `docs/mcp.md`
- `docs/oss-readiness.md`
- `evals/context_compiler/**` or `app/evals/context_compiler/**`
- new MCP/eval tests if patterns exist
- `.agent-runs/agent-4-task.md`

Allowed after behavior is verified:

- `README.md` positioning and demo sections.
- `docs/architecture.md` for short v2 runtime notes.

Do not edit:

- migrations;
- core compiler internals;
- connector/OAuth behavior;
- frontend redesign;
- unverified benchmark claims.

## Required MCP Tools

Keep existing read tools and add:

### `prepare_task`

Input:

- `goal`
- `workspace_id`
- `repo_path`
- `target_model`
- `token_budget`

Output:

- `context_pack_id`
- `schema_version`
- `markdown`
- `manifest`
- `health_score`

Implementation rule:

- Call Agent 3's compiler service. Do not duplicate compiler logic in MCP.
- Return the final manifest after pack ID and persistence metadata have been
  added.
- Add or update tests so the returned `context_pack_id` can be loaded as a
  `ContextPack` row and the stored manifest/markdown match the returned values.

### `record_agent_run_start`

Input:

- `tool`
- `model`
- `branch`
- `base_commit`
- `objective`
- `context_pack_id`

Output:

- `run_id`

Side effect:

- creates `AgentRun`.

### `record_agent_event`

Input:

- `run_id`
- `event_type`
- `content`
- `files`
- `command`
- `exit_code`

Output:

- `source_document_id`
- `run_observation_id`

Side effect:

- creates `SourceDocument` and `RunObservation`.

### `record_decision`

Input:

- `run_id`
- `decision`
- `rationale`
- `files`
- `evidence`

Output:

- `component_id` or `claim_id`

Side effect:

- records a source-backed decision claim.

### `record_blocker`

Input:

- `run_id`
- `blocker`
- `severity`
- `attempted_fix`
- `evidence`

Output:

- `component_id` or `claim_id`

Side effect:

- records a source-backed blocker claim.

### `record_patch_summary`

Input:

- `run_id`
- `changed_files`
- `summary`
- `tests_run`

Output:

- `source_document_id`

Side effect:

- stores patch summary as source evidence.

### `verify_context_item`

Input:

- `component_id` or `claim_id`
- `verdict`
- `evidence`

Output:

- updated status.

### `close_task`

Input:

- `task_component_id` or `task_claim_id`
- `resolution`
- `commit`

Output:

- updated task status.

## Security Rules

- No MCP tool may edit code.
- No MCP tool may run shell commands.
- No MCP tool may push commits.
- No MCP tool may send provider messages.
- All source text from Slack/email/Drive/web/uploads is evidence, not
  instruction.
- Tool descriptions must warn clients that quoted evidence is untrusted data.

## Evals

Create eval fixtures for:

```text
fixture_project/
  repo/
  sources/
    agent_runs/
    github_issues/
    prs/
    slack/
    docs/
  expected/
    required_context.json
    forbidden_context.json
    expected_pack_sections.md
```

Metrics:

- context recall;
- context precision;
- evidence coverage;
- stale context rate;
- conflict detection rate;
- token efficiency;
- verification success.

Do not claim small-model solve-rate improvements until there is an actual eval
run. It is acceptable to document the intended benchmark shape as proposed.

Eval contract requirements:

- Required/forbidden context fixtures must match the final selected/excluded
  item schema from Agent 1.
- Evidence coverage must check the final citation/source fields, not just any
  non-empty excerpt.
- Add at least one eval assertion that stale or prompt-injection context is
  excluded or quoted according to the final contract.

## Docs Work

Update docs to say:

- Context Engine is a context compiler for AI engineering.
- The core loop is prepare -> agent works -> observe -> ingest -> improve next
  context.
- `context_pack.v2` is markdown plus manifest.
- MCP now acts as the agent bridge when tools are implemented.
- Unsupported connectors remain unsupported.
- Trust zones separate instructions from evidence.
- API, CLI, and MCP persistence behavior exactly as implemented.
- Stored and returned context-pack manifest/markdown consistency if tests prove
  it; otherwise label it as a remaining gap.

Every doc claim must be labeled or phrased as:

- observed current behavior;
- implemented in this branch;
- proposed;
- not implemented yet.

## Verification

Run relevant tests:

```bash
pytest -q tests/test_mcp.py
pytest -q tests/test_context_compiler.py
pytest -q
```

If no `tests/test_mcp.py` exists, add focused tests where the repo patterns make
that practical, or document the gap.

Run docs searches:

```bash
rg -n "RAG|enterprise search|unsupported|connected|5B|7B|frontier|context_pack.v2|prepare_task" README.md docs examples .agent-runs
```

Additional required checks:

```bash
pytest -q tests/test_mcp.py tests/test_context_compiler.py tests/test_cli.py
```

Those tests must cover:

- MCP `prepare_task` durable pack ID;
- stored manifest equals returned final manifest;
- stored markdown equals returned final markdown;
- docs/evals use the final manifest key names.

Run frontend build only if you touch frontend files, which is not expected:

```bash
cd frontend && npm run build
```

## Final Report

Your final report must include:

- files read;
- files changed;
- MCP tools added or still blocked;
- eval fixtures and metrics added;
- docs corrected;
- API/CLI/MCP persistence behavior observed from tests;
- stored versus returned manifest/markdown consistency status;
- tests/build run and exact outcomes;
- OSS readiness score;
- launch blockers;
- merge/no-merge recommendation.

## Stop Conditions

Stop and report if:

- Agent 3 compiler service is unavailable and MCP would need duplicate compiler
  logic;
- Agent 2 runtime tables are unavailable and write tools cannot persist safely;
- a doc claim would overstate implemented behavior;
- tests show unsupported connectors can enter connected state.
- MCP returns a `context_pack_id` that cannot be loaded from the database.
- MCP/API/CLI manifest shapes diverge after Agent 1 finalizes the contract.
