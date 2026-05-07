# Kimi K2.6 Task

## Role

You are Kimi K2.6 working in `/Users/darshann/Desktop/context-engine`.

You are the main builder for the knowledge-graph UI implementation. Codex is the architect, reviewer, and final judge. Your job is to implement a large, evidence-backed UI slice from the existing contract, not to make final product or architecture decisions.

Do not merge. Do not open a PR unless explicitly asked. Do not work on stale branches. Do not touch `.agent-runs/glm-task.md` or other agent task files.

## Branch And Safety Rules

Before editing, run:

```bash
git status --short --branch
git fetch origin
git branch --show-current
```

Continue only if you are on a safe working branch based on the current repair branch or current main. If you are on `agent/qwen-graph-reasoning-validation`, stop immediately. That branch was previously identified as an unsafe stale/destructive rollback branch.

Non-negotiable rules:

- Treat `docs/knowledge-graph-display-strategy.md` as the implementation contract.
- Verify every assumption in code, tests, API payloads, or local docs before depending on it.
- Do not invent connectors, PR state, issue state, owners, merge state, source coverage, or graph relationships.
- Do not make `ai_proposed` or `proposed` relationships look deterministic.
- Preserve provenance and evidence in every UI state.
- Do not break the Connectors page catalog. It must continue to show Slack, GitHub, Discord, AI Context, Local Files, Codex, Claude, OpenCode, Zoom, GDrive, Gmail, and Wispr Flow according to backend availability.
- Do not work on connector OAuth/provider authentication.
- Do not revert user changes.

## Context You Must Read First

Read these files before making any implementation decision:

- `AGENTS.md`
- `docs/knowledge-graph-display-strategy.md`
- `docs/knowledge-graph-contract.md`
- `docs/connectors-graph-contract.md`
- `frontend/src/pages/GraphView.jsx`
- `frontend/src/pages/Connectors.jsx`
- `frontend/src/api/hooks.js`
- `frontend/src/App.jsx`
- `app/api/graph.py`
- `app/api/connectors.py`
- `app/taxonomy.py`
- `app/services/ingest.py`
- `app/processing/source_extractors.py`
- `tests/test_graph_api.py`
- `tests/test_knowledge_graph.py`
- `tests/test_adversarial_graph.py`
- `tests/test_connectors.py`

Use previous session files only as leads, never as proof:

- `/Users/darshann/.codex/sessions/2026/05/03/rollout-2026-05-03T22-20-54-019deec0-037d-7af3-8ecf-f53635a66a48.jsonl`
- `/Users/darshann/.codex/sessions/2026/05/05/rollout-2026-05-05T08-34-42-019df618-5306-7873-b1cd-3eb1bdfd60b4.jsonl`

## Current Handoff

Treat these as handoff leads that you must verify locally:

- Backend graph review regressions were repaired on `codex/fix-graph-review`.
- `docs/knowledge-graph-display-strategy.md` exists and is the contract.
- A first graph UI pass exists in `frontend/src/pages/GraphView.jsx`.
- Connector catalog rendering was recently repaired in `frontend/src/api/hooks.js`; do not regress it.

If any lead is false in your checkout, report the mismatch and stop before editing.

## Mission

Implement the next heavy graph UI slice so the Graph page becomes a project command map. The graph must let a user understand, at a glance:

- what the project is made of;
- what is active, blocked, stale, proposed, or completed;
- which GitHub issues, PRs, files, and review findings connect to work;
- which AI sessions from Codex, Claude, OpenCode, Kimi, GLM, or compatible imports generated tasks, decisions, risks, or file references;
- which connector/source produced each node and edge;
- which relationships are deterministic, extracted, proposed, AI-proposed, or human verified.

This is a 20x workload. Do not stop at a cosmetic pass.

## Implementation Scope

Primary file:

- `frontend/src/pages/GraphView.jsx`

Allowed adjacent frontend files if required:

- `frontend/src/api/hooks.js`
- `frontend/src/App.jsx`
- `frontend/src/components/*`
- `frontend/src/fixtures/mockData.js`

Backend files are allowed only if the UI cannot render the documented contract from real API payloads:

- `app/api/graph.py`
- `app/taxonomy.py`
- `tests/test_graph_api.py`
- `tests/test_knowledge_graph.py`
- `tests/test_adversarial_graph.py`

Avoid unless there is a proven graph-contract bug:

- connector OAuth/provider code;
- migrations;
- unrelated dashboard/sources/connectors redesigns;
- broad refactors.

## Required UI Work

### 1. First-Load Command Map

Make the default graph load useful at 100% browser zoom without requiring browser zoom changes.

The first view must prioritize:

- current high-confidence decisions;
- active tasks;
- blockers and risks;
- GitHub delivery nodes;
- AI sessions;
- source coverage gaps.

Low-confidence, stale, or proposed items should be visible but visually secondary or collapsed behind clear counts.

### 2. View Modes

Implement or harden these view modes from the strategy:

- `All`
- `CEO View`
- `Bird's Eye`
- `Gap Detector`
- `Decision Trail`
- `AI Sessions`
- `GitHub Delivery`
- `Repository`

Each mode must change the graph data presentation in a meaningful way. Do not add tabs that only change labels.

Required behavior:

- `CEO View`: compact clusters for decisions, active tasks, blockers/risks, GitHub work, and AI sessions.
- `Bird's Eye`: all major clusters with lighter detail and disconnected areas visible.
- `Gap Detector`: isolated nodes, missing owners, stale active work, low-confidence relationships, unresolved blockers.
- `Decision Trail`: decision -> source/session -> tasks/PRs/files -> remaining risks.
- `AI Sessions`: session -> generated tasks/decisions/risks -> touched files/PRs/issues.
- `GitHub Delivery`: issue -> PR -> changed files -> review findings -> tasks/decisions.
- `Repository`: repo/file/module clusters with connected tasks, PRs, risks, and agent sessions.

### 3. Node Grouping

Group nodes only when backed by `model_name`, `fact_type`, `source_type`, metadata, or explicit relationships.

Required groups:

- Decisions
- Active Work
- Risks & Blockers
- GitHub Delivery
- AI Sessions
- Sources & Connectors
- Product / Feature
- Repository / Files
- Other Context

Do not label a node as GitHub PR, GitHub Issue, Codex, Claude, OpenCode, Kimi, or GLM unless source type or metadata supports it.

### 4. Edge Trust Semantics

Make edge origin visually unambiguous:

- `deterministic`: solid blue, highest trust.
- `extracted`: solid violet, source-backed but less authoritative.
- `human_verified`: solid green, verified.
- `ai_proposed`: dashed amber, candidate only.
- `proposed`: dotted gray, weak/candidate only.

Confidence must affect opacity or thickness. Missing evidence must be visually warned in the inspector.

### 5. Filters And Search

Ensure filters work with real payload fields:

- model;
- source family/type;
- status;
- temporal horizon;
- confidence;
- edge origin;
- relationship type if feasible;
- text search across title/value/source metadata.

Filter empty states must explain what filter combination hid the graph.

### 6. Inspectors

Selected node inspector must show:

- title/name/value;
- model;
- fact type;
- status;
- temporal state;
- confidence;
- source type/family;
- source URL or external ID when available;
- source metadata summary;
- evidence/provenance excerpt;
- relationship count;
- connected nodes grouped by relationship type;
- warnings for stale/proposed/low-confidence/missing evidence.

Selected edge inspector must show:

- relationship type and label;
- origin;
- confidence;
- status;
- evidence;
- source/provenance;
- source and target nodes;
- warning if proposed/AI-proposed/low-confidence.

### 7. Side Panels

Implement or harden compact panels for:

- graph stats;
- source coverage;
- gap detector output;
- AI session summary;
- GitHub delivery summary;
- repository/file summary.

These panels must be dense and useful. Avoid marketing copy.

### 8. Visual QA

Use the browser or screenshots if available. Test at:

- desktop width around 2048x1152;
- laptop width around 1440x900;
- mobile/narrow width if the route supports it;
- 100% browser zoom.

Fix overlap, clipped text, empty whitespace, unreadable edge labels, hidden controls, and panels covering the graph.

## Tests And Verification

Run:

```bash
cd frontend && npm run build
```

Run relevant backend tests if backend files changed:

```bash
pytest -q tests/test_graph_api.py tests/test_knowledge_graph.py tests/test_adversarial_graph.py tests/test_connectors.py
```

If frontend test infrastructure has no test files, state that explicitly. Do not report it as a passing test.

If a dev server is used, verify:

- `/app/graph` renders without crashing;
- `/app/connectors` still shows the connector catalog;
- graph controls fit without browser zoom changes.

## Final Report

Your final response must include:

- files read;
- files changed;
- what graph behavior changed;
- how each view mode differs;
- how anti-hallucination rules are enforced;
- connector page regression check result;
- commands run and exact outcomes;
- known risks;
- what GLM should challenge.

## Success Bar

This task is complete only if the UI is materially more useful as a graph command map and Codex can review the diff without guessing what was intended.
