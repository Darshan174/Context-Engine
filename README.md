# Context Engine

Context Engine is an infrastructure product that ingests unstructured company
data, organizes it into a structured knowledge graph, and exposes that graph
through a Context API for downstream AI systems.

## Phase 1 Scope

This repository currently includes the foundation for:

- FastAPI application bootstrap
- Async SQLAlchemy database wiring
- Alembic migration scaffold
- Docker Compose services for PostgreSQL and Redis
- Backend project structure for later CRUD, connector, and processing work

## Connector Strategy

The connector layer is intentionally mixed:

- `Slack` stays built in because OAuth, thread expansion, and real-time events are product-critical.
- `Notion` is planned to use a `dlt` verified source rather than a full hand-built sync.
- `Google Drive` is planned to use `Unstructured` for ingestion and document extraction.
- `Gong` is expected to stay on the official API because transcript semantics matter more than generic ETL.

This keeps the product-specific parts in-house while reusing OSS where it actually helps.

## Quick Start

1. Copy `.env.example` to `.env`
2. Start infrastructure:

```bash
docker-compose up -d
```

If your Docker install supports the newer subcommand style, `docker compose up -d`
works too.

3. Install dependencies with your preferred environment manager, for example:

```bash
pip install -e ".[dev]"
```

4. Run a quick local preflight:

```bash
python scripts/preflight_phase1.py
```

This checks `.env`, PostgreSQL, and Redis. If the API is already running, it
also checks `/health` and `/health/ready`. After you start the API, you can
require those checks explicitly:

The Postgres check also verifies that the Phase 1 schema is present and the
Alembic revision matches the initial migration. If it reports missing tables or
the wrong revision, run:

```bash
alembic upgrade head
```

```bash
python scripts/preflight_phase1.py --require-api
```

5. Run the initial migration:

```bash
alembic upgrade head
```

6. Seed demo data if you want sample records:

```bash
python scripts/seed_demo.py
```

7. Run the API:

```bash
uvicorn app.main:app --reload
```

If port `8000` is already in use:

```bash
uvicorn app.main:app --reload --port 8001
```

8. Create a workspace if you want an empty workspace for manual CRUD testing:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Demo","description":"Local test workspace"}'
```

9. Run the automated Phase 1 smoke test against the live API:

```bash
python scripts/smoke_phase1.py
```

This validates health/readiness, workspace bootstrap, model/component/relationship
CRUD, and the MVP `/api/query` response path.

If the API is running on a different port, pass `--base-url`, for example:

```bash
python scripts/smoke_phase1.py --base-url http://localhost:8001
```

## Health Checks

- `GET /health` returns basic liveness
- `GET /health/ready` verifies PostgreSQL and Redis connectivity

## Accuracy Runtime Config

For provider-backed structured extraction and embeddings, set:

```bash
EXTRACTION_MODEL=openai/gpt-4.1-mini
EMBEDDING_MODEL=openai/text-embedding-3-large
EMBEDDING_DIMENSIONS=1024
LITELLM_API_KEY=your-provider-key
```

`LITELLM_API_BASE` is optional for non-default providers or gateways. The
backend stores embeddings in a fixed `pgvector` column, so `EMBEDDING_DIMENSIONS`
must match the database vector size. If `LITELLM_API_KEY` is present and the
model env vars are omitted, the backend will fall back to the default provider
models above. In `production`, missing real extraction or embedding models are
treated as configuration errors rather than silently relying on local fallbacks.

For production Zoom ingestion, also set:

```bash
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ZOOM_REDIRECT_URI=https://your-api.example.com/api/connectors/zoom/callback
ZOOM_WEBHOOK_SECRET=...
```

The Zoom connector remains transcript-only. Webhooks now require valid
`x-zm-signature` and `x-zm-request-timestamp` headers.
OAuth-installed Zoom connectors support webhook-driven sync. Manual-token Zoom
connections remain polling-only by design.

## Eval Regression

Run the startup-question regression harness against a seeded workspace:

```bash
python scripts/run_eval_regression.py --workspace-id REPLACE_WITH_WORKSPACE_ID
```

Optional thresholds:

```bash
python scripts/run_eval_regression.py \
  --workspace-id REPLACE_WITH_WORKSPACE_ID \
  --min-retrieval 0.85 \
  --min-fact-correctness 0.85 \
  --min-answer-correctness 0.80
```

The repository also includes a DB-backed gold-set regression test in
`tests/test_evals/test_gold_set.py`, intended for CI gating.

## CRUD Smoke Test

Create a model:

```bash
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id":"REPLACE_WITH_WORKSPACE_ID",
    "name":"Pricing",
    "description":"Pricing tiers and packaging"
  }'
```

List models for a workspace:

```bash
curl "http://localhost:8000/api/models?workspace_id=REPLACE_WITH_WORKSPACE_ID"
```

Add a component:

```bash
curl -X POST http://localhost:8000/api/models/REPLACE_WITH_MODEL_ID/components \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Enterprise Price",
    "value":"$500/seat",
    "confidence":0.9,
    "authority_source":"CEO Slack message"
  }'
```

Create a relationship:

```bash
curl -X POST http://localhost:8000/api/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "source_component_id":"REPLACE_SOURCE_COMPONENT_ID",
    "target_component_id":"REPLACE_TARGET_COMPONENT_ID",
    "relationship_type":"depends_on",
    "sentiment":"neutral",
    "confidence":0.8
  }'
```

Run a query against structured context:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question":"What is our enterprise pricing?",
    "workspace_id":"REPLACE_WITH_WORKSPACE_ID"
  }'
```

Or run the same checks automatically:

```bash
python scripts/smoke_phase1.py
```
