# Deterministic Project Compiler Contract

Status: P1 baseline implemented on 2026-07-14. Items explicitly labelled as a
follow-on, backlog, or "Not implemented yet" remain future work.

This contract adds one factual repository-structure layer beneath focused task
preparation:

`working-tree snapshot -> incremental file/symbol index -> exact edges -> affected code`

It does not claim exhaustive codebase understanding. A file is shown only when an
existing objective match or a supported deterministic edge supplies the reason.

## Observed baseline before P1

- `RepoIndexer.inspect_repo()` scans a bounded working tree, records Git branch,
  HEAD, dirty paths and content hashes, and extracts Python plus
  JavaScript/TypeScript symbols, imports and route hints
  (`app/services/repo_indexer.py`).
- `RepoIndexer._persist_frame()` deleted all `CodeFile` and `CodeSymbol`
  rows for the repository root and recreates them. Repeated unchanged indexing
  therefore changes their UUIDs (`app/services/repo_indexer.py`).
- `CodeFile` had repository root, path, content hash and `last_commit` fields, but
  `(workspace_id, repo_root, path)` is not unique. `CodeSymbol` belongs to one
  file. `CodeEdge` connects two symbols and stores only `edge_type`; it has no rule,
  source location, snapshot or evidence fields (`app/models.py`).
- Production indexing did not create `CodeEdge` rows. Existing migration tests
  only prove that a manually created `references` edge round-trips
  (`tests/test_migrations.py`).
- `RepoFrame.relevant_files_for_goal()` returned at most 16 ranked files with an
  internal reason code, matched terms, line ranges, hash and test flag. Its
  fallback can include changed files, tests and manifests even without an
  objective match (`app/services/repo_indexer.py`).
- `ContextCompiler` placed that list under `manifest.repo_state.relevant_files`
  and turns entries into file candidates. Markdown currently says a file is
  relevant because of the internal reason value; related tests and deterministic
  impact paths are absent (`app/services/context_compiler.py`).
- The focused-card inspector already owned task preparation and the source-backed
  run timeline. Timeline events can show observed files, but the prepared pack's
  likely implementation files are not a distinct UI section
  (`frontend/src/context-map/components/ContextInspector.jsx`,
  `app/services/founder_oversight.py`).
- `/api/repo/index` enforced one active local repository root per workspace and
  creates a source-first `local_repository` inventory revision. Its response
  reports file and symbol totals, not incremental or edge totals
  (`app/api/repo.py`, `tests/test_repo_indexer.py`).

## Implemented

- Workspace-scoped incremental file and symbol persistence preserves unchanged
  row identities and removes edges before changed or deleted symbols.
- Synthetic module symbols and versioned deterministic edges cover exact local
  imports, syntactic route ownership and exact test-path links.
- Snapshot fingerprints distinguish clean commits from dirty working-tree
  content and are retained with edge evidence.
- Focused packs can expose a bounded `affected_code.v1` payload; the selected
  inspector renders likely implementation files, exact linked tests and short
  impact paths without adding code nodes to the Project map.
- Runtime and Alembic migrations add stable identities and evidence fields while
  retaining legacy edges as `legacy.unspecified`.

## Implemented contract and acceptance requirements

### 1. Snapshot identity and truth boundary

Each scan produces a repository snapshot with:

```json
{
  "repo_root": "/absolute/resolved/path",
  "head_commit": "git SHA or null",
  "dirty": true,
  "snapshot_fingerprint": "sha256",
  "indexed_at": "ISO-8601 UTC"
}
```

`snapshot_fingerprint` is the SHA-256 of canonical JSON containing the resolved
repository root, HEAD, and the sorted indexed `(path, sha256)` pairs plus sorted
dirty `(status, old_path, path, sha256)` records. It is the authoritative snapshot
identity. `head_commit` alone is authoritative only when `dirty` is false.

User-facing wording must follow this distinction:

- clean: `Indexed at commit abc1234`;
- dirty: `Based on HEAD abc1234 with local changes`;
- no Git HEAD: `Based on the current local files`.

Never describe a dirty working-tree result as code "at" its HEAD commit.

### 2. Stable identities

#### File

Persistence is workspace-scoped. A scan without a non-null `workspace_id` may
produce a file-output pack, but it must not write `CodeFile`, `CodeSymbol`,
`CodeEdge` or `RepoEvent` rows. The natural file identity is:

`(workspace_id, resolved repo_root, POSIX-relative path)`

Repeated scans with the same identity update the row in place. Matching `sha256`
means the file and every existing symbol row remain unchanged. `last_commit` is
updated to the snapshot HEAD as scan metadata; it is not a claim that dirty file
content exists in that commit.

The writer stores a non-null `identity_key`, computed as the SHA-256 of canonical
JSON containing that tuple. Persistence adds:

- unique `(workspace_id, repo_root, path)`;
- unique `identity_key`.

`repo_root` and `path` must be normalized before lookup. Case folding is not
performed because repository paths may be case-sensitive.

#### Symbol

Every indexed file has one synthetic `module` symbol, including files with no
other parsed symbols. It uses the normalized path as `name` and `qualified_name`,
null line bounds, and is the file-level endpoint for import and test edges.
Within one parsed file revision, a symbol identity is:

`(code_file_id, symbol_type, qualified_name-or-name, start_line, end_line)`

The SHA-256 of this tuple is stored as a non-null, globally unique
`identity_key`. The existing deterministic de-duplication key remains the parser
gate. Symbol
UUIDs are durable only while the parent file hash is unchanged. When the file
changes, all of that file's symbols are replaced in one transaction; no attempt
is made to infer that a moved or edited symbol is "the same" symbol.

#### Edge

An edge identity is a deterministic `edge_key` hash of:

`rule_id, rule_version, source_symbol_id, target_symbol_id, evidence_path,
evidence_start_line, evidence_end_line`

The edge UUID is retained when this key is present in the next snapshot. Snapshot
metadata may update in place. If either endpoint is replaced, every incident edge
is deleted before its symbol and only exactly resolvable edges are rebuilt.

### 3. Additive schema migration

The migration adds, without renaming or dropping current fields:

#### `code_files`

- `identity_key VARCHAR(64)`;
- `is_test BOOLEAN NOT NULL DEFAULT false`;
- unique indexes on `identity_key` and `(workspace_id, repo_root, path)`.

#### `code_symbols`

- `identity_key VARCHAR(64)`;
- unique index on `identity_key`.

#### `code_edges`

- `edge_key VARCHAR(64)`;
- `rule_id VARCHAR(100)`;
- `rule_version VARCHAR(32)`;
- `evidence_path TEXT`;
- `evidence_start_line INTEGER`;
- `evidence_end_line INTEGER`;
- `evidence_json TEXT NOT NULL DEFAULT '{}'`;
- `evidence_sha256 VARCHAR(64)`;
- `snapshot_commit VARCHAR(100)`;
- `snapshot_dirty BOOLEAN NOT NULL DEFAULT false`;
- `snapshot_fingerprint VARCHAR(64)`;
- unique index on `edge_key`;
- index on `(rule_id, source_symbol_id)`.

The migration first backfills every identity key. Existing edges are retained with
`rule_id = legacy.unspecified`, `rule_version = 0`, canonical legacy evidence and
an edge key derived from the existing row ID; they are never used for
`affected_code`. After backfill, file/symbol/edge identity keys, rule ID/version,
evidence JSON and evidence hash become non-null. Snapshot commit/fingerprint and
source line fields remain nullable because legacy rows cannot truthfully supply
them. The migration must inspect existing file natural-key duplicates before
creating unique indexes and stop with a clear re-index instruction instead of
choosing a row or deleting evidence silently.

Foreign keys from symbols to files and edges to symbols use `ON DELETE CASCADE`
where the migration backend can change constraints safely. The writer still uses
the explicit portable order `CodeEdge -> CodeSymbol -> CodeFile`; correctness must
not depend on ORM cascade behavior, and migration tests cover SQLite and
PostgreSQL-compatible metadata.

The normal runtime migration and the Alembic revision must describe the same
columns and indexes. Downgrade drops only these new indexes/columns; it does not
delete file, symbol or legacy edge rows. The release rollback is therefore:
disable affected-code reads and edge writes first, then downgrade. Indexing remains
usable through the pre-existing full-rebuild behavior if the application version
is rolled back.

### 4. Incremental persistence behavior

One transaction performs a scan for one `(workspace_id, repo_root)`:

1. Load existing `CodeFile` rows keyed by path.
2. Classify scanned paths as unchanged, changed or added by exact hash comparison.
3. Classify persisted paths absent from the scan as deleted.
4. Preserve unchanged file IDs, symbol IDs and valid incident edge IDs.
5. For changed files, delete incident edges, delete only that file's symbols,
   update the file row, then insert its newly parsed symbols.
6. For deleted files, delete incident edges, symbols and the file row.
7. Insert added files and symbols.
8. Resolve the complete desired supported-edge set across the final in-memory
   snapshot. Diff all persisted supported edges by `edge_key`: retain present
   keys, delete every absent key, and insert new keys. A newly added file can make
   a formerly unique import ambiguous, so limiting invalidation to changed
   endpoints would leave a false edge.
9. Flush the repository event and return exact counters.

The endpoint response adds internal integration facts:

```json
{
  "files_indexed": 42,
  "files_added": 1,
  "files_changed": 2,
  "files_unchanged": 38,
  "files_deleted": 1,
  "symbols_indexed": 190,
  "edges_indexed": 31,
  "snapshot_fingerprint": "..."
}
```

These counters are useful for tests and diagnostics; they do not get dashboard
cards.

#### Git state cases

| Case | Persistence behavior | Product wording |
| --- | --- | --- |
| Unchanged | Preserve file, symbol and matching edge UUIDs. | No special message. |
| Changed | Replace only that file's symbols and incident edges. | `Includes local changes` when dirty. |
| Added/untracked | Insert normally; bind to snapshot fingerprint, not HEAD. | `New local file` only when shown. |
| Deleted | Remove file, symbols and incident edges; retain the deletion only in snapshot/change evidence. | Do not show it as a current affected file. |
| Renamed | Treat as exact old-path deletion plus new-path addition. Preserve Git `old_path` and `path` in change evidence, but do not infer symbol continuity. | `Renamed from …` only when Git reported it. |
| Clean new commit | Preserve rows for files whose hashes did not change; update snapshot metadata. | `Indexed at commit …`. |
| Dirty at a commit | Hash current working-tree content and include dirty status in the fingerprint. | `Based on HEAD … with local changes`. |

If scanning or persistence fails, the prior complete index remains authoritative;
no partial snapshot is exposed.

### 5. Supported deterministic edges

Only the following rule IDs are admitted in P1. Every edge requires exactly one
target. Zero or multiple candidates produce no edge and an optional diagnostic
counter; they do not produce a relationship with low confidence.

#### `local_module_import.v1` — `imports`

- Python: resolve an AST `import` or `from` module only to an indexed repository
  module at the exact module path (`x.py` or `x/__init__.py`). Relative imports are
  resolved from the importing package. When both layouts match, or the syntax
  cannot identify the module portion, reject it.
- JavaScript/TypeScript: resolve only static relative specifiers beginning `./` or
  `../`. Use the explicit extension, or accept an extension/index expansion only
  when exactly one indexed `.js`, `.jsx`, `.ts` or `.tsx` target exists.
- Package imports, configured aliases, dynamic imports, `require()` with a
  non-literal, wildcard export chains and dependency-package files are excluded.
- Endpoints are deterministic per-file `module` symbols. Evidence stores the
  importing path, exact literal/specifier and parser line range.

Plain-language reason: `Imports <target> through an exact local import.`

#### `route_handler_owner.v1` — `owned_by`

- Python: a static HTTP route decorator and the function defined by the same AST
  node create `route -> function` within one file.
- JavaScript/TypeScript: a static `router|app.METHOD("/path", handler)` creates an
  edge only when `handler` is a direct identifier matching exactly one top-level
  function in that file.
- Dynamic paths, middleware chains, inline callbacks without a separately indexed
  handler, re-exported handlers and multiple same-name candidates are excluded.
- Evidence stores the route literal, method, file and route call/decorator range.

Plain-language reason: `Defines the handler for <METHOD /path>.`

#### `test_path_match.v1` — `tests`

A test module links to a non-test module only for one unique exact path convention:

- Python sibling/mirrored `test_<name>.py` to `<name>.py`, including a mirrored
  path beneath `tests/` against an existing repository `app/`, `src/` or root
  path;
- JS/TS sibling `<name>.test|spec.<ext>` to `<name>.<supported-ext>`, including an
  exact `__tests__` parent mirror.

If more than one source-root or supported-extension candidate exists, reject it.
Substring, embedding and LLM similarity never establish a test edge. Evidence is
the exact path transformation and both hashes.

Plain-language reason on code: `Linked to <test path> by the repository's exact
test path.`

Plain-language reason on test: `Tests <code path> by an exact path match.`

#### Proposed follow-on: `test_symbol_match.v1` — `tests`

This rule runs only after `test_path_match.v1` has established one unique test
module to production-module pair:

- Python `test_<name>` resolves only to one production symbol named exactly
  `<name>` in that paired module;
- JavaScript/TypeScript static `test("<name>", ...)` or `it("<name>", ...)`
  resolves only to one production symbol named exactly `<name>` in that paired
  module;
- matching is case-sensitive and exact. Descriptive strings, substrings, global
  same-name searches and duplicate candidates produce no edge.

Plain-language reason: `Directly exercises <symbol> by exact test name.`

No P1 rule emits general `calls`, `references`, inheritance, database-model,
runtime or transitive dependency edges. Existing `legacy.unspecified` rows do not
become trusted merely because they are present.

### 6. `affected_code` contract

Focused task packs add a top-level `affected_code` object. The current raw
`repo_state.relevant_files` remains for compatibility but is not the UI contract.

```json
{
  "schema_version": "affected_code.v1",
  "snapshot": {
    "head_commit": "abc123",
    "dirty": false,
    "snapshot_fingerprint": "...",
    "indexed_at": "2026-07-14T12:00:00Z"
  },
  "files": [
    {
      "path": "app/services/repo_indexer.py",
      "role": "likely_implementation",
      "why": "Matches the focused task's repository-index wording.",
      "sha256": "...",
      "line_ranges": [{"start_line": 280, "end_line": 350}],
      "evidence": [{"kind": "objective_match", "terms": ["repository", "index"]}],
      "related_tests": [
        {
          "path": "tests/test_repo_indexer.py",
          "why": "Linked by the repository's exact test path.",
          "edge_key": "...",
          "rule_id": "test_path_match.v1"
        }
      ],
      "impact_paths": [
        {
          "paths": ["tests/test_repo_indexer.py", "app/services/repo_indexer.py"],
          "why": "Exact test path link."
        }
      ]
    }
  ],
  "truncated": false
}
```

Bounds are fixed and deterministic:

- at most 12 files, ordered by existing objective score then path;
- at most 4 related tests per file, ordered by path;
- at most 3 impact paths per file;
- at most 4 edges per impact path;
- only current indexed files with a hash;
- only edge evidence from the same `snapshot_fingerprint`;
- no transitive path when an intermediate edge is legacy, ambiguous or from a
  different snapshot.

An `impact_path` means only "connected by these exact stored rules." It is not a
prediction that editing the first file will change or break every later file.

`why` is selected from a small human-facing template set: explicit file named in
the objective, objective path/symbol match, exact local import, route ownership,
or exact linked test. Internal score, matched-term weights, edge IDs and rule
versions remain in `evidence`, not in primary prose.

The object is omitted when there is no focused task, no repository snapshot, or no
evidenced file. Do not populate it from fallback manifests/tests alone. An empty
edge set does not remove a genuinely objective-matched file; it only means related
tests and impact paths are absent.

`run_timeline.v1` returns the latest pack's same bounded `affected_code` object at
the top level. It must not merge these prepared likely files with event `files`,
which remain files actually reported by an observed run. This prevents "likely to
change" from appearing as "changed".

### 7. Inspector placement and user perception

Use the existing selected-focus inspector. After preparation, place one collapsed
`Affected code` disclosure between focus evidence and `Agent runs`:

- summary: `3 likely files · 2 linked tests`;
- snapshot note using the clean/dirty wording above;
- rows labelled `Likely implementation` or `Related test` with path and one
  sentence `why`;
- expand a row only for line ranges or a short exact path chain.

If `affected_code` is absent or has no files, render nothing—no empty panel and no
warning. Keep the section usable on narrow screens with wrapping paths and no
horizontal graph. The Project map remains module-level.

Do not expose the words `compiler`, `CodeEdge`, `rule version`, `ranking score`,
`snapshot fingerprint`, `call graph`, or `complete dependency map` in primary UI.
The user should perceive a direct answer to: **Which files should the agent inspect,
which tests are exactly linked, and why?**

### 8. Acceptance fixtures and tests

This section defines the complete release contract. The implemented baseline
covers repeat scans, changed/deleted files, exact supported edges, focused pack
integration and migration head. The broader adversarial, rollback and database
matrix below remains the acceptance backlog where not yet represented by a test.

#### Incremental persistence

- Two identical scans preserve every file and symbol UUID and report all files
  unchanged.
- Editing one file preserves all other file/symbol UUIDs, replaces only edited-file
  symbols and removes/rebuilds only incident edges.
- Deleting a file removes its symbols and incoming/outgoing edges.
- A Git rename records `old_path` and new `path`, removes the old identity and adds
  the new identity.
- A clean HEAD change with unchanged content preserves rows. Dirty/untracked
  content changes the snapshot fingerprint without claiming it belongs to HEAD.
- A persistence failure rolls back the entire scan.

#### Exact edge fixtures

- Python absolute local import, relative local import and decorated route handler.
- TS/JS relative import with explicit extension, unique extension expansion and a
  direct named route handler.
- Python mirrored test path and JS/TS sibling or `__tests__` path.
- Exact Python and JS/TS test-symbol names after a unique module link, plus fuzzy
  and duplicate-name negative fixtures.
- Negative fixtures for package imports, aliases, dynamic paths, ambiguous
  extension/module candidates, duplicate handler names and fuzzy test names.
- Every accepted edge asserts rule ID/version, exact source range, evidence JSON,
  endpoint identity, commit/fingerprint and stable `edge_key` on repeat scan.

#### Pack, API and UI

- A focused objective fixture asserts the expected implementation file, exact
  linked test, human `why`, bounds and snapshot identity.
- A fallback-only relevant-file result does not manufacture `affected_code`.
- Timeline returns prepared `affected_code` separately from observed event files.
- Inspector tests cover collapsed placement, concise reason, dirty wording, absent
  state and wrapped narrow layout.
- Migration tests cover a populated legacy database, new indexes/columns, retained
  legacy edge and downgrade. Duplicate file identities must produce the documented
  actionable migration failure.

Release gates remain the focused and full backend/frontend suites, production
build, migration tests, `git diff --check`, and live desktop/narrow visual checks.

## Not implemented yet

- General call/reference graphs, type resolution, inheritance, data flow or
  transitive-change certainty.
- Exact test-symbol edges; P1 currently links tests to production modules only by
  a unique exact path convention.
- Import alias configuration such as TS path aliases, bundler aliases or arbitrary
  Python path mutation.
- Dependency-package indexing or a graph database.
- LLM-authored edges, inferred renames or inferred symbol continuity.
- Autonomous code review, code-quality/slop grading, or a claim that listed files
  are exhaustive.
- File/symbol nodes on the Project map.
- Persisted compiler diagnostics UI. Ambiguity is counted for evaluation and
  omitted from user conclusions.

## Risks and remaining gaps

- Regex-based JS/TS parsing supports only the explicit static forms above; false
  negatives are expected and safer than guessed edges.
- Exact test-path rules vary across repositories. Precision is the P1 goal; new
  conventions require named, versioned rules and negative fixtures.
- A full working-tree scan still reads unchanged files to calculate hashes. This
  contract makes database writes incremental, not filesystem discovery.
- Existing databases can contain duplicate file natural keys because no unique
  constraint exists today. Migration must surface this and require a deliberate
  re-index rather than silently merging provenance.
- `last_commit` is legacy naming and can be misread for dirty files. The snapshot
  fingerprint and explicit dirty wording are required to prevent that error.
