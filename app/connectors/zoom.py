"""Zoom connector — transcript-only recording ingestion.

This first pass intentionally stays narrow:
- fetch recorded meeting transcript files only
- normalize them into SourceDocuments
- no media download, diarization, or transcript generation pipeline
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx

from app.config import settings
from app.connectors.base import (
    AuthenticationError,
    BaseConnector,
    ConnectorError,
    NormalizedDocument,
    RateLimitError,
)


class ZoomConnector(BaseConnector):
    """Connector for Zoom cloud recording transcripts."""

    def __init__(self, access_token: str) -> None:
        super().__init__(access_token)
        self._headers = {"Authorization": f"Bearer {self._access_token}"}
        self._api_base_url = settings.zoom_api_base_url.rstrip("/")

    async def fetch_initial(self) -> AsyncIterator[NormalizedDocument]:
        async with self._http_client() as http:
            async for document in self._fetch_transcripts(http, since=None):
                yield document

    async def fetch_incremental(
        self, *, cursor: str | None = None
    ) -> AsyncIterator[NormalizedDocument]:
        since, last_external_id = self._cursor_to_state(cursor)
        async with self._http_client() as http:
            async for document in self._fetch_transcripts(
                http,
                since=since,
                last_external_id=last_external_id,
            ):
                yield document

    async def handle_webhook(self, payload: dict) -> list[NormalizedDocument]:
        return []

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=self._headers,
            timeout=30,
        )

    async def _fetch_transcripts(
        self,
        http: httpx.AsyncClient,
        *,
        since: datetime | None,
        last_external_id: str | None = None,
    ) -> AsyncIterator[NormalizedDocument]:
        next_page_token: str | None = None

        while True:
            params: dict[str, Any] = {"page_size": 100}
            if next_page_token:
                params["next_page_token"] = next_page_token
            if since is not None:
                params["from"] = since.date().isoformat()
                params["to"] = datetime.now(timezone.utc).date().isoformat()

            body = await self._zoom_get(http, "/users/me/recordings", params=params)
            for meeting in body.get("meetings", []):
                async for document in self._meeting_documents(
                    http,
                    meeting,
                    since=since,
                    last_external_id=last_external_id,
                ):
                    yield document

            next_page_token = body.get("next_page_token")
            if not next_page_token:
                break

    async def _meeting_documents(
        self,
        http: httpx.AsyncClient,
        meeting: dict[str, Any],
        *,
        since: datetime | None,
        last_external_id: str | None,
    ) -> AsyncIterator[NormalizedDocument]:
        for transcript_file in meeting.get("recording_files", []):
            if not self._is_transcript_file(transcript_file):
                continue

            created_at = self._recording_datetime(meeting, transcript_file)
            transcript_file_id = str(transcript_file.get("id") or "")
            if since is not None and created_at is not None:
                if created_at < since:
                    continue
                if (
                    created_at == since
                    and last_external_id
                    and transcript_file_id
                    and transcript_file_id <= last_external_id
                ):
                    continue

            transcript_text = await self._download_transcript(http, transcript_file)
            document = self._to_normalized_document(
                meeting,
                transcript_file,
                transcript_text,
            )
            if document is None:
                continue
            if since is not None and document.created_at is not None:
                if document.created_at < since:
                    continue
                if (
                    document.created_at == since
                    and last_external_id
                    and document.external_id <= last_external_id
                ):
                    continue
            yield document

    async def _zoom_get(
        self,
        http: httpx.AsyncClient,
        path_or_url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = (
            path_or_url
            if path_or_url.startswith("http://") or path_or_url.startswith("https://")
            else f"{self._api_base_url}{path_or_url}"
        )

        try:
            response = await http.get(url, params=params or {})
        except httpx.HTTPError as exc:
            raise ConnectorError(
                f"Zoom API request failed: {exc.__class__.__name__}"
            ) from exc

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 5))
            raise RateLimitError(retry_after)

        if response.status_code in {401, 403}:
            raise AuthenticationError("Zoom auth failed")

        if response.status_code != 200:
            raise ConnectorError(f"Zoom API returned HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise ConnectorError("Zoom API returned malformed JSON") from exc

    async def _download_transcript(
        self,
        http: httpx.AsyncClient,
        transcript_file: dict[str, Any],
    ) -> str:
        url = transcript_file.get("download_url")
        if not url:
            return ""

        try:
            response = await http.get(url)
        except httpx.HTTPError as exc:
            raise ConnectorError(
                f"Zoom transcript download failed: {exc.__class__.__name__}"
            ) from exc

        if response.status_code in {401, 403}:
            raise AuthenticationError("Zoom auth failed")

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", 5))
            raise RateLimitError(retry_after)

        if response.status_code != 200:
            raise ConnectorError(
                f"Zoom transcript download returned HTTP {response.status_code}"
            )

        return self._normalize_transcript_text(response.text)

    @classmethod
    def _to_normalized_document(
        cls,
        meeting: dict[str, Any],
        transcript_file: dict[str, Any],
        transcript_text: str,
    ) -> NormalizedDocument | None:
        clean_text = cls._normalize_transcript_text(transcript_text)
        if not clean_text:
            return None

        meeting_id = meeting.get("id") or transcript_file.get("meeting_id")
        meeting_uuid = meeting.get("uuid")
        meeting_topic = meeting.get("topic") or "Untitled meeting"
        host = (
            meeting.get("host")
            or meeting.get("host_email")
            or meeting.get("host_name")
            or meeting.get("host_id")
        )
        participants = cls._participant_names(meeting.get("participants"))
        created_at = cls._recording_datetime(meeting, transcript_file)
        source_url = (
            transcript_file.get("play_url")
            or meeting.get("share_url")
            or transcript_file.get("download_url")
        )
        transcript_file_id = transcript_file.get("id")

        parts = [f"Meeting: {meeting_topic}"]
        if host:
            parts.append(f"Host: {host}")
        if participants:
            parts.append(f"Participants: {', '.join(participants)}")
        if created_at is not None:
            parts.append(f"Recording Date: {created_at.isoformat()}")
        parts.extend(["", clean_text])

        metadata = {
            "meeting_id": meeting_id,
            "meeting_uuid": meeting_uuid,
            "meeting_topic": meeting_topic,
            "host": host,
            "participants": participants,
            "transcript_timestamp": transcript_file.get("recording_start")
            or meeting.get("start_time"),
            "recording_date": created_at.date().isoformat()
            if created_at is not None
            else None,
            "transcript_file_id": transcript_file_id,
            "recording_start": transcript_file.get("recording_start"),
            "recording_end": transcript_file.get("recording_end"),
            "source_type": "zoom_transcript",
        }

        external_suffix = transcript_file_id or transcript_file.get("recording_start") or "transcript"
        external_id = f"zoom:{meeting_id or meeting_uuid or 'meeting'}:{external_suffix}"

        return NormalizedDocument(
            external_id=external_id,
            content="\n".join(parts).strip(),
            author=host,
            source_url=source_url,
            created_at=created_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], "")},
        )

    @staticmethod
    def _is_transcript_file(recording_file: dict[str, Any]) -> bool:
        recording_type = str(recording_file.get("recording_type", "")).lower()
        file_type = str(recording_file.get("file_type", "")).lower()
        extension = str(recording_file.get("file_extension", "")).lower()

        return (
            "transcript" in recording_type
            or file_type == "transcript"
            or extension in {"vtt", "txt"}
        )

    @staticmethod
    def _normalize_transcript_text(text: str) -> str:
        cleaned_lines: list[str] = []
        for raw_line in text.splitlines():
            line = re.sub(r"<[^>]+>", "", raw_line).strip()
            if not line or line == "WEBVTT":
                continue
            if re.match(r"^\d+$", line):
                continue
            if re.match(
                r"^\d{2}:\d{2}(?::\d{2})?\.\d{3}\s+-->\s+\d{2}:\d{2}(?::\d{2})?\.\d{3}",
                line,
            ):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines).strip()

    @classmethod
    def _recording_datetime(
        cls,
        meeting: dict[str, Any],
        transcript_file: dict[str, Any],
    ) -> datetime | None:
        for value in (
            transcript_file.get("recording_start"),
            meeting.get("start_time"),
            meeting.get("recording_start"),
        ):
            parsed = cls._parse_datetime(value)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _participant_names(raw_participants: Any) -> list[str]:
        if not isinstance(raw_participants, list):
            return []

        names: list[str] = []
        for participant in raw_participants:
            if isinstance(participant, str):
                value = participant.strip()
            elif isinstance(participant, dict):
                value = (
                    participant.get("name")
                    or participant.get("display_name")
                    or participant.get("email")
                    or participant.get("user_email")
                    or participant.get("id")
                    or ""
                ).strip()
            else:
                value = ""

            if value:
                names.append(value)

        return names

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _cursor_to_state(cursor: str | None) -> tuple[datetime | None, str | None]:
        if not cursor:
            return None, None
        try:
            payload = json.loads(cursor)
            if isinstance(payload, dict) and payload.get("recording_start"):
                return (
                    datetime.fromisoformat(
                        str(payload["recording_start"]).replace("Z", "+00:00")
                    ),
                    str(payload.get("external_id") or ""),
                )
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        try:
            return datetime.fromtimestamp(float(cursor), tz=timezone.utc), None
        except (TypeError, ValueError):
            return None, None
