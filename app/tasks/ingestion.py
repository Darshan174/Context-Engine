"""Celery task: run_ingestion — document reprocess/replay only.

NOT called by run_sync (which handles its own ingestion inline via SyncExecutor).
Used exclusively by the reprocess endpoint to re-extract a single document.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.connector import Connector
from app.models.job import SyncJob, SyncJobStatus
from app.models.source import SourceDocument
from app.services.ingestion_service import IngestionService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.ingestion.run_ingestion", max_retries=0)
def run_ingestion(self, sync_job_id: str, document_id: str) -> dict:
    """Re-extract knowledge from a single source document.

    Scoped to document_id only — will not sweep unrelated pending docs.
    """
    return asyncio.run(_run_ingestion_async(sync_job_id, document_id))


async def _run_ingestion_async(sync_job_id: str, document_id: str) -> dict:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                job = await session.get(SyncJob, sync_job_id)
                if job is None:
                    logger.error("SyncJob %s not found", sync_job_id)
                    return {"error": "job not found"}

                doc = await session.get(SourceDocument, UUID(document_id))
                if doc is None:
                    job.status = SyncJobStatus.FAILED
                    job.error_type = "DocumentNotFound"
                    job.error_message = f"SourceDocument {document_id} not found"
                    return {"error": "document not found"}

                connector = await session.get(Connector, doc.connector_id)
                if connector is None:
                    job.status = SyncJobStatus.FAILED
                    job.error_type = "ConnectorNotFound"
                    job.error_message = "Connector for document not found"
                    return {"error": "connector not found"}

                job.status = SyncJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)

            async with session.begin():
                job = await session.get(SyncJob, sync_job_id)
                doc = await session.get(SourceDocument, UUID(document_id))
                connector = await session.get(Connector, doc.connector_id)

                try:
                    svc = IngestionService(session)
                    processed = await svc.process_single_document(
                        workspace_id=connector.workspace_id,
                        document=doc,
                        connector_type=connector.connector_type,
                    )

                    job.status = SyncJobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    job.result_metadata = {
                        **job.result_metadata,
                        "documents_processed": processed,
                        "document_id": document_id,
                    }
                    return job.result_metadata

                except Exception as exc:
                    job.status = SyncJobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_type = exc.__class__.__name__
                    job.error_message = str(exc)
                    logger.exception("Ingestion failed for document %s", document_id)
                    return {"error": str(exc), "error_type": exc.__class__.__name__}
    finally:
        await engine.dispose()
