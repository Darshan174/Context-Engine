# Evidence Graph Route

`/app/graph` is the selected-workspace evidence graph. It is a projection over
imported `SourceDocument` revisions; it is not a provider client and it is not a
workspace objective generator.

## Observed behavior

- A compact command bar names the selected workspace and reports the visible
  record/relationship count without permanently covering the canvas.
- The objective is a distinct task-focus anchor when one has been supplied. When
  it has not, the anchor says so and does not infer intent from imported history.
- Individual source-backed records are arranged into `Sources`, `Intent`,
  `Delivery`, and `Risk & verification` lanes. Lanes are navigation structure,
  not factual relationships.
- `Update graph` processes pending current source revisions.
- `Rebuild` re-extracts the current imported revisions and reconciles their
  derived components. It lives in the graph-actions menu, with the longer
  snapshot explanation and scope/freshness detail hidden until requested.
  Historical source revisions remain addressable.
- Neither graph action contacts GitHub or another provider. `Refresh sources`
  is a separate connector operation.
- Pull requests and issues appear in their named panels only when backend
  classification has typed provider metadata. Their state is described as an
  observation at the last successful sync, not as live state.
- An AI-session card represents one imported session root. It shows its tool,
  stable session identifier, available repository/cwd and branch context,
  timing/message metadata, and workspace-relevance status.
- Decisions and blockers require a typed component plus exact source evidence.
  Agent-session suggestions remain supporting evidence unless explicitly
  confirmed by a human source.
- The document-finding panel remains explicitly unverified until a structured
  document-health extractor emits a supported finding.
- Selecting a record quiets unrelated records, labels its local relationship
  paths, and opens the inspector. The inspector shows classification,
  status, source snapshot, evidence excerpt, session/provider metadata,
  visible factual relationships, and the imported source content.

## Relationship display

The canvas draws only links included by the backend digest. The backend includes
only deterministic, extracted, or human-verified relationships that contain
evidence. Proposed relationships are not drawn as facts. Relationship-connected
records receive visual priority when the 24-node canvas budget is exceeded; the
number of lower-priority hidden records remains visible.

Edges remain quiet until a record is selected. The selected record's one-hop
neighborhood stays prominent and relationship labels become visible. Blocking
and contradiction edges use the risk color; other factual edges remain neutral.

## Interaction and accessibility

- Pointer pan and pinch/wheel zoom stay inside the graph surface.
- `+`/`-` zoom, `0` reset, arrow-key pan, fit, and reset controls are available
  when the graph region
  has focus.
- Evidence records and graph actions are keyboard selectable. `Escape` clears a
  local focus or closes graph popovers.
- Mobile opens centered between the Intent and Delivery lanes while preserving
  pan access to the complete evidence surface.
- The desktop application sidebar can collapse to its icon rail while keeping
  accessible navigation names and workspace/theme access.

## Not implemented yet

- A live provider-state stream inside the graph.
- Automatic repository matching for every imported session. Missing comparable
  metadata is reported as `Relevance unverified`.
- A validated broken-document crawler.
- A server-authored `task_map.v1` projection with compiler selection/exclusion and
  explicit gap nodes. The current client projection consumes the evidence digest,
  sourced objective, and factual links.
- Multi-hop path controls beyond the current one-hop selection focus.

## Anti-hallucination rules

- Do not classify panels from title keywords or URL regexes in the frontend.
- Do not call a graph-row lifecycle status a GitHub provider state.
- Do not call a provider snapshot current without a successful sync timestamp.
- Do not display historical source revisions as current projection rows.
- Do not infer an objective from sessions, issues, PRs, graph topology, or
  attention ranking.
- Do not promote an assistant recommendation to a workspace decision without
  explicit human confirmation.
