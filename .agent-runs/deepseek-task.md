# DeepSeek V4 Task

## Coding Capability Rank

3 of 5.

DeepSeek is a senior hard-bug, reasoning, and validation engineer. Use it to break the graph, prove edge cases, and force the implementation to stay evidence-backed.

## Branch

`agent/deepseek-graph-validation`

## Mission

Stress-test the knowledge graph implementation for correctness. The goal is to prevent hallucinated models, components, and relationships, especially for GitHub issues/PRs and AI markdown sessions.

Do not work on connector availability or provider OAuth.

## Current Repo Facts To Verify First

- Relationship persistence currently flows through `app/services/ingest.py` and `app/agents/relationship_agent.py`.
- Relationship inference also exists in `app/agents/graph_builder.py`.
- Relationship display data is exposed through `app/api/graph.py`.
- Extraction rules live in `app/processing/extractor.py`.
- Canonical types live in `app/taxonomy.py`.

Verify these before editing. If the code changed, report exact paths.

## 10x Workload

### 1. Adversarial Relationship Tests

Create adversarial tests proving the graph does not connect unrelated facts:

- two components share a common noun but no explicit link;
- two PRs touch similar files but solve unrelated issues;
- two AI sessions mention the same generic term like “auth” or “graph”;
- a closed historical issue is mentioned in a current session but should not become active work;
- a markdown heading contains a model name but no atomic fact;
- an LLM-style summary makes a claim not supported by the source text.

Expected outcome: no relationship unless there is explicit evidence.

### 2. Evidence and Confidence Enforcement

Test and harden:

- relationships require non-empty evidence;
- confidence is clamped to 0.0-1.0;
- low-confidence relationships are skipped or stored as hidden/proposed according to contract;
- deterministic GitHub/file relationships can use deterministic evidence;
- AI-suggested relationships are always `proposed` unless verified.

### 3. GitHub Issue/PR Edge Cases

Add tests for:

- PR body with `Fixes #123` creates a deterministic issue relationship.
- PR references issue number in unrelated prose and should not imply resolution.
- PR changed files create file/module components without exploding into hundreds of noisy nodes.
- Review comments create blocker/risk components only when actionable.
- Closed/merged state maps to temporal/status correctly.
- Duplicate issue titles remain distinct by source ID or external ID.

### 4. AI Markdown Session Edge Cases

Add tests for:

- task list extraction;
- final recommendation extraction;
- review finding extraction;
- file reference extraction;
- session-root relationship to extracted components;
- no extraction from generic acknowledgements;
- no duplicate components from repeated final summary text;
- provenance preserved at least to source document and evidence excerpt.

### 5. Graph API and MCP Validation

Verify graph consumers preserve truth:

- `/api/graph` includes confidence, evidence, status, temporal, source type, and source URL/source ID.
- stale/deprecated components do not produce misleading active relationships.
- MCP/query/context-pack outputs preserve provenance or explicitly state when provenance is unavailable.
- graph stats match persisted rows.

### 6. Migration and Storage Safety

If schema changes were made by GLM or Qwen:

- test old SQLite databases upgrade safely;
- test migration idempotency;
- ensure nullable/default columns do not break existing rows;
- ensure indexes do not break SQLite.

### 7. Failure Report

Produce a bug-focused report:

- confirmed bugs;
- fixed bugs;
- tests added;
- behavior still unproven;
- any relationship type that remains too dangerous to show by default.

## Required Commands

Run:

- `pytest -q`

If frontend display metadata changed and frontend files were touched by others, also run:

- `npm run build`

## Rules

- Tests first when possible.
- Minimal fixes after failures.
- No broad refactors.
- No connector/OAuth work.
- No accepting AI claims without source evidence.
- Keep relationship line ranges and evidence tight.
