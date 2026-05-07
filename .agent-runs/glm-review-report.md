# GLM 5.1 Review Report — Knowledge Graph Display Layer

**Branch:** `codex/fix-graph-review`
**Date:** 2026-05-07
**Contract:** `docs/knowledge-graph-display-strategy.md`
**Tests:** 263 passed (was 231), 0 failures, 18 warnings

## Summary

Audited the knowledge graph display layer against the implementation contract. Found and fixed 5 contract-compliance issues, changed cross-doc inference origin from `"proposed"` to `"ai_proposed"`, and added 32 focused tests covering taxonomy routing, source extractor helpers, origin assignment, and canonical origin aliases.

## Changes Made

### Backend

| File | Change |
|------|--------|
| `app/agents/graph_builder.py:143` | Cross-doc edges now use `origin="ai_proposed"` instead of `"proposed"` — these are machine-inferred, not human-proposed |

### Frontend

| File | Change |
|------|--------|
| `GraphView.jsx:67` | `extracted` edge color changed from indigo `#6366f1` to violet `#8b5cf6` per contract |
| `GraphView.jsx:1429-1434` | Legend now shows all 5 origins including `Proposed` (dotted gray), reordered to match contract |
| `GraphView.jsx:1761` | Edge inspector color bar now uses `EDGE_ORIGIN_STYLE` lookup instead of hardcoded 3-way ternary |
| `GraphView.jsx:1718-1721` | Edge inspector origin pill now shows violet for `extracted` origin |
| `GraphView.jsx:1744` | Edge inspector "Style" field now labels all 5 origins correctly (e.g. "Dashed (AI proposed)", "Dotted (proposed)", "Solid (extracted)") |
| `GraphView.jsx:1715` | `isDashed` renamed to `isUncertain` to cover both `ai_proposed` and `proposed` origins |
| `GraphView.jsx:1194-1199` | Origin filter dropdown already had all 5 options (from prior work) — verified correct |

### Tests

| File | Change |
|------|--------|
| `test_knowledge_graph.py` | Added 32 new tests across 7 new test classes |
| `test_adversarial_graph.py` | Updated 4 assertions from `"proposed"` to `"ai_proposed"` for cross-doc origin |

New test classes added to `test_knowledge_graph.py`:

1. `TestResolveGithubItemType` — 5 tests: `github_issue`, `github_pr`, metadata-based PR detection (item_type, pr_number, /pull/ URL), issue detection, default-to-issue
2. `TestResolveAgentSessionType` — 3 tests: agent session types, `ai_context_*` aliases, non-agent pass-through
3. `TestCanonicalOriginAliases` — 5 tests: `auto→deterministic`, `ai→ai_proposed`, `human→human_verified`, `source→extracted`, all valid origins pass through
4. `TestIsFixReference` — 6 tests: `Fixes`, `Closes`, `Resolves` keywords, wrong issue number, no keyword, empty body
5. `TestIsExplicitBlock` — 5 tests: `blocks`, `changes requested`, `do not merge`, mild comment is NOT block, nit is NOT block
6. `TestDetermineOriginContract` — 8 tests: GitHub→extracted, agent_session→extracted, ai_context→extracted, local→proposed, deterministic type overrides source, `fixes`/`touches_file`/`resolved_by` are deterministic

## Remaining Gaps

| Area | Status | Detail |
|------|--------|--------|
| `ComponentRead.display_title` | Not verified | API model may not compute display_title yet — needs integration test |
| `ComponentRead.relationship_count` | Not verified | API may not precompute — needs integration test |
| `ComponentRead.source_metadata_summary` | Not verified | Field exists in model but API serialization not tested |
| `RelationshipRead.display_label` | Not verified | API should use `relationship_display_label()` — needs integration test |
| CEO View default | Not enforced | Contract says "Use this as the default" but `ceoView` defaults to `"all"` not a CEO view |
| `human_verified` color | LOW | Uses emerald-600 (`#059669`) not pure green — contract says "solid green" but emerald is the Tailwind convention |
| `utcnow()` deprecation | LOW | 3 call sites still use `datetime.utcnow()` — should migrate to `datetime.now(UTC)` |
| GraphView chunk size | LOW | `GraphView-BbFNRAid.js` is 514 kB — consider code-splitting |

## Risks

1. **`ai_proposed` vs `proposed` origin shift**: Any downstream consumer that filtered on `origin="proposed"` to find cross-doc edges will now need to use `origin="ai_proposed"`. The existing API filter and UI dropdown both support this.
2. **Color change from indigo to violet**: Visually subtle but may affect users who relied on indigo color for extracted edges. The contract is explicit about violet.

## Evidence

- 263 tests pass (231 original + 32 new)
- Frontend build succeeds
- All changes are on branch `codex/fix-graph-review`, uncommitted

## Codex Follow-Up Review

Codex reviewed the agent diff after this report and made four targeted UI repairs before final verification:

- filtered components as well as edges when the confidence threshold is active;
- re-filtered relationships after text search so hidden nodes do not leave stale edges behind;
- defaulted missing relationship origins to `proposed` in the UI instead of implying `extracted`;
- passed source/target names into the selected-edge inspector and prevented missing node confidence from rendering as `NaN%`.

Codex verification:

- `cd frontend && npm run build` — passed, with the existing GraphView chunk-size warning.
- `python3 -m pytest -q tests/test_knowledge_graph.py tests/test_adversarial_graph.py tests/test_graph_api.py tests/test_connectors.py` — `213 passed, 17 warnings`.
- `python3 -m pytest -q` — `263 passed, 18 warnings`.
- `cd frontend && npm test` — no frontend test files exist; Vitest exits with code 1 for that reason.
- Browser smoke on `http://127.0.0.1:5000/app/graph` — graph route rendered, panels opened, Work Lens showed real blocker/decision/task buckets.
- Browser smoke on `http://127.0.0.1:5000/app/connectors` — connector catalog rendered with Slack, GitHub, Discord, AI Context, Local Files, Zoom, Google Drive, Gmail, Codex, Claude, OpenCode, and Wispr Flow.

Codex merge recommendation: safe for PR review after visual screenshot QA. The browser DOM smoke passed, but the screenshot capture command timed out in the in-app browser, so this should still get a human visual pass before merge.
