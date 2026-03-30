"""Base connector abstractions.

Every data-source connector (Slack, Notion, etc.) implements BaseConnector.
All connectors yield NormalizedDocument instances — a uniform shape that the
ingestion pipeline consumes regardless of the source.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    """Source-agnostic representation of an ingested document.

    Every connector converts its native payloads into this shape before
    handing off to the ingestion pipeline.
    """

    external_id: str
    """Unique identifier within the source (e.g. Slack ts, Notion page id)."""

    content: str
    """Full text content of the document."""

    author: str | None = None
    """Display name or user-id of the author, if available."""

    source_url: str | None = None
    """Deep-link back to the original item in the source system."""

    created_at: datetime | None = None
    """When the item was originally created in the source system."""

    metadata: dict = field(default_factory=dict)
    """Connector-specific metadata (channel name, page tags, etc.)."""


class ConnectorError(Exception):
    """Raised when a connector operation fails."""


class AuthenticationError(ConnectorError):
    """Raised when the connector's stored token is invalid or revoked."""


class RateLimitError(ConnectorError):
    """Raised when the source API rate-limits us."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limited{f' — retry after {retry_after}s' if retry_after else ''}"
        )


class BaseConnector(ABC):
    """Abstract base for all data-source connectors.

    Subclasses must implement the three fetch methods. The lifecycle is:

    1. ``fetch_initial``  — first-time full sync after OAuth completes
    2. ``fetch_incremental`` — subsequent syncs using a cursor/timestamp
    3. ``handle_webhook`` — real-time push events (optional)

    All fetch methods are async generators that yield NormalizedDocument.
    This lets the ingestion layer process documents as they arrive instead
    of buffering the entire source in memory.
    """

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    @abstractmethod
    async def fetch_initial(self) -> AsyncIterator[NormalizedDocument]:
        """Full historical fetch.  Called once on first sync."""
        ...

    @abstractmethod
    async def fetch_incremental(
        self, *, cursor: str | None = None
    ) -> AsyncIterator[NormalizedDocument]:
        """Delta fetch since *cursor*.  Called on subsequent syncs."""
        ...

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> list[NormalizedDocument]:
        """Process a real-time event push from the source.

        Returns a (possibly empty) list of documents extracted from
        the event.  Not all connectors support webhooks — those should
        return an empty list.
        """
        ...
