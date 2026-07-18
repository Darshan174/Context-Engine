# Codex task — product-loop and trust hardening

## Objective

Close the smallest honest product loop across current work, compiled context,
observed execution, and inspectable evidence while removing confirmed release
blockers.

## Observed

- Backend context packs are durable, but the product treats each compile result
  as ephemeral.
- Goal selection, compilation, and run observation use compatible records but
  do not preserve one stable goal identity through the default UI workflow.
- Several interfaces hide evidence or destinations despite source-backed trust
  being the central product promise.
- PDF upload, mobile navigation, zoom policy, and connector-run routing expose
  behavior that is broken or misleading.

## Contract

- Keep source claims explicit and provenance-preserving.
- Do not invent PDF extraction or run/provider automation that is not present.
- Persist and expose pack artifacts using existing workspace access controls.
- Carry current goal identity into compiled packs and derive latest results only
  from runs linked to those packs.
- Keep Now concise while providing complete attention/backlog destinations.
- Add focused backend/frontend regressions before full verification.

## Verification

- `pytest -q`: 566 passed, one existing Python/SQLite deprecation warning.
- `npm test`: 92 passed.
- `npm run build`: production build passed.
- `ruff check .`: passed.
- `git diff --check`: passed.
- Live desktop/mobile browser checks were not completed in this slice.

## Implemented

- Durable context-pack list/detail APIs and a Prepare history/reopen/download UI.
- Full per-item inclusion and exclusion inspection with available provenance,
  trust, revision, citation, and source links.
- Stable workspace-goal identity on context packs and goal-linked harness
  outcome summaries.
- Honest PDF rejection, restored browser zoom, usable mobile navigation, and a
  real connector run-history route.

## Remaining gaps

- Complete attention/backlog browsing and evidence inspection from Now.
- A guided in-product harness flow beyond the existing CLI-first Runs surface.
- Context-pack diffing and live browser QA.
