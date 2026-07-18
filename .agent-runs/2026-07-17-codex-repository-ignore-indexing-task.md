# Codex task — repository ignore-aware indexing

## Objective

Prevent ignored generated output from consuming repository indexing safety
limits while preserving tracked and non-ignored project source.

## Observed

- The indexer walked the whole filesystem tree and applied only a small
  hard-coded directory denylist.
- It did not consult Git ignore rules.
- The stock-radar repository contained a 1.5 GB `web/.next` directory. Although
  individual files above 400 KB were skipped, 1,222 smaller generated candidates
  still contributed 58.5 MB and tripped the 50 MB cap.
- Excluding generated directories left 211 real candidates totaling 2.4 MB.

## Contract

- Prefer `git ls-files --cached --others --exclude-standard` for valid Git
  repositories.
- Fall back to filesystem traversal only when Git enumeration is unavailable.
- Apply known generated-directory exclusions in both modes as defense in depth.
- Do not weaken the existing file-count, per-file, aggregate-byte, or symlink
  protections.

## Verification

- `pytest -q tests/test_repo_indexer.py` — 20 passed.
- `pytest -q` — 564 passed with one existing Python 3.13 SQLite deprecation
  warning.
- `ruff check .` — passed.
- `git diff --check` — passed.
- Read-only scan of `/Users/darshann/Desktop/OLD Proj/stock-radar` — 210
  candidates, 2,429,172 bytes, zero `.next` candidates.

## Implemented

- Git repositories use tracked plus non-ignored untracked files as their input
  boundary.
- Files that are ignored but already tracked remain eligible unless they live in
  a known generated directory.
- Filesystem fallback excludes common framework, language, test, coverage, and
  build output directories.
- The 5,000-file, 400 KB-per-file, 50 MB aggregate, and symlink protections are
  unchanged.

## Remaining gaps

- The product does not yet display an exclusion report or offer per-workspace
  ignore overrides. Those are separate UX features, not required to unblock
  correct indexing of this repository.
