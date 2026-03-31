"""Celery task: run_sync — full connector sync pipeline.

Each invocation creates its own async engine + session so the worker
process is independent of the web app's connection pool.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.connector import Connector
from app.models.job import SyncJob, SyncJobStatus
from app.services.sync_service import SyncExecutor
from app.tasks.celery_app import celery_app
from app.utils.crypto import EncryptionError, decrypt_token

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.sync.run_sync", max_retries=0)
def run_sync(self, sync_job_id: str, connector_id: str) -> dict:
    """Execute fetch→persist→ingest for one connector.

    Returns a result dict persisted in Celery backend and SyncJob.result_metadata.
    """
    return asyncio.run(_run_sync_async(sync_job_id, connector_id))


async def _run_sync_async(sync_job_id: str, connector_id: str) -> dict:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with AsyncSessionLocal() as session:
            # Phase 1: mark RUNNING
            async with session.begin():
                job = await session.get(SyncJob, sync_job_id)
                if job is None:
                    logger.error("SyncJob %s not found", sync_job_id)
                    return {"error": "job not found"}

                connector = await session.get(Connector, connector_id)
                if connector is None:
                    job.status = SyncJobStatus.FAILED
                    job.error_type = "ConnectorNotFound"
                    job.error_message = f"Connector {connector_id} not found"
                    return {"error": "connector not found"}

                try:
                    token = decrypt_token(connector.oauth_token_encrypted)
                except (EncryptionError, TypeError) as exc:
                    job.status = SyncJobStatus.FAILED
                    job.error_type = "EncryptionError"
                    job.error_message = str(exc)
                    return {"error": str(exc)}

                job.status = SyncJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)

            # Phase 2: run pipeline in its own transaction
            async with session.begin():
                job = await session.get(SyncJob, sync_job_id)
                connector = await session.get(Connector, connector_id)
                token = decrypt_token(connector.oauth_token_encrypted)

                try:
                    result = await SyncExecutor(session).run(connector, token)

                    job.status = SyncJobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    job.result_metadata = {
                        **job.result_metadata,
                        "documents_fetched": result.documents_fetched,
                        "documents_persisted": result.documents_persisted,
                        "documents_processed": result.documents_processed,
                        "sync_mode": result.sync_mode,
                    }
                    return job.result_metadata

                except Exception as exc:
                    job.status = SyncJobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_type = exc.__class__.__name__
                    job.error_message = str(exc)
                    logger.exception("Sync failed for connector %s", connector_id)
                    return {
                        "error": str(exc),
                        "error_type": exc.__class__.__name__,
                    }
    finally:
        await engine.dispose()
