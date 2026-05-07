# GLM 5.1 Task

## Role

You are GLM 5.1 working in `/Users/darshann/Desktop/context-engine`.

You are the secondary builder and adversarial checker. Your job is to challenge Kimi's implementation, find bugs, add focused tests, repair small confirmed issues, and document anything that is still unsafe. Codex is the architect, reviewer, and final judge.

Do not make final product or architecture decisions. Do not merge. Do not open a PR unless explicitly asked. Do not touch `.agent-runs/kimi-task.md` or other agent task files.

## Branch And Safety Rules

Before editing, run:

```bash
git status --short --branch
git fetch origin
git branch --show-current
```

Continue only if you are on a safe working branch based on the current repair branch or current main. If you are on `agent/qwen-graph-reasoning-validation`, stop immediately. That branch was previously identified as an unsafe stale/destructive rollback branch.

Non-negotiable rules:

- Treat `docs/knowledge-graph-display-strategy.md` as the contract, but verify it against the repo before relying on it.
- Review Kimi's current diff before making changes.
- Do not invent graph data, source coverage, GitHub state, owners, PR status, or connector support.
- Do not make proposed or AI-proposed edges look certain.
- Preserve provenance and evidence.
- Keep fixes small unless you find a confirmed blocker.
- Do not work on connector OAuth/provider authentication.
- Do not revert user changes.
- Keep the Connectors page catalog working.

## Context You Must Read First

Read these files before reviewing or editing:

- `AGENTS.md`
- `docs/knowledge-graph-display-strategy.md`
- `.agent-runs/kimi-task.md`
- `frontend/src/pages/GraphView.jsx`
- `frontend/src/pages/Connectors.jsx`
- `frontend/src/api/hooks.js`
- `frontend/src/App.jsx`
- `app/api/graph.py`
- `app/api/connectors.py`
- `app/taxonomy.py`
- `tests/test_graph_api.py`
- `tests/test_knowledge_graph.py`
- `tests/test_adversarial_graph.py`
- `tests/test_connectors.py`

Use previous session files only as leads, never as proof:

- `/Users/darshann/.codex/sessions/2026/05/03/rollout-2026-05-03T22-20-54-019deec0-037d-7af3-8ecf-f53635a66a48.jsonl`
- `/Users/darshann/.codex/sessions/2026/05/05/rollout-2026-05-05T08-34-42-019df618-5306-7873-b1cd-3eb1bdfd60b4.jsonl`

## Mission

Perform a brutal implementation review and targeted repair pass for the graph UI work.

Your goal is to answer:

- Does the UI actually implement `docs/knowledge-graph-display-strategy.md`?
- Does it use real API fields instead of hallucinated categories?
- Are node groups backed by model, fact type, source type, metadata, or explicit relationships?
- Are edge trust semantics truthful?
- Does the graph remain usable at 100% browser zoom?
- Does `/app/connectors` still show the connector catalog?
- Are there missing tests or obvious regressions?

## Required Review Loop

### 1. Establish The Diff

Run:

```bash
git status --short --branch
git diff --stat
git diff -- frontend/src/pages/GraphView.jsx frontend/src/api/hooks.js frontend/src/pages/Connectors.jsx app/api/graph.py app/taxonomy.py tests/test_graph_api.py tests/test_knowledge_graph.py tests/test_adversarial_graph.py tests/test_connectors.py
```

Do not assume Kimi changed only the intended files. Report any unexpected file changes.

### 2. Contract Compliance Audit

Build a checklist from `docs/knowledge-graph-display-strategy.md` and mark each item:

- implemented;
- partially implemented;
- missing;
- implemented but unsafe;
- unverified.

Cover at minimum:

- default first-load command map;
- CEO View;
- Bird's Eye;
- Gap Detector;
- Decision Trail;
- AI Sessions;
- GitHub Delivery;
- Repository;
- node grouping;
- source family labeling;
- edge origin styles;
- confidence styling;
- selected node inspector;
- selected edge inspector;
- source metadata display;
- missing evidence warnings;
- filters;
- empty states;
- connector catalog preservation.

### 3. Anti-Hallucination Audit

Look specifically for these bugs:

- code labels nodes as PRs/issues/agents from title text alone;
- code treats `github` raw source as enough to know issue vs PR without metadata;
- code labels Codex/Claude/OpenCode/Kimi/GLM without source metadata;
- code invents owner, merged state, branch, commit, or blocker status;
- code hides proposed/AI-proposed status behind color only;
- code displays source coverage counts without real source fields;
- code silently drops low-confidence or stale items without a count or explanation;
- code adds decorative panels that do not reflect real graph data.

### 4. Functional Regression Audit

Verify:

- `/app/graph` can render with real or fixture data;
- graph controls do not require browser zoom changes;
- selected node/edge states do not crash on missing optional fields;
- empty graph state is useful;
- filters do not create misleading totals;
- `/app/connectors` still shows catalog entries from the backend shape `{ connectors, setupStatus }`;
- frontend hook normalization still handles both array and object connector responses.

### 5. Targeted Repairs

You may make repairs only when the issue is confirmed and the fix is scoped.

Preferred files for repairs:

- `frontend/src/pages/GraphView.jsx`
- `frontend/src/api/hooks.js`
- focused frontend helper/component files if they already exist;
- focused backend graph response fixes only if a real API contract mismatch blocks UI truthfulness;
- focused tests.

Do not rewrite Kimi's implementation wholesale. If the implementation is too flawed for a small repair, document it as a blocker for Codex.

### 6. Tests And Verification

Run:

```bash
cd frontend && npm run build
```

If frontend tests exist, run them. If Vitest reports no test files, say that explicitly.

If backend files changed, run:

```bash
pytest -q tests/test_graph_api.py tests/test_knowledge_graph.py tests/test_adversarial_graph.py tests/test_connectors.py
```

If possible, run a browser smoke check:

- `/app/graph`
- `/app/connectors`

Capture or describe the exact visual result. Do not say it is good without checking.

## Output Required

Create or update:

- `.agent-runs/glm-review-report.md`

The report must include:

1. `Diff Reviewed`
2. `Contract Compliance Matrix`
3. `Anti-Hallucination Findings`
4. `Functional Regression Findings`
5. `Repairs Made`
6. `Tests Run`
7. `Remaining Blockers`
8. `Merge Recommendation`

The merge recommendation must be one of:

- `safe for Codex final review`;
- `needs targeted repair before Codex final review`;
- `do not merge`.

## Final Response

Your final response must include:

- files read;
- files changed;
- findings by severity;
- repairs made;
- tests run and exact outcomes;
- remaining risks;
- merge recommendation.

## Success Bar

This task is complete only if Codex can use your report to make a merge decision quickly and can trust that you challenged Kimi's work instead of rubber-stamping it.
