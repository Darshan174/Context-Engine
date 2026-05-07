# Kimi K2.6 Task

## Role

You are Kimi K2.6 working in `/Users/darshann/Desktop/context-engine`.

You are the evidence-first architecture and product-strategy reviewer for the knowledge graph. Your job is not to write broad product prose. Your job is to read the actual repo, find the truth, define a robust graph/display strategy, and produce a contract that GLM can implement without hallucinating.

## Non-Negotiable Rules

- Do not edit connector OAuth/provider code.
- Do not claim behavior exists unless you verified it in code, tests, API responses, or session files.
- Do not rely on old reports as truth. Treat them as leads only.
- Every factual claim about current behavior must cite file paths and functions/classes/endpoints. Include line numbers when practical.
- If evidence is missing, say `unverified` and list exactly how to verify it.
- Do not invent model names, relationship types, source types, endpoints, or UI states.
- Do not make MD task files for other models. This round is for Kimi and GLM only.

## Context You Must Read First

Read these before writing conclusions:

- `AGENTS.md`
- `app/models.py`
- `app/taxonomy.py`
- `app/services/ingest.py`
- `app/processing/extractor.py`
- `app/processing/source_extractors.py`
- `app/sync/github.py`
- `app/sync/ai_session.py`
- `app/importers/ai_context.py`
- `app/api/graph.py`
- `app/api/connectors.py` only for source-document creation paths, not OAuth work
- `app/agents/graph_builder.py`
- `app/agents/gap_detector.py`
- `app/agents/relationship_agent.py`
- `app/agents/context_pack.py`
- `frontend/src/pages/GraphView.jsx`
- `frontend/src/api/hooks.js`
- `docs/knowledge-graph-contract.md`
- `docs/connectors-graph-contract.md`
- `tests/test_knowledge_graph.py`
- `tests/test_adversarial_graph.py`
- `tests/test_graph_api.py`
- `tests/test_ingestion.py`
- `tests/test_agents.py`

Also inspect these session files if available:

- `/Users/darshann/.codex/sessions/2026/05/03/rollout-2026-05-03T22-20-54-019deec0-037d-7af3-8ecf-f53635a66a48.jsonl`
- `/Users/darshann/.codex/sessions/2026/05/05/rollout-2026-05-05T08-34-42-019df618-5306-7873-b1cd-3eb1bdfd60b4.jsonl`

Use them only to recover project context and prior decisions. They are not proof of current code behavior.

## Mission

Create the 20x knowledge-graph engineering strategy for organizing the graph UI around:

- models
- components
- relationships
- GitHub issues and PRs
- repos/files/changed modules
- source documents from connectors
- workload sessions from Codex, Claude, OpenCode, and similar AI tools
- AI agents such as graph builder, gap detector, relationship detector, and context pack generator

The goal is a graph display where a user can understand the project at a glance:

- What is true now?
- What is planned?
- What is blocked?
- Which issues/PRs/files implement which tasks/decisions?
- Which AI sessions produced which decisions, tasks, risks, or file changes?
- Which source connector produced the evidence?
- Which edges are deterministic, extracted, proposed, or human verified?

## Required Investigation

### 1. Current-State Truth Table

Produce a table with these columns:

- Area
- Verified current behavior
- Evidence path/function/test
- Gap
- Fix required before UI can trust it

Cover at least:

- `SourceDocument.source_type` values used by GitHub sync
- `SourceDocument.source_type` values used by AI session import
- canonical source-type handling in taxonomy
- canonical model names
- canonical fact types
- canonical relationship types
- relationship origin semantics
- component provenance and excerpt fields
- relationship evidence handling
- graph API payload fields
- graph-slice payload fields
- component detail endpoint
- relationship detail endpoint
- source-diff endpoint
- work-lens endpoint
- frontend graph filters
- frontend CEO views
- frontend selected node/edge inspectors
- agent sidebar behavior

### 2. Find Contract Mismatches

You must explicitly check for these likely loopholes and confirm or reject them:

- GitHub sync stores both issues and PRs as `source_type="github"` while source extractors expect `github_issue` and `github_pr`.
- AI session imports may use `codex`, `claude`, `opencode`, `agent_session`, and older `ai_context_*` names inconsistently.
- Taxonomy may not include product-critical relationships: `fixes`, `resolved_by`, `touches_file`, `conflicts_with`, `implements`.
- API response models may be inconsistent with fields returned by graph-slice/detail/diff endpoints.
- Relationship origin values may be inconsistent across backend and frontend: `proposed`, `deterministic`, `extracted`, `ai_proposed`, `human_verified`.
- Source-diff and work-lens may exist but not be wired into the visible Graph UI.
- Weak/template evidence may be displayed as if it were source-backed truth.

Do not assume these are true. Verify each one.

### 3. Design the Display Strategy

Design the graph as a project command map, not a decorative graph.

Your strategy must specify:

- default first-load view
- node grouping lanes or zones
- visual hierarchy
- graph layout rules
- filter defaults
- edge style semantics
- node card content
- selected-node inspector content
- selected-edge inspector content
- source-to-knowledge diff panel behavior
- work-lens behavior
- AI sessions view behavior
- GitHub PR/issue view behavior
- repo/file view behavior
- gap detector behavior
- context-pack-from-selection behavior

The strategy must make these distinctions obvious:

- source-backed deterministic truth
- extracted fact with confidence
- AI-proposed candidate
- stale/deprecated historical context
- missing evidence
- blocked/needs-review state

### 4. Implementation Contract For GLM

Write a precise implementation contract GLM can execute.

Include:

- files GLM should inspect first
- files GLM is allowed to edit
- files GLM should avoid unless required
- exact backend fixes required
- exact frontend fixes required
- exact tests required
- accepted source-type vocabulary
- accepted fact-type vocabulary
- accepted relationship-type vocabulary
- accepted relationship-origin vocabulary
- migration constraints
- API backward-compatibility constraints
- UI acceptance criteria
- verification commands

## Required Output File

Update or create:

- `docs/knowledge-graph-display-strategy.md`

This document must include:

1. `Verified Current State`
2. `Known Contract Mismatches`
3. `Canonical Graph Vocabulary`
4. `Display Strategy`
5. `Backend Implementation Contract`
6. `Frontend Implementation Contract`
7. `Tests Required`
8. `Open Questions`
9. `No-Hallucination Checklist`

## Final Report

Your final response must include:

- files read
- files changed
- mismatches found
- implementation contract summary
- confidence level for each major claim
- items still unverified

## Success Bar

This task is complete only when GLM can implement from your contract without guessing. If any part of the graph strategy depends on a behavior you did not verify, mark it as unverified and block implementation of that part until verified.
