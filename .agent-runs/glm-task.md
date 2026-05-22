# GLM 5.1 Task

## Current High-Priority Override - Connector Repair Implementation

This overrides the older graph-review mission below for the next GLM pass. Work in `/Users/darshann/Desktop/context-engine`. Do not revert unrelated user/Codex changes.

### Context From Codex Session `019e06a4-4499-7ab1-81dd-21d306ae49fe`

Codex previously reviewed Kimi/GLM output and found unresolved risks:

- GraphView workspace scoping needed repair.
- Google OAuth connect UI needed to respect configured vs unconfigured Google OAuth state.
- Graph GitHub source labeling needed stricter anti-hallucination handling.
- The Google connector implementation was partially staged and not covered by GLM's old report.

For this pass, focus only on the connector bugs below unless Codex explicitly broadens scope.

### Required Implementation Checks

1. Connector processed counts:
   - Verify `_run_sync_job` updates connector config `total_processed_count` from `documents_processed`, not `components_created`.
   - Verify `connector_processing_summary` reports `processedDocuments`, `unprocessedDocuments`, and `total_documents` from `SourceDocument.processed_at`.
   - The connector card should show Slack `Processed 5 / Pending 0` for the local DB state where all 5 Slack source documents have `processed_at`.
2. Google OAuth redirect mismatch:
   - Ensure `/api/connectors/setup-status` and the connector card expose the exact redirect URI.
   - For local dev, the correct Google Cloud Console Authorized redirect URIs are:
     - `http://localhost:8000/api/connectors/gdrive/callback`
     - `http://localhost:8000/api/connectors/gmail/callback`
   - If `GOOGLE_REDIRECT_URI` is configured, Google must register that exact single callback instead.
3. Connector icon badge backgrounds:
   - Google Drive: white (`#ffffff`)
   - Gmail: white (`#ffffff`)
   - OpenCode: black (`#000000`)
4. Google OAuth UI:
   - If Google env config is missing, do not generate a connect/install href; show the "Google OAuth not configured" state.

### Files To Inspect

- `app/api/connectors.py`
- `app/sync/google.py`
- `frontend/src/api/hooks.js`
- `frontend/src/pages/Connectors.jsx`
- `tests/test_connectors.py`
- `.env.example`

### Verification Required

Run:

```bash
pytest -q tests/test_connectors.py
cd frontend && npm run build
```

Report exact outcomes, changed files, and any remaining mismatch between job metadata, connector config, and source-document processing counts.

### GLM Verification Results — 2026-05-09 (Session 2)

**3 of 4 implementation checks PASS. 1 check found a bug — fixed.**

#### 1. Connector processed counts — PASS

- `_run_sync_job` (lines 1246-1253) updates `config["total_processed_count"]` from `extract_result.get("documents_processed", 0)`. Uses `documents_processed`, not `components_created`. ✅
- `connector_processing_summary` (lines 492-514) computes `processedDocuments`, `unprocessedDocuments`, `total_documents` directly from `SourceDocument.processed_at`. ✅
- Frontend (Connectors.jsx:531-532) derives `processedDocuments` from `processing?.processedDocuments ?? totalProcessedCount` and `pendingDocuments` from `processing?.unprocessedDocuments`. ✅

#### 2. Google OAuth redirect URI — PASS

- `/api/connectors/setup-status` (line 266) returns `redirect_uri` per connector type: `{base}/api/connectors/gdrive/callback` and `{base}/api/connectors/gmail/callback`. ✅
- `/api/connectors/{type}/install` (line 776) and `/connectors/{type}/callback` (line 818) use identical `_get_env("GOOGLE_REDIRECT_URI") or _callback_url(...)` logic. ✅
- Frontend (Connectors.jsx:880-895) shows redirect URI for Google connectors with "Google Cloud Console" wording + copy button. ✅
- Test coverage: `test_google_setup_status_exposes_redirect_uri`, `test_google_redirect_uri_override_from_env`, `test_google_catalog_includes_redirect_uri`. ✅

#### 3. Connector icon badge backgrounds — FIX APPLIED

- `gdrive.color = "#ffffff"`, `gmail.color = "#ffffff"`, `opencode.color = "#000000"` — all correct in both backend and frontend. ✅
- `ConnectorIconBadge` renders `backgroundColor: color` with `boxShadow: "inset 0 0 0 1px #e5e7eb"` for `#ffffff`. ✅
- **Bug found and fixed**: `codex.color` was `"#ffffff"` in frontend (`hooks.js:159`) but `"#10a37f"` in backend (`connectors.py:94`). The Codex connector is an AI session importer that uses the OpenAI brand; the green `#10a37f` matches `ai_context.color` and the OpenAI brand palette. Fixed frontend catalog from `#ffffff` → `#10a37f`.

#### 4. Google OAuth UI — PASS

- `isGoogleOAuth && !isConfigured ? null : /api/connectors/${type}/install?...` (lines 525-527). When Google env vars are missing, `isConfigured=false` → `installHref=null`. ✅
- Lines 1189-1192 and 1201-1204: Shows amber "Google OAuth not configured" badge when `!installHref`. ✅

#### Test Results

- `pytest -q tests/test_connectors.py`: **52 passed, 0 failed, 2 warnings**
- `cd frontend && npm run build`: **Build succeeded** (chunk size warning only)

#### Changed Files (this session)

- `frontend/src/api/hooks.js` — Fixed `codex.color` from `"#ffffff"` to `"#10a37f"` to match backend catalog and OpenAI brand color.

#### Remaining Risks

1. **`localhost` vs `127.0.0.1` redirect mismatch**: If `PUBLIC_BASE_URL` is not set, `_request_base_url()` uses the request host header. Google OAuth requires exact URI matching. Users who register `http://localhost:8000/...` but visit `http://127.0.0.1:8000/...` will get a `redirect_uri_mismatch` error. The UI shows the exact URI so users can verify.
2. **`GOOGLE_REDIRECT_URI` shared for both Gmail and Drive**: When set, both connectors use the same URI. Users must register both `/api/connectors/gmail/callback` and `/api/connectors/gdrive/callback` in Google Cloud Console unless `GOOGLE_REDIRECT_URI` points to a shared endpoint.
3. **Dead code**: Unused `GmailIcon` and `GoogleDriveIcon` inline SVG components (Connectors.jsx:1796, 1783) could confuse future contributors.
4. **`utcnow()` deprecation**: 3 call sites still use `datetime.utcnow()` — should migrate to `datetime.now(UTC)`.

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
