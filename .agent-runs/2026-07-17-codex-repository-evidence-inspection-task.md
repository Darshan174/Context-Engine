# Codex Integration Task — Repository Evidence Inspection (complete)

## Objective

Make deterministic repository matches and selected-record evidence understandable
without presenting heuristic suggestions as confirmed implementation scope.

## Contract

- Preserve existing compiler, repository index, source provenance, and `OpenLoop`
  persistence contracts.
- Expose why a file matched and distinguish named, strong, possible, and linked
  test matches.
- Prefer provider state and source freshness over internal extraction labels.
- Keep file suggestions bounded and explicitly advisory.

## Verification

- Focused context-compiler and repository-indexer tests.
- Full frontend tests and production build.
- Focused Ruff checks and `git diff --check`.
