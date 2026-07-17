# Codex task — explicit goals, workspace lifecycle, realistic project validation

## Objective

Implement the ordered product corrections identified during the Now/workspace
audit: explicit current goals, urgent-attention versus backlog semantics,
workspace lifecycle management, repo-first onboarding, and a realistic external
project validation path.

## Observed before implementation

- The Now page inferred Current goal from the newest old context pack that had a
  focus component, even when newer prepared objectives had no focus component.
- The selected Context engine workspace explicitly tracked this repository and
  included one AI session whose repository relevance was unknown.
- Every unresolved issue category was rendered under Needs attention.
- Workspace creation accepted only a name; rename, archive, and delete were not
  implemented, while GET `/workspaces` could create a Default workspace.
- Demo and real workspaces were indistinguishable in the native selector.

## Slice 1 contract

- Add durable workspace-goal history with at most one active selection.
- Active agent runs override a stored selection only while actually active.
- Context packs remain preparation artifacts and never imply current work.
- Add set/clear goal endpoints with workspace and source access validation.
- Add `attention_required` and a Backlog digest cluster so open issues are not
  presented as urgent by category alone.
- Give Now explicit choose/change/clear controls, visible provenance, a separate
  suggestion, and selectable backlog.

## Remaining slices

- Workspace lifecycle API and management surface.
- Repo-first onboarding, sample separation, and unassigned-session handling.
- Full realistic-project walkthrough using a user-supplied external repository.

## Verification record

- Focused backend goal/digest/migration tests: 55 passed.
- Full backend suite: 557 passed with one existing Python 3.12 SQLite warning.
- Focused frontend product-loop tests: 4 passed; full frontend suite: 80 passed.
- Production frontend build, Ruff, and `git diff --check`: passed.
