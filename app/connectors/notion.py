"""Notion connector — fetches pages and their content via the Notion API.

Uses dlt as the extraction substrate.  The Notion integration token is
stored encrypted in the Connector row (same as Slack's OAuth token).

Limitations (first pass):
- Incremental sync does a full re-fetch; true cursor-based delta sync
  is not yet implemented because Notion's search API lacks a reliable
  "modified after" filter.
- Block fetching is single-level (no recursive child-block expansion).
- Webhooks are not supported (Notion has no push API; polling only).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator

import dlt
import requests

from app.connectors.base import (
    AuthenticationError,
    BaseConnector,
    ConnectorError,
    NormalizedDocument,
    RateLimitError,
)

_NOTION_API = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


# ── dlt resource (the extraction substrate) ──────────────────────────


@dlt.resource(name="notion_pages", write_disposition="replace")
def notion_pages_resource(api_key: str, *, page_size: int = 100):
    """dlt resource that yields Notion page dicts with their content blocks.

    Uses Notion's ``/search`` endpoint to list all pages the integration
    can access, then fetches first-level blocks for each page.
    """
    headers = _notion_headers(api_key)
    start_cursor: str | None = None

    while True:
        body: dict = {
            "filter": {"value": "page", "property": "object"},
            "page_size": page_size,
        }
        if start_cursor:
            body["start_cursor"] = start_cursor

        data = _notion_post(headers, "search", body)

        for page in data.get("results", []):
            page["_blocks"] = _fetch_page_blocks(headers, page["id"])
            yield page

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")


# ── Notion API helpers (synchronous, used inside dlt resource) ───────


def _notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": _NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _notion_post(headers: dict, endpoint: str, body: dict) -> dict:
    """POST to the Notion API with standard error handling."""
    try:
        resp = requests.post(
            f"{_NOTION_API}/{endpoint}",
            headers=headers,
            json=body,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ConnectorError(f"Notion API request failed: {exc}") from exc

    if resp.status_code == 401:
        raise AuthenticationError("Notion API token is invalid or revoked")
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", 5))
        raise RateLimitError(retry_after)
    if resp.status_code != 200:
        raise ConnectorError(f"Notion API returned HTTP {resp.status_code}")

    return resp.json()


def _fetch_page_blocks(headers: dict, page_id: str) -> list[dict]:
    """Fetch first-level content blocks for a Notion page."""
    blocks: list[dict] = []
    start_cursor: str | None = None

    while True:
        params: dict = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor

        try:
            resp = requests.get(
                f"{_NOTION_API}/blocks/{page_id}/children",
                headers=headers,
                params=params,
                timeout=30,
            )
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        data = resp.json()
        blocks.extend(data.get("results", []))

        if not data.get("has_more"):
            break
        start_cursor = data.get("next_cursor")

    return blocks


# ── Content extraction helpers ───────────────────────────────────────


def extract_page_title(page: dict) -> str:
    """Pull the title property from a Notion page object."""
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(
                rt.get("plain_text", "") for rt in prop.get("title", [])
            )
    return "Untitled"


def extract_block_text(block: dict) -> str:
    """Extract plain text from a single Notion block."""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})
    rich_text = block_data.get("rich_text", [])
    text = "".join(rt.get("plain_text", "") for rt in rich_text)

    if block_type in ("heading_1", "heading_2", "heading_3"):
        return f"# {text}" if text else ""
    if block_type == "to_do":
        checked = block_data.get("checked", False)
        marker = "[x]" if checked else "[ ]"
        return f"{marker} {text}" if text else ""
    if block_type in ("bulleted_list_item", "numbered_list_item"):
        return f"- {text}" if text else ""
    if block_type == "code":
        lang = block_data.get("language", "")
        return f"```{lang}\n{text}\n```" if text else ""

    return text


def page_to_text(page: dict) -> str:
    """Assemble a Notion page and its blocks into a single text string."""
    title = extract_page_title(page)
    parts = [title] if title and title != "Untitled" else []

    for block in page.get("_blocks", []):
        text = extract_block_text(block)
        if text:
            parts.append(text)

    return "\n\n".join(parts)


def _extract_author(page: dict) -> str | None:
    """Best-effort author extraction from Notion page metadata."""
    created_by = page.get("created_by", {})
    if created_by.get("type") == "person":
        return created_by.get("person", {}).get("email")
    return created_by.get("name") or created_by.get("id")


# ── Connector implementation ─────────────────────────────────────────


class NotionConnector(BaseConnector):
    """Connector for Notion workspaces, backed by dlt."""

    async def fetch_initial(self) -> AsyncIterator[NormalizedDocument]:
        """Fetch all pages the integration can access.

        Runs the dlt resource synchronously in a thread to avoid
        blocking the event loop.
        """
        pages: list[dict] = await asyncio.to_thread(
            lambda: list(notion_pages_resource(self._access_token))
        )
        for page in pages:
            doc = self._to_normalized_document(page)
            if doc is not None:
                yield doc

    async def fetch_incremental(
        self, *, cursor: str | None = None
    ) -> AsyncIterator[NormalizedDocument]:
        """Incremental fetch.

        **Limitation**: Notion's search API does not support a reliable
        "modified since" filter, so this currently performs a full
        re-fetch identical to ``fetch_initial``.  The persistence layer's
        upsert-on-(connector_id, external_id) ensures no duplicates are
        created.  The upsert only resets ``processed_at`` when the
        content column actually differs, so unchanged pages are not
        re-extracted.
        """
        async for doc in self.fetch_initial():
            yield doc

    async def handle_webhook(self, payload: dict) -> list[NormalizedDocument]:
        """Notion has no push/webhook API — returns empty list."""
        return []

    # ── Internal ─────────────────────────────────────────────────────

    @staticmethod
    def _to_normalized_document(page: dict) -> NormalizedDocument | None:
        """Convert a Notion page dict (with _blocks) to a NormalizedDocument."""
        page_id = page.get("id", "")
        content = page_to_text(page)
        if not content.strip():
            return None

        created_time = page.get("created_time")
        created_at = None
        if created_time:
            created_at = datetime.fromisoformat(
                created_time.replace("Z", "+00:00")
            )

        last_edited = page.get("last_edited_time")

        return NormalizedDocument(
            external_id=f"notion:{page_id}",
            content=content,
            author=_extract_author(page),
            source_url=page.get("url"),
            created_at=created_at,
            metadata={
                "page_id": page_id,
                "last_edited_time": last_edited,
                "source_type": "notion",
            },
        )
