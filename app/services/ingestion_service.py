"""Ingestion pipeline — processes raw SourceDocuments into knowledge graph facts.

Phase 1 uses a rule-based stub extractor.  A future phase will swap in
an LLM-backed extractor without changing the service interface.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Component, ComponentSource, KnowledgeModel
from app.models.source import ConnectorType, SourceDocument


class IngestionServiceError(Exception):
    """Base ingestion error."""


class IngestionService:
    """Reads unprocessed SourceDocuments and creates knowledge graph entries."""

    _AUTO_MODEL_NAMES: dict[ConnectorType, tuple[str, str]] = {
        ConnectorType.SLACK: ("Slack Insights", "Auto-generated from Slack connector sync"),
        ConnectorType.NOTION: ("Notion Insights", "Auto-generated from Notion connector sync"),
    }
    _FALLBACK_MODEL = ("Connector Insights", "Auto-generated from connector sync")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def process_connector_documents(
        self,
        workspace_id: UUID,
        connector_id: UUID,
        connector_type: ConnectorType | None = None,
    ) -> int:
        """Process all unprocessed SourceDocuments for a specific connector.

        Returns the number of documents processed.
        """
        docs = await self._select_unprocessed(connector_id)
        if not docs:
            return 0

        model_name, model_desc = self._AUTO_MODEL_NAMES.get(
            connector_type, self._FALLBACK_MODEL
        )
        model = await self._get_or_create_model(workspace_id, model_name, model_desc)

        processed = 0
        for doc in docs:
            facts = self._extract_facts(doc)
            for name, value, confidence in facts:
                component = await self._upsert_component(
                    model, name, value, confidence, doc,
                )
                await self._link_source(component, doc)

            doc.processed_at = datetime.now(timezone.utc)
            processed += 1

        await self.session.flush()
        return processed

    # ── Private helpers ───────────────────────────────────────────

    async def _select_unprocessed(
        self, connector_id: UUID
    ) -> list[SourceDocument]:
        """Return SourceDocuments for this connector that have not been processed yet.

        Uses populate_existing so that ORM objects are refreshed from the
        DB — necessary because _persist_documents uses Core-level SQL
        that bypasses the ORM identity map when resetting processed_at.
        """
        result = await self.session.scalars(
            select(SourceDocument)
            .where(
                SourceDocument.connector_id == connector_id,
                SourceDocument.processed_at.is_(None),
            )
            .order_by(SourceDocument.ingested_at)
            .execution_options(populate_existing=True)
        )
        return list(result)

    async def _get_or_create_model(
        self, workspace_id: UUID, model_name: str, model_desc: str,
    ) -> KnowledgeModel:
        """Return the auto-generated KnowledgeModel, creating it if needed."""
        model = await self.session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace_id,
                KnowledgeModel.name == model_name,
            )
        )
        if model is None:
            model = KnowledgeModel(
                workspace_id=workspace_id,
                name=model_name,
                description=model_desc,
                auto_generated=True,
            )
            self.session.add(model)
            await self.session.flush()
        return model

    async def _upsert_component(
        self,
        model: KnowledgeModel,
        name: str,
        value: str,
        confidence: float,
        doc: SourceDocument,
    ) -> Component:
        """Create a component or update it if one with the same name exists."""
        existing = await self.session.scalar(
            select(Component).where(
                Component.model_id == model.id,
                Component.name == name,
            )
        )
        if existing is not None:
            existing.value = value
            existing.confidence = max(existing.confidence, confidence)
            existing.last_verified_at = datetime.now(timezone.utc)
            existing.is_stale = False
            existing.authority_source = doc.source_url
            await self.session.flush()
            return existing

        component = Component(
            model_id=model.id,
            name=name,
            value=value,
            confidence=confidence,
            authority_source=doc.source_url,
        )
        self.session.add(component)
        await self.session.flush()
        return component

    async def _link_source(
        self, component: Component, doc: SourceDocument
    ) -> None:
        """Create a ComponentSource link if it doesn't already exist."""
        exists = await self.session.scalar(
            select(ComponentSource.component_id).where(
                ComponentSource.component_id == component.id,
                ComponentSource.source_document_id == doc.id,
            )
        )
        if exists is not None:
            return

        link = ComponentSource(
            component_id=component.id,
            source_document_id=doc.id,
            extraction_context=f"Extracted from {doc.connector_type.value} "
            f"document {doc.external_id}",
        )
        self.session.add(link)
        await self.session.flush()

    # ── Stub extractor ────────────────────────────────────────────

    @staticmethod
    def _extract_facts(
        doc: SourceDocument,
    ) -> list[tuple[str, str, float]]:
        """Rule-based fact extraction from a SourceDocument.

        Returns a list of (name, value, confidence) tuples.  This is a
        placeholder that extracts obvious patterns; the LLM extractor
        will replace it in a later phase.
        """
        facts: list[tuple[str, str, float]] = []
        content = doc.content
        meta = doc.metadata_json or {}
        channel = meta.get("channel_name", "unknown")

        # Pattern: "decision: <text>" or "decided: <text>"
        for m in re.finditer(
            r"(?:decision|decided)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Decision in #{channel}",
                m.group(1).strip(),
                0.75,
            ))

        # Pattern: "action item: <text>" or "todo: <text>" or "AI: <text>"
        for m in re.finditer(
            r"(?:action item|todo|AI)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Action Item in #{channel}",
                m.group(1).strip(),
                0.70,
            ))

        # Pattern: "blocker: <text>" or "blocked by: <text>"
        for m in re.finditer(
            r"(?:blocker|blocked by)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Blocker in #{channel}",
                m.group(1).strip(),
                0.80,
            ))

        # Fallback: if no structured facts found, create a channel summary
        # entry from messages with thread replies (likely important discussions)
        if not facts and meta.get("reply_count"):
            author = doc.author or "Unknown"
            preview = content[:200].replace("\n", " ")
            facts.append((
                f"Discussion in #{channel}",
                f"{author}: {preview}",
                0.55,
            ))

        return facts
