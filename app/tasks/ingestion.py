"""Document ingestion task — async entrypoint for the processing pipeline.

Currently runs synchronously inside queue_sync.  A future phase will
dispatch this as a Celery / ARQ task so the sync endpoint returns
immediately and processing happens in the background.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import ConnectorType
from app.services.ingestion_service import IngestionService


async def process_documents_for_connector(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    connector_id: UUID,
    connector_type: ConnectorType | None = None,
) -> int:
    """Process all unprocessed SourceDocuments for a connector.

    This is the entry point that queue_sync (or a future task runner)
    calls after persisting new documents.

    Returns the number of documents processed.
    """
    svc = IngestionService(session)
    return await svc.process_connector_documents(
        workspace_id=workspace_id,
        connector_id=connector_id,
        connector_type=connector_type,
    )
