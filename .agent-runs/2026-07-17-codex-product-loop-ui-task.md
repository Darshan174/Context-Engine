# Codex Integration Task — Product Loop UX (complete)

## Objective

Integrate the existing project digest, context compiler, local harness outcomes,
and evidence graph into a clear product-facing workflow.

## Contract

- `/app` answers what is happening now and what the user should do next.
- `/app/prepare` compiles a real persisted `context_pack.v2`; it does not pretend
  to deliver the pack to an agent automatically.
- `/app/runs` displays only local-harness-observed outcomes and makes the paired
  baseline gap explicit.
- `/app/explain` retains the inspectable project map and maps relationship meaning
  to distinct geometry or line treatment.
- Sources and connectors remain available as supporting evidence/configuration
  surfaces.
- Workspace and source-access boundaries are enforced before outcome data is
  serialized.
- Existing unrelated working-tree edits are preserved.

## Required verification

- Focused backend tests for outcome serialization and access scoping.
- Focused frontend tests for routing, preparation, run states, and semantic graph
  rendering.
- Full frontend test suite and production build.
- Relevant backend suite, Ruff, `git diff --check`, and live desktop/narrow UI
  inspection.

## Required final report

Changed files, tests run, implementation evidence, risks, and remaining gaps.
