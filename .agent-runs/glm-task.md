# GLM 5.1 Task

## Role

You are GLM 5.1 working in `/Users/darshann/Desktop/context-engine`.

You are the primary senior implementation engineer for the 20x knowledge-graph round. Your job is to implement the source-backed graph contract and graph display so users can understand the project at a glance from connectors, GitHub, repositories, and AI workload sessions.

## Non-Negotiable Rules

- Do not work on connector OAuth/provider authentication unless a graph source-type bug requires touching source-document creation. If you must touch connector code, limit it to metadata/source-document shape and document why.
- Do not create fake graph edges.
- Do not infer relationships from broad word overlap.
- Do not make proposed AI edges look like confirmed truth.
- Do not remove existing user changes.
- Do not hallucinate current behavior. Verify before editing.
- Preserve provenance for every component and relationship.
- Every persisted relationship must have evidence. Prefer direct source quotes or deterministic rule evidence over template evidence.
- Keep SQLite compatibility and use the existing lightweight migration style unless the repo already has a stronger migration system.

## Required Inputs

Read Kimi's strategy first if present:

- `docs/knowledge-graph-display-strategy.md`

Then verify against the repo yourself. Do not trust the strategy blindly.

Read these files before editing:

- `AGENTS.md`
- `app/models.py`
- `app/taxonomy.py`
- `app/services/ingest.py`
- `app/processing/extractor.py`
- `app/processing/source_extractors.py`
- `app/sync/github.py`
- `app/sync/ai_session.py`
- `app/importers/ai_context.py`
- `app/api/graph.py`
- `app/api/connectors.py` only for source-document creation and source-type metadata
- `app/agents/graph_builder.py`
- `app/agents/gap_detector.py`
- `app/agents/relationship_agent.py`
- `app/agents/context_pack.py`
- `frontend/src/pages/GraphView.jsx`
- `frontend/src/api/hooks.js`
- `tests/test_knowledge_graph.py`
- `tests/test_adversarial_graph.py`
- `tests/test_graph_api.py`
- `tests/test_ingestion.py`
- `tests/test_agents.py`

## Mission

Implement the robust knowledge graph and display layer for:

- models
- components
- relationships
- GitHub issues
- GitHub PRs
- repos/files/changed modules
- source documents from connectors
- AI workload sessions from Codex, Claude, OpenCode, and compatible tools
- graph agents and context-pack workflows

The final UI must quickly answer:

- What is happening in this project?
- What is blocked?
- What decisions are open or already made?
- What tasks are active?
- Which issues and PRs relate to those tasks?
- Which files/repos are touched?
- Which AI sessions produced the work?
- Which connector/source produced the evidence?
- Which relationships are deterministic, extracted, proposed, human verified, or stale?

## 20x Workload

### 1. Canonical Source-Type Normalization

Fix source-type drift so real synced/imported documents route to the correct extractors.

You must verify and harden:

- GitHub issue source documents route to GitHub issue extraction.
- GitHub PR source documents route to GitHub PR extraction.
- Existing `source_type="github"` documents use metadata such as `item_type`, `source_type`, or external ID to choose issue vs PR extraction.
- AI sessions from `codex`, `claude`, `opencode`, `agent_session`, and older `ai_context_*` source types route to the AI session extractor or an explicit compatibility path.
- Graph filters and display labels use one canonical display vocabulary even if legacy rows exist.

Do not break existing connector tests or source imports.

### 2. Canonical Vocabulary

Harden the vocabulary in `app/taxonomy.py` and related tests.

Support at minimum:

Models:

- `Agent Session`
- `Context Pack`
- `Decision`
- `Document`
- `Feature`
- `GitHub`
- `Issue`
- `Metric`
- `Person`
- `PR`
- `Repo`
- `Risk`
- `Task`
- `Team`

Fact types:

- `github_issue`
- `github_pr`
- `pr_review_finding`
- `commit_reference`
- `changed_file`
- `ai_session`
- `ai_task`
- `ai_decision`
- `ai_blocker`
- `open_question`
- `decision`
- `task`
- `blocker`
- `risk`
- `feature`
- `metric`
- `fact`

Relationship types:

- `fixes`
- `resolved_by`
- `implements`
- `implemented_in`
- `touches_file`
- `blocks`
- `blocked_by`
- `depends_on`
- `conflicts_with`
- `supersedes`
- `duplicates`
- `mentions`
- `discussed_in`
- `generated_by_agent`
- `created_from`
- `verified_by_human`
- `part_of`
- `related_to`

Relationship origins:

- `deterministic`
- `extracted`
- `ai_proposed`
- `human_verified`

If you choose different canonical names, justify them and update backend, frontend, and tests consistently.

### 3. GitHub Issue/PR Extraction

Implement or harden deterministic extraction for GitHub issues and PRs.

Issues must support:

- title
- body
- state
- labels
- assignees
- milestone
- comments when present
- source URL
- repo full name
- issue number

PRs must support:

- title
- body
- state
- merged state
- linked issues
- review comments/findings
- changed files
- source URL
- repo full name
- PR number

Required deterministic edges:

- PR `fixes` Issue when body/title explicitly says `fixes #N`, `closes #N`, `resolves #N`, or equivalent.
- Issue `resolved_by` PR as inverse when resolvable.
- PR `touches_file` Repo/File component for changed files.
- Review finding `blocks` PR only when review text explicitly requests changes, blocks merge, or identifies a concrete issue.
- PR `implements` Task/Decision only when explicit.
- Duplicate links only when explicit.

Do not create issue/PR relationships from generic shared words.

### 4. AI Workload Session Extraction

Implement or harden AI session extraction for Codex, Claude, OpenCode, and compatible markdown/session imports.

Required components:

- session root under `Agent Session`
- actionable tasks from checklists, TODOs, next steps, or implementation plans
- decisions from explicit decision/recommendation/verdict/final-summary sections
- blockers/risks from failed tests, review findings, unresolved questions, or explicit blockers
- changed/touched file references when source text includes file paths
- context-pack candidates when session clearly prepares handoff context

Required relationships:

- task/decision/risk `generated_by_agent` session root
- changed file `discussed_in` or `generated_by_agent` session root if source-backed
- task `depends_on` blocker only when explicit

Skip:

- generic acknowledgements
- vague narration
- broad summaries without source evidence
- duplicate task restatements
- low-specificity claims

### 5. Relationship Safety

Harden relationship persistence.

Requirements:

- skip self-loops
- skip duplicates
- skip confidence below threshold
- skip stale/deleted target components unless explicit historical relationship is required
- require non-empty evidence
- label evidence quality where evidence is template/generated rather than direct quote
- store and return origin consistently
- never promote AI proposed relationships to deterministic based only on confidence

GraphBuilder cross-document inference must produce only proposed/candidate edges with clear evidence explaining why they are weak, or remain disabled by default.

### 6. Graph API Contract

Make the API response self-describing enough that the frontend never guesses.

Ensure graph/list/detail/slice/diff/work-lens responses expose:

- component id
- model id/name
- component name
- display title
- value
- fact type
- source document id
- source type
- source URL
- source external id
- source metadata summary
- provenance
- excerpt/evidence excerpt
- confidence
- temporal
- status
- relationship count
- relationship id
- source/target component ids and names where useful
- relationship type
- display label
- relationship evidence
- relationship confidence
- relationship status
- relationship origin
- created/ingested timestamps where useful

Fix any Pydantic response-model mismatch caused by returning fields not declared in response models.

Endpoints to harden or add:

- `GET /api/graph`
- `POST /api/graph/slice`
- `GET /api/components/{id}`
- `GET /api/relationships/{id}`
- `GET /api/source-documents/{id}/diff`
- `GET /api/work-lens`
- context-pack-from-selection endpoint, if the existing context pack agent can support it cleanly

### 7. Frontend Graph Display

Engineer `frontend/src/pages/GraphView.jsx` or adjacent components into a project command map.

Default view:

- current, high-confidence, non-stale knowledge first
- blockers, open decisions, active tasks, PRs/issues, repos/files, AI sessions visible in a structured layout
- proposed/weak relationships hidden or visually secondary by default

Required views:

- `All`
- `Bird's Eye`
- `Gap Detector`
- `Decision Trail`
- `AI Sessions`
- `Work Lens`
- `GitHub Delivery`
- `Repository`

Required UI behavior:

- model filter
- source-type filter
- status filter
- temporal filter
- confidence filter
- relationship origin filter
- edge type filter if useful
- selected-node inspector with evidence/provenance/source metadata
- selected-edge inspector with evidence/confidence/origin/status
- source-to-knowledge diff panel
- work-lens panel
- AI sessions panel that shows session -> generated work -> touched files/PRs/issues
- GitHub panel that shows issue -> PR -> files -> decisions/tasks
- visual distinction:
  - deterministic: solid, high-trust
  - extracted: solid but less dominant
  - ai_proposed: dashed/candidate
  - human_verified: verified/highlighted
  - stale/deprecated: muted
  - missing evidence: warning style

Do not make the page decorative. Prioritize scanability, density, evidence, and trust.

### 8. Tests

Add or update focused tests.

Backend tests must cover:

- GitHub issue extraction from real-ish JSON
- GitHub PR extraction from real-ish JSON
- legacy `source_type="github"` routing to issue/PR based on metadata
- PR `fixes` issue deterministic edge
- inverse issue `resolved_by` PR edge when resolvable
- PR `touches_file` edge
- review finding blocks PR only when explicit
- AI session extraction for Codex-like markdown
- AI session extraction for Claude/OpenCode source-type aliases
- session root -> generated task/decision/risk relationships
- no relationships from unrelated shared words
- evidence required for all persisted relationships
- origin values stay canonical
- graph API includes display metadata
- source diff endpoint returns components and relationships
- work lens categorizes blockers/decisions/tasks
- stale items do not appear as active project work

Frontend verification:

- `npm run build`
- If feasible, run a local UI smoke test and capture screenshots or describe exact API payload tested.

### 9. Verification Commands

Run at minimum:

```bash
pytest -q tests/test_knowledge_graph.py tests/test_adversarial_graph.py tests/test_graph_api.py tests/test_ingestion.py tests/test_agents.py tests/test_migrations.py
```

Run full suite if practical:

```bash
pytest -q
```

Run frontend build if frontend changed:

```bash
cd frontend && npm run build
```

If full `pytest -q` fails because of unrelated connector tests, document exact failures and prove graph-specific suites pass.

## Deliverables

Final report must include:

- files changed
- graph behavior changed
- canonical source types supported
- canonical fact types supported
- canonical relationship types supported
- canonical relationship origins supported
- backend API changes
- frontend UI changes
- tests added
- tests run
- build result
- known risks
- anything left for Codex final review

## Final Review Expectation

After your work, Codex will review it brutally. Expect review to check:

- whether source types actually route correctly
- whether relationships are evidence-backed
- whether origin semantics are consistent
- whether UI hides weak/proposed edges appropriately
- whether graph API and frontend agree
- whether tests prove the important behavior
- whether any connector/OAuth work leaked into this task
