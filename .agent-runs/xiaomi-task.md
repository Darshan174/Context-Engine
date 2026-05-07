# MiMo V2.5 Task

## Coding Capability Rank

5 of 5.

MiMo is a senior long-context repo reviewer, documentation reviewer, UX reviewer, and readiness evaluator. Use it after implementation to find stale claims, missing evidence, weak product logic, and documentation drift.

## Branch

`agent/mimo-knowledge-graph-review`

## Mission

Review the 10x knowledge-graph engineering work after Kimi, GLM, DeepSeek, and Qwen. The goal is to decide whether Context Engine now behaves like a credible engineering memory system for GitHub issues/PRs and AI markdown sessions.

Do not work on connector availability or provider OAuth.

## Current Repo Facts To Verify First

- Read `README.md`, `project.md`, `TASK_PLAN.md`, `AGENTS.md`, and `docs/`.
- Read `app/models.py`, `app/taxonomy.py`, `app/processing/extractor.py`, `app/services/ingest.py`, `app/api/graph.py`, `app/api/models_api.py`, and `app/agents/`.
- Read `frontend/src/pages/GraphView.jsx` and relevant API hooks.
- Read all tests touched by GLM, DeepSeek, and Qwen.

Do not trust prior reports without checking files.

## 10x Workload

### 1. Product Readiness Review

Evaluate whether the product now answers the real user questions:

- What changed recently?
- What is blocked?
- Which PRs implement which decisions?
- Which issues are resolved by which PRs?
- Which AI sessions produced useful decisions/tasks/risks?
- Which relationships are evidence-backed?
- What context pack should another coding agent receive?

### 2. Documentation Truth Review

Find and fix stale or overbroad docs:

- README claims about graph capabilities;
- project docs about current status;
- task plans that still emphasize connector work;
- graph contract docs that do not match code;
- agent docs that overclaim relationship inference;
- setup/test instructions that no longer match reality.

### 3. UX Review

Review graph display from an engineering-user perspective:

- Can a user inspect node provenance quickly?
- Can a user inspect edge evidence quickly?
- Are candidate/proposed edges visually distinct?
- Are low-confidence edges hidden or clearly marked?
- Does the source-to-knowledge diff make imports understandable?
- Does the UI support GitHub and AI-session source types clearly?
- Does the graph avoid decorative complexity?

### 4. AI Agent Function Review

Review whether the in-project AI agents are functioning:

- GraphBuilderAgent;
- GapDetectorAgent;
- RelationshipAgent;
- ContextPackAgent;
- API wrappers under `/api/agents/*`;
- graph build API under `/api/graph/build`.

Classify each as:

- functioning;
- partially functioning;
- blocked;
- untested.

Ground every classification in code/tests.

### 5. Test and Evidence Review

Verify:

- backend tests cover GitHub and AI-session graph extraction;
- adversarial relationship tests exist;
- graph API tests include display metadata;
- migration tests cover new fields;
- frontend build passes if frontend changed;
- docs cite true behavior only.

### 6. Final Readiness Score

Produce:

- readiness score out of 10;
- launch blockers;
- serious risks;
- polish issues;
- exact files/areas requiring Codex final review.

## Required Commands

Run:

- `pytest -q`
- `npm run build` if frontend changed or if display behavior is under review.

## Deliverables

Final report must include:

- files read;
- files changed;
- evidence-backed findings by severity;
- docs corrected;
- tests/build run;
- readiness score;
- merge/no-merge recommendation.

## Rules

- No connector/OAuth work.
- No unsupported claims.
- No vague product advice without code evidence.
- Do not rewrite implementation unless a small doc/code fix is necessary.
- Keep review findings actionable and file-grounded.
