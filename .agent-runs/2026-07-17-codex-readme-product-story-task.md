# Codex task — product README story

## Objective

Rewrite the README product narrative so a builder immediately understands the
problem, the change in daily AI usage, the current product loop, and the model
efficiency thesis. Keep Setup, Deployment, Contributing, Documentation, and
License unchanged.

## Observed

- The existing README was accurate but led with a category description rather
  than the cost users feel when coding sessions lose project state.
- The strongest company thesis, getting more useful work from older or cheaper
  models through better context and execution, appeared late in the harness
  section.
- The README listed features but did not make the before/after workflow vivid.

## Contract

- Use short sentences, concrete nouns, and product language a founder would
  naturally write.
- Describe implemented behavior only.
- State model-lift as the product thesis being measured, not a proven result.
- Keep the setup and OSS-readiness tail byte-for-byte unchanged.

## Verification

- Capability claims were checked against the current goal, context compiler,
  harness, run evidence, graph, connector, API, CLI, and MCP implementations.
- Setup through License is byte-for-byte unchanged from the branch base.
- Every local README link resolves.
- `git diff --check` passed.
