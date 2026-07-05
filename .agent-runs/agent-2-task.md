# Agent 2 Task - Evidence Ledger And Claim Graph Backend

## Role

You are Agent 2 working in `/Users/darshann/Desktop/context-engine`.

You are the primary implementation agent for the v2 persistence and extraction
grounding layer. Codex is the integration owner. Keep your work backend-focused
and migration-safe.

## Branch

`agent/2-evidence-ledger-claim-graph`

## Read First

Read:

- `AGENTS.md`
- `TASK_PLAN.md`
- `.agent-runs/agent-2-task.md`
- `docs/architecture.md`
- `docs/knowledge-graph-contract.md`
- `app/models.py`
- `app/migrations.py`
- `app/alembic/env.py`
- `app/alembic/versions/0001_bootstrap_current_schema.py`
- `app/services/ingest.py`
- `app/processing/extractor.py`
- `app/processing/source_extractors.py`
- `app/taxonomy.py`
- `tests/test_migrations.py`
- `tests/test_ingestion.py`
- `tests/test_extraction.py`
- `tests/test_adversarial_graph.py`

If Agent 1's contract docs exist on your branch, read them too. If they do not,
use `TASK_PLAN.md` as the contract and state that assumption in your report.

## Mission

Add the backend layer for:

- immutable evidence spans;
- normalized claims;
- append-only claim revisions;
- component projection from claims;
- context pack persistence tables;
- agent run and observation tables;
- repo intelligence tables;
- extraction validation that prevents ungrounded claims from becoming active.

## Codex Review Follow-Up

Before this task can be considered done, validate the persistence layer against
the current v2 review findings:

- Confirm the runtime tables can support a durable final `context_pack.v2`
  artifact, not only a flushed in-memory response.
- `ContextPack` must be able to store the final markdown and final manifest
  after the compiler adds pack identifiers and persistence metadata.
- `ContextPackItem` must be able to store each selected item's score, inclusion
  reason, token cost, and any available component/claim/evidence references.
- If the final manifest contract requires fields not representable by the
  current tables, stop and report the schema delta instead of working around it
  in Agent 3 code.
- Add migration/ORM tests that round-trip a `ContextPack` and at least one
  `ContextPackItem` with the fields Agent 3 and Agent 4 consume.

## Expanded Backend Workload

The backend slice must now be complete enough that Agent 3 and Agent 4 do not
need to modify schema or invent persistence workarounds.

### A. Runtime Schema Hardening

Validate and, if needed within owned files, add migration-safe support for:

- final `ContextPack.manifest` JSON text;
- final `ContextPack.markdown` text;
- `ContextPack.health_score`;
- selected item score, inclusion reason, token cost, component reference, and
  evidence-span reference;
- claim-level item references if Agent 1 finalizes `claim_id` as required;
- indexes needed for loading packs by workspace, creation time, and target
  model.

### B. Evidence Ledger Hardening

Add or complete tests for:

- `content_sha256` backfill and insert behavior;
- source-created timestamp parsing from metadata;
- exact span location by character range;
- exact span hash mismatch rejection;
- fuzzy evidence becoming `needs_review`;
- hostile or prompt-injection text scoring;
- untrusted external source text never becoming active without exact evidence.

### C. Claim Graph Hardening

Add or complete tests for:

- append-only revisions;
- current revision pointer updates;
- contradiction operation with explicit target claim;
- supersession operation with explicit target claim;
- resolved/stale/rejected status transitions;
- legacy components without `claim_id` still appearing in graph/query reads.

### D. Runtime Table Round Trip

Add a focused test that creates:

- one `ContextPack`;
- two `ContextPackItem` rows;
- one `AgentRun`;
- one `RunObservation`;
- one repo index row set if repo tables are present.

Read those records in a fresh session or new transaction and assert the stored
fields match exactly.

### E. Non-Conflict Boundaries

- Do not implement `ContextCompiler`.
- Do not add `ctxe prepare`.
- Do not register HTTP routes.
- Do not edit MCP server behavior.
- Do not change connector status semantics.

## Files You Own

Primary:

- `app/models.py`
- `app/migrations.py`
- `app/alembic/versions/*`
- `app/services/ingest.py`
- `app/processing/extractor.py`
- `app/processing/source_extractors.py`
- `app/taxonomy.py`
- `tests/test_migrations.py`
- `tests/test_ingestion.py`
- new `tests/test_evidence_ledger.py`
- new `tests/test_claim_graph.py`

Allowed if needed:

- new `app/services/evidence.py`
- new `app/services/claims.py`

Do not edit:

- MCP server implementation;
- context compiler service;
- CLI command behavior;
- frontend files;
- connector status semantics;
- README positioning.

## Required Implementation

### 1. SourceDocument Additions

Add migration-safe nullable fields if absent:

- `content_sha256`
- `trust_zone`
- `source_created_at`

Rules:

- Existing rows must migrate without data loss.
- New rows should compute `content_sha256`.
- Default trust zone should be conservative by source type:
  - repo/local code: `trusted_repo`;
  - user/imported agent run: `trusted_human` or `semi_trusted_tool` depending on
    source metadata;
  - Slack/email/Drive/web/upload: `untrusted_external`;
  - test adversarial fixtures: `hostile_test`.

### 2. EvidenceSpan Table

Add model and migration for:

- `id`
- `workspace_id`
- `source_document_id`
- `start_char`
- `end_char`
- `text_sha256`
- `evidence_type`
- `authority_weight`
- `trust_zone`
- `prompt_injection_risk_score`
- `extraction_method`
- `created_at`

Implement helper behavior:

- locate exact span text inside `SourceDocument.content`;
- compute and verify span hash;
- reject impossible ranges;
- allow explicit `needs_review` path for fuzzy evidence;
- score obvious prompt-injection phrases.

### 3. Claim And ClaimRevision Tables

Add models and migrations for `Claim` and `ClaimRevision`.

`Claim` must include:

- `id`
- `workspace_id`
- `identity_key`
- `claim_type`
- `status`
- `temporal`
- `confidence`
- `authority_weight`
- `current_revision_id`
- timestamps

`ClaimRevision` must include:

- `id`
- `claim_id`
- `evidence_span_id`
- `value`
- `operation`
- `confidence_delta`
- `created_at`

Rules:

- Revisions are append-only.
- Active claims require evidence.
- Ungrounded claims become `needs_review`.
- Supersession and contradiction must not silently overwrite old claims.

### 4. Component Projection

Add nullable `Component.claim_id`.

Rules:

- Existing components must continue to work.
- New grounded claims should create or update a current `Component` projection.
- `Component.provenance` and `Component.excerpt` must remain populated for API
  compatibility.

### 5. Context Runtime Tables

Add tables for:

- `ContextPack`
- `ContextPackItem`
- `AgentRun`
- `RunObservation`
- `CodeFile`
- `CodeSymbol`
- `CodeEdge`
- `RepoEvent`

Keep them minimal but compatible with `TASK_PLAN.md`. Agents 3 and 4 will use
these tables.

Runtime persistence requirements:

- `ContextPack.pack_version` must store `context_pack.v2`.
- `ContextPack.markdown` must store the final rendered markdown returned to API,
  CLI, and MCP clients.
- `ContextPack.manifest` must store the final manifest JSON returned to clients,
  including the durable pack ID and persistence metadata.
- `ContextPackItem` must support selected context audit fields:
  `context_pack_id`, `component_id`, `evidence_span_id`, `score`,
  `inclusion_reason`, and `token_cost`.
- If Agent 1 finalizes claim-level item references and a `claim_id` column is
  needed on `ContextPackItem`, add it migration-safely and cover it in tests.

### 6. Extraction Grounding

Update deterministic and fallback extraction paths so that:

- source content is preserved first;
- spans are created before claims;
- claims are atomic;
- model names and fact types remain canonical;
- relationships require evidence or deterministic rules;
- unresolved relationship targets stay unresolved, not hallucinated;
- low-confidence or ungrounded output is `needs_review`.

Do not degrade existing ingestion behavior.

## Tests To Add

Add focused tests for:

- source document hash creation;
- evidence span range and hash validation;
- prompt-injection risk scoring;
- claim revision append-only behavior;
- ungrounded LLM claim becomes `needs_review`;
- grounded deterministic claim becomes active;
- component projection preserves old graph API compatibility;
- migration idempotency on SQLite;
- existing source documents remain readable after migration;
- relationships still require evidence/confidence.
- context pack and context pack item ORM round-trip;
- migrated runtime tables can store the final manifest/markdown shape required
  by Agent 1's contract.

## Verification

Run at minimum:

```bash
pytest -q tests/test_migrations.py
pytest -q tests/test_ingestion.py tests/test_extraction.py
pytest -q tests/test_evidence_ledger.py tests/test_claim_graph.py
pytest -q tests/test_adversarial_graph.py
```

Run full backend tests if the migration touches shared model behavior:

```bash
pytest -q
```

## Final Report

Your final report must include:

- changed files;
- schema changes;
- migration behavior;
- tests run and exact results;
- observed evidence that legacy graph reads still work;
- observed evidence that runtime persistence tables can store final
  context-pack output;
- risks;
- remaining gaps for Agents 3, 4, and Codex.

## Stop Conditions

Stop and report if:

- migration cannot preserve existing SQLite rows;
- extraction cannot locate evidence spans reliably and would need broad
  behavior changes;
- you need to change connector semantics;
- a required schema field conflicts with current code in a way that needs Codex
  architecture review.
- the final Context Pack v2 manifest cannot be represented without a schema
  change outside your owned files.
