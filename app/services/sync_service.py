"""SyncExecutor — the fetch→persist→ingest pipeline.

Both the Celery worker task and the in-process test path call this.
Neither ConnectorService nor the API endpoint should duplicate this logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import AuthenticationError, BaseConnector, ConnectorError, NormalizedDocument
from app.models.connector import Connector, ConnectorStatus, SyncState
from app.models.source import ConnectorType, SourceDocument
from app.services.ingestion_service import IngestionService


class SyncError(Exception):
    """Raised when the sync pipeline fails."""


@dataclass
class SyncResult:
    documents_fetched: int
    documents_persisted: int
    documents_processed: int
    sync_mode: str  # "initial" | "incremental"
    connector_type: ConnectorType

class SyncExecutor:
    """Executes the full fetch→persist→ingest cycle for one connector.

    Designed to be called from:
      - Celery worker (with its own engine + session)
      - Tests (with the test savepoint session)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, connector: Connector, token: str) -> SyncResult:
        """Run the full sync pipeline.  Updates connector and SyncState in-place.

        Raises SyncError (wrapping AuthenticationError or ConnectorError) on failure.
        The connector.config is updated with structured ``last_error`` on failure.
        """
        impl = self._resolve_connector(connector.connector_type, token)
        sync_state = await self._get_or_create_sync_state(connector)

        # Legacy cursor migration: prefer SyncState, fall back to config
        cursor = sync_state.cursor or connector.config.get("sync_cursor")
        # Mark in-progress
        connector.config = {
            **connector.config,
            "sync_queued_at": datetime.now(timezone.utc).isoformat(),
            "message": "Sync in progress",
        }
        await self.session.flush()

        documents: list[NormalizedDocument] = []
        latest_cursor: str | None = cursor

        try:
            if cursor is None:
                async for doc in impl.fetch_initial():
                    documents.append(doc)
                    latest_cursor = self._merge_cursor(
                        connector.connector_type,
                        latest_cursor,
                        doc,
                    )
            else:
                async for doc in impl.fetch_incremental(cursor=cursor):
                    documents.append(doc)
                    latest_cursor = self._merge_cursor(
                        connector.connector_type,
                        latest_cursor,
                        doc,
                    )

            persisted = await self._persist_documents(
                connector.id, connector.connector_type, documents
            )

            ingestion = IngestionService(self.session)
            processed = await ingestion.process_connector_documents(
                workspace_id=connector.workspace_id,
                connector_id=connector.id,
                connector_type=connector.connector_type,
            )

            completed_at = datetime.now(timezone.utc)

            # Update SyncState cursor
            sync_state.cursor = latest_cursor
            sync_state.last_synced_at = completed_at
            if documents:
                sync_state.last_synced_item_id = documents[-1].external_id

            # Build clean config (remove transient keys)
            sync_mode = "initial" if cursor is None else "incremental"
            total_count = await self._count_active_documents(connector.id)
            prev_processed = connector.config.get("total_processed_count", 0)
            clean = {
                k: v for k, v in connector.config.items()
                if k not in ("sync_cursor", "sync_queued_at")
            }
            connector.last_sync_at = completed_at
            connector.config = {
                **clean,
                "document_count": total_count,
                "processed_count": processed,
                "total_processed_count": prev_processed + processed,
                "sync_mode": sync_mode,
                "message": (
                    f"Synced {persisted} new documents, processed {processed}"
                    f" ({sync_mode} sync)"
                ),
            }

            # Notion transparency
            if connector.connector_type == ConnectorType.NOTION:
                connector.config = {
                    **connector.config,
                    "sync_mode_note": (
                        "Full re-fetch (Notion API limitation). "
                        "Unchanged pages are not re-processed."
                    ),
                }

            await self.session.flush()

            return SyncResult(
                documents_fetched=len(documents),
                documents_persisted=persisted,
                documents_processed=processed,
                sync_mode=sync_mode,
                connector_type=connector.connector_type,
            )

        except AuthenticationError as exc:
            await self._record_error(connector, exc, mark_error_status=True)
            raise SyncError(str(exc)) from exc
        except ConnectorError as exc:
            await self._record_error(connector, exc, mark_error_status=False)
            raise SyncError(str(exc)) from exc

    async def _record_error(
        self,
        connector: Connector,
        exc: Exception,
        *,
        mark_error_status: bool,
    ) -> None:
        if mark_error_status:
            connector.status = ConnectorStatus.ERROR
        clean = {k: v for k, v in connector.config.items() if k != "sync_queued_at"}
        connector.config = {
            **clean,
            "message": f"{'Auth failed' if mark_error_status else 'Sync failed'}: {exc}",
            "last_error": {
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        await self.session.flush()

    # ── Infrastructure helpers ────────────────────────────────────

    def _resolve_connector(
        self, connector_type: ConnectorType, token: str
    ) -> BaseConnector:
        from app.connectors.notion import NotionConnector
        from app.connectors.slack import SlackConnector
        from app.connectors.zoom import ZoomConnector

        if connector_type == ConnectorType.SLACK:
            return SlackConnector(token)
        if connector_type == ConnectorType.NOTION:
            return NotionConnector(token)
        if connector_type == ConnectorType.ZOOM:
            return ZoomConnector(token)
        raise SyncError(f"No connector implementation for {connector_type.value}")

    async def _get_or_create_sync_state(self, connector: Connector) -> SyncState:
        sync_state = await self.session.scalar(
            select(SyncState).where(SyncState.connector_id == connector.id)
        )
        if sync_state is None:
            sync_state = SyncState(connector_id=connector.id)
            self.session.add(sync_state)
            await self.session.flush()
        return sync_state

    async def _persist_documents(
        self,
        connector_id: UUID,
        connector_type: ConnectorType,
        documents: list[NormalizedDocument],
    ) -> int:
        """Upsert NormalizedDocuments; return count of newly inserted rows."""
        if not documents:
            return 0

        rows = [
            {
                "connector_id": connector_id,
                "connector_type": connector_type.value,
                "external_id": doc.external_id,
                "content": doc.content,
                "author": doc.author,
                "source_url": doc.source_url,
                "created_at_source": doc.created_at,
                "metadata": doc.metadata or {},
                "deleted_at": None,
            }
            for doc in documents
        ]

        stmt = pg_insert(SourceDocument.__table__).values(rows)
        sd = SourceDocument.__table__.c
        stmt = stmt.on_conflict_do_update(
            index_elements=["connector_id", "external_id"],
            set_={
                "content": stmt.excluded.content,
                "author": stmt.excluded.author,
                "source_url": stmt.excluded.source_url,
                "created_at_source": stmt.excluded.created_at_source,
                "metadata": stmt.excluded.metadata,
                "deleted_at": None,
                "processed_at": case(
                    (
                        or_(
                            sd.content != stmt.excluded.content,
                            sd.deleted_at.is_not(None),
                        ),
                        None,
                    ),
                    else_=sd.processed_at,
                ),
            },
        )
        stmt = stmt.returning(literal_column("(xmax = 0)").label("inserted"))
        result = await self.session.execute(stmt)
        return sum(1 for row in result if row.inserted)

    async def _count_active_documents(self, connector_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count())
            .select_from(SourceDocument)
            .where(
                SourceDocument.connector_id == connector_id,
                SourceDocument.deleted_at.is_(None),
            )
        )
        return int(count or 0)

    @staticmethod
    def _merge_cursor(
        connector_type: ConnectorType,
        current_cursor: str | None,
        document: NormalizedDocument,
    ) -> str | None:
        if document.created_at is None:
            return current_cursor

        if connector_type == ConnectorType.ZOOM:
            current_ts: datetime | None = None
            current_external_id: str = ""
            if current_cursor:
                try:
                    payload = json.loads(current_cursor)
                    current_ts = datetime.fromisoformat(
                        payload["recording_start"].replace("Z", "+00:00")
                    )
                    current_external_id = str(payload.get("external_id") or "")
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    current_ts = None

            candidate = {
                "recording_start": document.created_at.isoformat(),
                "external_id": document.external_id,
            }
            if (
                current_ts is None
                or document.created_at > current_ts
                or (
                    document.created_at == current_ts
                    and document.external_id > current_external_id
                )
            ):
                return json.dumps(candidate, sort_keys=True)
            return current_cursor

        ts = str(document.created_at.timestamp())
        if current_cursor is None or ts > current_cursor:
            return ts
        return current_cursor
