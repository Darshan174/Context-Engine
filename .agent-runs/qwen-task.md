# Qwen Task

## Role

You are the graph reasoning checker, schema compatibility reviewer, and hard bug solver.

Work in this repo:

```text
/Users/darshann/Desktop/context-engine
```

Preferred branch:

```bash
agent/qwen-graph-reasoning-validation
```

## Focus

- Relationship extraction and relationship creation must be conservative and evidence-based.
- Graph APIs must expose current, review-needed, and future/proposed context.
- Existing local SQLite databases must remain usable after schema additions.
- MCP/query behavior should preserve useful provenance.
- The graph must help users understand what needs to be done now, what was decided in the past, and what is proposed for the future.

## Required Workload

1. Add adversarial graph tests for relationship hallucination:
   - unrelated components in the same source must not get relationship edges;
   - weak semantic similarity alone must not create edges;
   - explicit relationship wording should create an edge with evidence.
2. Add or verify temporal context tests:
   - future/planned/proposed facts appear as `proposed`;
   - deprecated/past facts appear as review-needed or otherwise do not overwrite active truth silently;
   - graph stats count proposed components.
3. Verify migration safety:
   - existing SQLite relationship tables missing `confidence` and `evidence` are upgraded;
   - migration is idempotent.
4. Review source provenance:
   - components returned by graph include source type/URL/ingested timestamp when available;
   - relationships include confidence and evidence when available.
5. Review MCP/query surface if relevant:
   - graph/query responses should not strip provenance in ways that make evidence impossible to inspect.

## Read First

- `AGENTS.md`
- `TASK_PLAN.md`
- `app/models.py`
- `app/migrations.py`
- `app/processing/extractor.py`
- `app/services/ingest.py`
- `app/api/graph.py`
- `app/mcp/server.py`
- `tests/test_migrations.py`
- `tests/test_graph_api.py`
- `tests/test_ingestion.py`

## Rules

- Do not implement provider OAuth.
- Do not edit connector UI unless a graph contract requires it.
- Do not create inferred relationships from weak semantic similarity alone.
- Add tests for any graph/schema behavior change.
- If behavior is already correct, add or improve tests/docs instead of changing logic unnecessarily.
- Final report must include files changed, tests run, evidence, risks, and unresolved gaps.
