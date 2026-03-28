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

4. Run the initial migration:

```bash
alembic upgrade head
```

5. Seed demo data if you want sample records:

```bash
python scripts/seed_demo.py
```

6. Run the API:

```bash
uvicorn app.main:app --reload
```

7. Create a workspace if you want an empty workspace for manual CRUD testing:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Demo","description":"Local test workspace"}'
```

## Health Checks

- `GET /health` returns basic liveness
- `GET /health/ready` verifies PostgreSQL and Redis connectivity

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
