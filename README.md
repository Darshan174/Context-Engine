# Context Engine

Context Engine is an infrastructure product that ingests unstructured company
data, organizes it into a structured knowledge graph, and exposes that graph
through a Context API for downstream AI systems.

## Current Backend Scope

This repository currently includes the foundation for:

- FastAPI application bootstrap
- Async SQLAlchemy database wiring
- Alembic migration scaffold
- Docker Compose services for PostgreSQL, Redis, API, and worker
- Connector-backed ingestion for Slack, Notion, Zoom transcripts, and GitHub issues / pull requests
- Query, provenance, review, temporal, and eval flows for source-backed answers

## Connector Strategy

The connector layer is intentionally mixed:

- `Slack` stays built in because OAuth, thread expansion, and real-time events are product-critical.
- `Notion` is planned to use a `dlt` verified source rather than a full hand-built sync.
- `GitHub` stays narrow and native for now because issues and pull requests are high-signal engineering context without needing a full repo mirror.
- `Google Drive` is planned to use `Unstructured` for ingestion and document extraction.
- `Gong` is expected to stay on the official API because transcript semantics matter more than generic ETL.

This keeps the product-specific parts in-house while reusing OSS where it actually helps.

## Quick Start

1. Copy `.env.example` to `.env`
2. Generate an `ENCRYPTION_KEY` before using manual-token connectors:

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Put that value into `.env` as `ENCRYPTION_KEY=...`.

3. Start the backend stack:

```bash
docker compose up -d postgres redis api worker
```

4. Install dependencies with your preferred environment manager, for example:

```bash
pip install -e ".[dev]"
```

5. Run a quick local preflight if you are starting services outside Compose:

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

6. Run the migration locally when you are not relying on the Compose `api` container:

```bash
alembic upgrade head
```

7. Seed the deterministic demo workspace used by the smoke and eval flows:

```bash
python scripts/seed_demo.py --json --replace-existing
```

This prints a stable `workspace_id` you can reuse for local eval runs.

8. If you are not using the Compose `api` service, run the API manually:

```bash
uvicorn app.main:app --reload
```

If port `8000` is already in use:

```bash
uvicorn app.main:app --reload --port 8001
```

9. Create an empty workspace only if you want manual CRUD testing outside the seeded demo:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Demo","description":"Local test workspace"}'
```

10. Run the automated backend smoke test against the live API:

```bash
python scripts/smoke_phase1.py
```

This validates health/readiness, workspace bootstrap, model/component/relationship
CRUD, and the `/api/query` response path.

If the API is running on a different port, pass `--base-url`, for example:

```bash
python scripts/smoke_phase1.py --base-url http://localhost:8001
```

## Health Checks

- `GET /health` returns basic liveness
- `GET /health/ready` verifies PostgreSQL and Redis connectivity

## Accuracy Runtime Config

Provider-backed structured extraction and embeddings are optional in local OSS
setups. Leave the keys blank to stay offline. For real models, set:

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

For production Zoom OAuth + webhook ingestion, also set:

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

GitHub does not require app-level env vars for the first pass. Use
`POST /api/connectors/github/connect` with a manual token plus a repository list.

## Eval Regression

Run the startup-question regression harness against the seeded demo workspace:

```bash
context-engine-eval-regression --workspace-id REPLACE_WITH_WORKSPACE_ID --json
```

The existing script wrapper still works:

```bash
python scripts/run_eval_regression.py --workspace-id REPLACE_WITH_WORKSPACE_ID --json
```

Phase 3B is currently frozen against these exit criteria:

- `25` total gold-set cases
- `5` required domains: `pricing`, `blocker`, `roadmap`, `decision`, `meeting`
- `>= 0.80` pass rate
- `>= 0.80` average retrieval hit quality
- `>= 0.80` average extracted fact correctness
- `>= 0.75` average final answer correctness
- `<= 0.25` confidence calibration error

CI enforces both the DB-backed regression tests and the CLI eval run via
`.github/workflows/backend-accuracy.yml`.

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
