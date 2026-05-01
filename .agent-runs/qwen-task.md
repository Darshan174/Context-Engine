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
- Final report must include files changed, tests run, evidence, risks, and unresolved gaps.

