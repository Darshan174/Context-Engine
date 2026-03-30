"""Slack connector — fetches messages and threads via the Slack Web API.

Uses the bot token obtained through the OAuth flow.  All public and
private channels the bot has been added to are eligible for sync.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from app.connectors.base import (
    AuthenticationError,
    BaseConnector,
    ConnectorError,
    NormalizedDocument,
    RateLimitError,
)

_SLACK_API = "https://slack.com/api"


class SlackConnector(BaseConnector):
    """Connector for Slack workspaces."""

    def __init__(self, access_token: str) -> None:
        super().__init__(access_token)
        self._headers = {"Authorization": f"Bearer {self._access_token}"}
        self._user_cache: dict[str, str] = {}

    # ── Public API (BaseConnector contract) ────────────────────────

    async def fetch_initial(self) -> AsyncIterator[NormalizedDocument]:
        """Fetch full message history from all accessible channels.

        Iterates through every channel the bot can see, pages through
        the full conversation history, and yields one NormalizedDocument
        per message.
        """
        async with self._http_client() as http:
            channels = await self._list_channels(http)
            for channel in channels:
                async for doc in self._fetch_channel_history(
                    http, channel, oldest=None
                ):
                    yield doc

    async def fetch_incremental(
        self, *, cursor: str | None = None
    ) -> AsyncIterator[NormalizedDocument]:
        """Fetch messages newer than *cursor* (a Unix timestamp string).

        If cursor is None, falls back to fetch_initial.
        """
        if cursor is None:
            async for doc in self.fetch_initial():
                yield doc
            return

        oldest = cursor
        async with self._http_client() as http:
            channels = await self._list_channels(http)
            for channel in channels:
                async for doc in self._fetch_channel_history(
                    http, channel, oldest=oldest
                ):
                    yield doc

    async def handle_webhook(self, payload: dict) -> list[NormalizedDocument]:
        """Handle a Slack Events API payload.

        Not yet implemented — returns empty list.  Future work will
        parse message events and convert them into NormalizedDocuments.
        """
        return []

    # ── Internal helpers ───────────────────────────────────────────

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self._headers,
            timeout=15,
        )

    async def _slack_get(
        self, http: httpx.AsyncClient, method: str, params: dict | None = None
    ) -> dict:
        """Call a Slack Web API method with standard error handling."""
        try:
            resp = await http.get(f"{_SLACK_API}/{method}", params=params or {})
        except httpx.HTTPError as exc:
            raise ConnectorError(
                f"Slack API {method} request failed: {exc.__class__.__name__}"
            ) from exc

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 5))
            raise RateLimitError(retry_after)

        if resp.status_code != 200:
            raise ConnectorError(f"Slack API {method} returned HTTP {resp.status_code}")

        body = resp.json()

        if not body.get("ok"):
            error = body.get("error", "unknown_error")
            if error in ("token_revoked", "invalid_auth", "not_authed"):
                raise AuthenticationError(f"Slack auth failed: {error}")
            raise ConnectorError(f"Slack API {method} error: {error}")

        return body

    async def _list_channels(self, http: httpx.AsyncClient) -> list[dict]:
        """Return all channels (public + private) the bot can see."""
        channels: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {
                "types": "public_channel,private_channel",
                "limit": 200,
                "exclude_archived": "true",
            }
            if cursor:
                params["cursor"] = cursor

            body = await self._slack_get(http, "conversations.list", params)
            channels.extend(body.get("channels", []))

            cursor = body.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return channels

    async def _fetch_channel_history(
        self,
        http: httpx.AsyncClient,
        channel: dict,
        *,
        oldest: str | None,
    ) -> AsyncIterator[NormalizedDocument]:
        """Page through a single channel's history and yield documents."""
        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)
        cursor: str | None = None

        while True:
            params: dict = {"channel": channel_id, "limit": 200}
            if oldest:
                params["oldest"] = oldest
                params["inclusive"] = "false"
            if cursor:
                params["cursor"] = cursor

            body = await self._slack_get(http, "conversations.history", params)

            for msg in body.get("messages", []):
                # Replies are emitted as part of the parent thread document.
                if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
                    continue

                document = await self._build_document(
                    http,
                    channel_id=channel_id,
                    channel_name=channel_name,
                    msg=msg,
                )
                if document is not None:
                    yield document

            cursor = body.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

    async def _build_document(
        self,
        http: httpx.AsyncClient,
        *,
        channel_id: str,
        channel_name: str,
        msg: dict,
    ) -> NormalizedDocument | None:
        text = msg.get("text", "").strip()
        if not text:
            return None

        ts = msg.get("ts", "")
        created_at = (
            datetime.fromtimestamp(float(ts), tz=timezone.utc)
            if ts
            else None
        )
        author = await self._resolve_author(http, msg)
        thread_ts = msg.get("thread_ts")
        content = text

        metadata = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "thread_ts": thread_ts,
            "message_type": msg.get("type", "message"),
        }

        if thread_ts == ts or msg.get("reply_count"):
            replies = await self._fetch_thread_replies(http, channel_id, ts)
            reply_lines: list[str] = []
            for reply in replies:
                if reply.get("ts") == ts:
                    continue

                reply_text = reply.get("text", "").strip()
                if not reply_text:
                    continue

                reply_author = await self._resolve_author(http, reply)
                prefix = reply_author or reply.get("user") or "unknown"
                reply_lines.append(f"{prefix}: {reply_text}")

            if reply_lines:
                content = f"{text}\n\nThread replies:\n" + "\n".join(reply_lines)
                metadata["reply_count"] = len(reply_lines)

        return NormalizedDocument(
            external_id=f"{channel_id}:{ts}",
            content=content,
            author=author,
            source_url=f"https://slack.com/archives/{channel_id}/p{ts.replace('.', '')}",
            created_at=created_at,
            metadata=metadata,
        )

    async def _fetch_thread_replies(
        self,
        http: httpx.AsyncClient,
        channel_id: str,
        thread_ts: str,
    ) -> list[dict]:
        replies: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {"channel": channel_id, "ts": thread_ts, "limit": 200}
            if cursor:
                params["cursor"] = cursor

            body = await self._slack_get(http, "conversations.replies", params)
            replies.extend(body.get("messages", []))

            cursor = body.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return replies

    async def _resolve_author(
        self,
        http: httpx.AsyncClient,
        msg: dict,
    ) -> str | None:
        if username := msg.get("username"):
            return username

        if bot_name := msg.get("bot_profile", {}).get("name"):
            return bot_name

        user_id = msg.get("user")
        if not user_id:
            return None

        cached = self._user_cache.get(user_id)
        if cached:
            return cached

        try:
            body = await self._slack_get(http, "users.info", {"user": user_id})
        except AuthenticationError:
            raise
        except RateLimitError:
            raise
        except ConnectorError:
            return user_id

        user = body.get("user", {})
        profile = user.get("profile", {})
        author = (
            profile.get("display_name")
            or profile.get("real_name")
            or user.get("real_name")
            or user.get("name")
            or user_id
        )
        self._user_cache[user_id] = author
        return author
