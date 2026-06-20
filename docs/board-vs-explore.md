# Board Vs Explore

The graph UI has two modes with different jobs. Board is the default because it
helps users understand the project by source family. Explore is for following
connections around a selected node.

## Board

Board answers: "What context do we have, and where did it come from?"

Behavior:

- Default graph mode and URL state.
- Source-first clusters such as GitHub, Slack, Gmail, AI, and Local.
- Uniform cards around 220px wide.
- Labels use source grammar, for example `Issue #12: ...`, `PR #11: ...`, and
  `Slack: ...`.
- Edges stay quiet by default; labels reveal on hover or selection.
- Refine drawer controls filters and lens presets.
- Lens presets include All, Work, Decisions, and Gaps.
- Cmd+K focuses graph search.
- Minimap helps navigation without adding canvas noise.

Board should not add Input, KB, LLM, or Output nodes to the knowledge graph. Those
belong in dashboard or documentation surfaces, not in project memory.

## Explore

Explore answers: "What is connected to this fact?"

Behavior:

- Force layout with logo-in-circle nodes.
- Physics runs briefly and then freezes.
- Orphans are hidden by default.
- Search dims non-matching nodes.
- Local graph panel supports 1-hop and 2-hop context.
- "Open in Board" returns to source-cluster comprehension around the selection.

Explore should feel closer to an Obsidian-style local graph than a workflow
canvas. It is not a pipeline builder.

## Inspector

Both modes rely on the right-rail inspector for trust detail:

- Component value and source excerpt.
- Provenance and source metadata.
- Source links when available.
- Status, temporal state, confidence, and authority.
- Connected relationships.
- Edge origin, confidence, evidence, and approve/reject actions.

The canvas should stay quiet; the inspector carries the loud trust metadata.

## Trust Mode

Default edge styling should be restrained. Trust mode can reveal relationship
origin more explicitly:

| Origin | Meaning |
|---|---|
| `deterministic` | Parsed from structured source evidence such as GitHub issue/PR links. |
| `extracted` | Extracted from source content with conservative rules. |
| `human_verified` | Accepted or verified by a user. |
| `ai_proposed` | Proposed by AI and needs review. |
| `proposed` | Low-certainty or pending relationship. |

Do not use color intensity to imply certainty for proposed edges.
