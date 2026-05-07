# Connector / Knowledge Graph Contract

Last updated: 2026-05-01
Reviewed: 2026-05-01 by Xiaomi MiMo V2.5 Pro
Branch: `agent/xiaomi-repo-review-docs`

---

## 1. Connector Response Schema

### 1.1 Wrapped Response Shape

**Implemented:** `GET /api/connectors` returns a wrapped object with two keys:
- `connectors`: list of connector objects
- `setupStatus`: list of setup status objects

**Evidence:** `app/api/connectors.py`, lines 363–421. The handler returns `{"connectors": result, "setupStatus": setup_status}`.

**Evidence:** `tests/test_connectors.py`, lines 73–84. The test `test_list_connectors_returns_all_catalog_entries` asserts `"connectors" in data` and `"setupStatus" in data`.

### 1.2 Connector Object Fields

**Implemented:** Each connector object in the `connectors` list includes:
- `connector_type` (mirrors `type`)
- `type`, `name`, `description`, `color`
- `availability`, `provider`, `provider_label`, `provider_note`
- `status`, `last_sync`, `items_synced`
- `message` (for unsupported connectors)
- `team_name`, `scope`, `sync_queued_at`, `sync_mode`, `sync_mode_note`
- `processed_count`, `total_processed_count`
- `auth_mode`, `account_id`, `ingestion_mode`, `source_focus`
- `last_webhook_event`, `last_webhook_received_at`
- `is_configured`, `managed_connect_available`, `managed_install_url`
- `config`: a nested dict with non-null config values

**Evidence:** `app/api/connectors.py`, lines 363–421. The handler serializes `ConnectorRead` and injects `connector_type`, `last_sync_at`, and a `config` dict.

**Evidence:** `tests/test_connectors.py`, lines 86–100. The test `test_connector_response_has_frontend_shape` asserts `connector_type`, `config`, and their types.

### 1.3 Setup Status Shape

**Implemented:** `GET /api/connectors/setup-status` returns a list of objects with:
- `connector_type`, `type`, `name`
- `configured` (bool)
- `status` (string: `available`, `coming_soon`, `disconnected`, etc.)
- `availability`, `auth_mode`

**Evidence:** `app/api/connectors.py`, lines 462–467 and 366–399.

**Evidence:** `tests/test_connectors.py`, lines 180–210.

---

## 2. AI Context Import and Source Type Counting

### 2.1 Import Endpoint

**Implemented:** `POST /api/connectors/ai-context/import` accepts a payload with `documents`, each having:
- `external_id` (required)
- `content` (required)
- `author`, `tool`, `session_type`, `session_id`, `started_at`, `ended_at`, `metadata` (optional)

**Evidence:** `app/api/connectors.py`, lines 513–573.

### 2.2 Tool-to-Source-Type Mapping

**Implemented:** Tools are mapped to source types as follows:
- `codex` → `ai_context_codex`
- `claude_code` → `ai_context_claude_code`
- `opencode` → `ai_context_opencode`
- `cursor`, `generic`, or unknown → `ai_context`

**Evidence:** `app/api/connectors.py`, lines 529–535.

### 2.3 Processing Summary Groups AI Context Subtypes

**Implemented:** `GET /api/connectors/processing-summary` counts all AI context subtypes under the single `ai_context` bucket.

**Evidence:** `app/api/connectors.py`, lines 475–484. The `all_types` dict maps `ai_context` to the list `["ai_context", "ai_context_codex", "ai_context_claude_code", "ai_context_opencode"]`. The query groups by the literal `source_type`, then Python sums the counts for all subtypes into the `ai_context` display bucket.

**Evidence:** `tests/test_connectors.py`, lines 553–590. The test `test_processing_summary_counts_ai_context_subtypes_together` creates documents with all four subtypes and asserts the summary returns `total_documents >= 4` for `ai_context`.

---

## 3. Unsupported Connector States

### 3.1 Slack Connect is Rejected

**Implemented:** `POST /connectors/slack/connect` returns `400` because Slack has `"supported": False` in the catalog.

**Evidence:** `app/api/connectors.py`, lines 594–598. The handler checks `if not catalog_entry.get("supported", True)` and raises `HTTPException(status_code=400)`.

**Evidence:** `tests/test_connectors.py`, lines 211–218. The test `test_connect_slack_returns_400_unsupported` asserts status code `400` and checks the detail message.

**Evidence:** `tests/test_connectors.py`, lines 658–665. The test `test_slack_connect_returns_400_unsupported` also asserts `400`.

### 3.2 Slack Sync Returns Failed Job

**Implemented:** If a Slack connector row exists and a sync is triggered, the sync endpoint creates a `SyncJob` with `status="failed"`, `error_type="unsupported_connector"`.

**Evidence:** `app/api/connectors.py`, lines 640–653.

**Evidence:** `tests/test_connectors.py`, lines 639–656. The test `test_slack_sync_returns_unsupported_error` asserts `status == "failed"` and `error_type == "unsupported_connector"`.

### 3.3 Discord and Gmail Are Coming Soon

**Implemented:** Discord and Gmail have `"availability": "coming_soon"` and `"supported": False`. Their connect endpoints return `400`.

**Evidence:** `app/api/connectors.py`, lines 33–124 (catalog entries).

**Evidence:** `tests/test_connectors.py`, lines 219–238.

---

## 4. Graph Visibility

### 4.1 Proposed Components Are Visible

**Implemented:** `GET /api/graph` includes components with status `proposed` alongside `active` and `needs_review`.

**Evidence:** `app/api/graph.py`, line 78. The query uses `.where(Component.status.in_(["active", "needs_review", "proposed"]))`.

**Evidence:** `tests/test_graph_api.py`, lines 353–380. The test `test_graph_includes_proposed_components` creates a component with `status="proposed"` and asserts it appears in the response.

### 4.2 Graph Response Provenance

**Implemented:** Graph components include:
- `source_type`
- `source_url`
- `ingested_at`

**Evidence:** `app/api/graph.py`, lines 39–41 (ComponentRead schema) and lines 128–130 (response construction).

**Evidence:** `tests/test_graph_api.py`, lines 11–70. Tests assert `source_type`, `source_url`, and `ingested_at` are present.

### 4.3 Relationships Include Confidence and Evidence

**Implemented:** Graph relationships include `confidence` and `evidence`.

**Evidence:** `app/api/graph.py`, lines 51–52 (RelationshipRead schema) and lines 136–137 (response construction).

**Evidence:** `tests/test_graph_api.py`, lines 72–103. Test asserts `confidence == 0.85` and `evidence == "'A' depends_on 'B'"`.

---

## 5. SQLite Schema Migration / Backfill

### 5.1 Startup Migration Runs

**Implemented:** On application startup, `Base.metadata.create_all()` runs first, then `run_migrations()` executes.

**Evidence:** `app/main.py`, lines 18–23. The lifespan context manager calls `create_all` and then `run_migrations`.

**Evidence:** `app/migrations.py`, lines 7–8. `run_migrations` delegates to `_migrate_relationships_confidence_evidence`.

### 5.2 Relationships Table Migration

**Implemented:** The migration adds `confidence` and `evidence` columns to the `relationships` table if missing, and backfills null values.

**Evidence:** `app/migrations.py`, lines 11–32. The function:
- No-ops if the table does not exist (detected via empty column set).
- Adds `confidence FLOAT NOT NULL DEFAULT 0.7` if missing.
- Adds `evidence TEXT` if missing.
- Backfills `confidence = 0.7` and `evidence = 'backfill: schema migration'` for null rows.

**Not implemented yet:** Alembic-based migration management. The current approach is a lightweight startup guard suitable for local SQLite deployments.

---

## 6. Relationship Rules

### 6.1 Cross-Model Relationships

**Implemented:** The ingestion service resolves relationship targets across all models, not just the source component's model.

**Evidence:** `app/services/ingest.py`, lines 111–126. The first query searches by `Component.name` across all models, ordered by confidence. A fallback query restricts to the same model.

**Evidence:** `tests/test_ingestion.py`, lines 13–65. `test_creates_cross_model_relationship` verifies a Pricing component can link to a Security component.

### 6.2 Confidence Threshold

**Implemented:** Relationships are skipped if extractor confidence is below `0.6`.

**Evidence:** `app/services/ingest.py`, lines 103–105.

**Evidence:** `tests/test_ingestion.py`, lines 109–146. `test_skips_low_confidence_relationship` asserts no row is created for `confidence=0.45`.

### 6.3 Duplicate and Self-Loop Prevention

**Implemented:** Duplicate relationships (same source, target, and type) and self-loops are rejected.

**Evidence:** `app/services/ingest.py`, lines 131–139 (duplicate check) and line 114 (self-loop check via `Component.id != source.id`).

**Evidence:** `tests/test_ingestion.py`, lines 187–261.

---

## 7. Frontend/Backend Catalog Alignment

### 7.1 Frontend/Backend Catalog Alignment

**Implemented:** The frontend `CONNECTOR_CATALOG` in `hooks.js` (lines 73-154) and the backend `CONNECTOR_CATALOG` in `app/api/connectors.py` (lines 19-124) are now aligned. Both include 8 types: `slack`, `discord`, `ai_context`, `local`, `zoom`, `gdrive`, `gmail`, `wispr_flow`.

**Behavior:** `normalizeConnectors` (hooks.js line 1774) iterates over `CONNECTOR_CATALOG` values. For types with a backend record, it uses the backend data. For types without a backend record, it returns `status: "coming_soon"` and `connectorId: null`.

### 7.2 Backend-Only Connector Types

The backend has no types that the frontend omits. All 8 backend types appear in the frontend catalog.

### 7.3 Frontend Hooks Without Working Backend Paths

**Observed:** `hooks.js` defines mutation hooks for provider setup paths that are not implemented as working integrations:
- `useConnectNotion` → `POST /connectors/notion/connect` (line 1604). The generic connect route exists, but `notion` is not in the backend catalog, so this returns 404 unknown connector type.
- `useConnectZoom` → `POST /connectors/zoom/connect` (line 1620). The generic connect route exists and `zoom` is catalogued, so this returns 400 coming soon.
- `useConnectGitHub` → `POST /connectors/github/connect` (line 1636). The generic connect route exists, but `github` is not in the backend catalog, so this returns 404 unknown connector type.
- `useSaveSlackOAuthSettings` → `POST /connectors/slack/oauth-settings` (line 1654). No backend route exists for this settings endpoint.

**Risk:** If these hooks are called from reachable UI paths, Notion/GitHub/Slack settings will fail as missing or unknown, and Zoom will fail as an intentional coming-soon stub. The hooks do not have fallback mock behavior, so errors propagate to the caller.

### 7.4 Slack Availability Inconsistency

**Observed:** The backend catalog sets Slack to `"availability": "available"` but `"supported": False` (line 30). This means:
- `GET /connectors` returns Slack with `availability: "available"` and `status: "disconnected"`
- `POST /connectors/slack/connect` returns 400 because `supported` is False
- The frontend shows Slack as "available" in the connector card

**Compare with Discord:** Discord uses `"availability": "coming_soon"` and `"supported": False` (line 38). The UI correctly shows Discord as "coming soon".

**Recommendation:** Change Slack's `availability` to `"coming_soon"` to match Discord's honest pattern, or add a distinct `supported` check in the frontend before showing the connect button.

---

## 8. Not Implemented Yet

- **Slack OAuth install/callback and Slack API sync.** No OAuth handshake, no Slack client, no real sync worker.
- **Discord API sync.** Catalogued as `coming_soon`.
- **Gmail OAuth and mailbox sync.** Catalogued as `coming_soon`.
- **Zoom, Google Drive, Gmail, and Wispr provider backends.** Catalog entries exist in backend, but no sync logic.
- **Notion and GitHub catalog entries/provider backends.** Frontend hooks exist, but these connector types are not catalogued in the backend.
- **Zoom provider sync.** Frontend hook exists and the generic backend connect route handles it as a catalogued `coming_soon` connector, but no working sync path exists.
- **GitHub connect behavior.** Frontend hook exists (`useConnectGitHub`), but the backend currently treats `github` as an unknown connector type.
- **Slack OAuth settings endpoint.** Frontend hook exists (`useSaveSlackOAuthSettings`) but no backend endpoint.
- **Alembic-based production migration management.** Current migrations are lightweight startup guards.
- **Dedicated frontend AI Context import form.** The backend endpoint exists; the frontend relies on the generic Sources workflow or manual API calls.

---

## 9. Verification

### 9.1 Test Commands

```bash
pytest -q
cd frontend && npm run build
```

### 9.2 Latest Verified Result (2026-05-01)

- `pytest -q`: **107 passed**
- `npm run build`: **passed**

### 9.3 Evidence Files Used

| File | Lines | Purpose |
|------|-------|---------|
| `app/api/connectors.py` | 19–124 | Connector catalog |
| `app/api/connectors.py` | 402–460 | `GET /connectors` response shape |
| `app/api/connectors.py` | 475–484 | AI context subtype grouping |
| `app/api/connectors.py` | 513–573 | AI context import endpoint |
| `app/api/connectors.py` | 594–598 | Slack connect rejection |
| `app/api/connectors.py` | 640–653 | Slack sync failure |
| `app/api/graph.py` | 78 | Graph status filter includes `proposed` |
| `app/api/graph.py` | 128–130 | Component provenance fields |
| `app/api/graph.py` | 136–137 | Relationship confidence/evidence |
| `app/migrations.py` | 11–32 | Relationships column migration |
| `app/main.py` | 18–23 | Startup lifecycle |
| `app/services/ingest.py` | 103–139 | Relationship creation rules |
| `tests/test_connectors.py` | 73–112 | Connector list shape tests |
| `tests/test_connectors.py` | 180–210 | Setup status tests |
| `tests/test_connectors.py` | 211–218 | Slack connect rejection test |
| `tests/test_connectors.py` | 553–590 | AI context subtype grouping test |
| `tests/test_connectors.py` | 639–665 | Slack unsupported tests |
| `tests/test_graph_api.py` | 11–103 | Graph provenance tests |
| `tests/test_graph_api.py` | 377–406 | Proposed visibility test |
| `tests/test_ingestion.py` | 14–65 | Cross-model relationship tests |
| `tests/test_ingestion.py` | 110–146 | Confidence threshold tests |
