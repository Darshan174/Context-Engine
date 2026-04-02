"""GitHub connector for high-signal engineering artifacts.

Current scope:
- repository-scoped polling via the REST API
- issues and pull requests
- issue comments, pull-request reviews, and review comments
- explicit issue / pull-request / commit references captured in metadata

This intentionally stops short of broad repository mirroring.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Sequence

import httpx

from app.config import settings
from app.connectors.base import (
    AuthenticationError,
    BaseConnector,
    ConnectorError,
    NormalizedDocument,
    RateLimitError,
)

_PULL_REFERENCE_RE = re.compile(
    r"(?:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#|(?:PR|pull request)\s+#?)(?P<number>\d+)",
    re.IGNORECASE,
)
_PULL_URL_RE = re.compile(
    r"https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)
_ISSUE_REFERENCE_RE = re.compile(
    r"(?:(?:issue|issues|fixes|fixed|fix|closes|closed|close|resolves|resolved|resolve|refs|references|referenced)\s+)"
    r"(?:(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#|#)(?P<number>\d+)",
    re.IGNORECASE,
)
_ISSUE_URL_RE = re.compile(
    r"https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)",
    re.IGNORECASE,
)
_COMMIT_REFERENCE_RE = re.compile(r"\b(?P<sha>[0-9a-f]{7,40})\b", re.IGNORECASE)
_COMMIT_URL_RE = re.compile(
    r"https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/commit/(?P<sha>[0-9a-f]{7,40})",
    re.IGNORECASE,
)


class GitHubConnector(BaseConnector):
    """Connector for repository issues, PRs, and review discussion."""

    def __init__(self, access_token: str, *, repositories: Sequence[str]) -> None:
        super().__init__(access_token)
        self._repositories = [repo.strip().lower() for repo in repositories if repo.strip()]
        self._headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/vnd.github+json",
        }
        self._api_base_url = settings.github_api_base_url.rstrip("/")

    async def fetch_initial(self) -> AsyncIterator[NormalizedDocument]:
        async with self._http_client() as http:
            for repo in self._repositories:
                async for document in self._fetch_repository_activity(http, repo, since=None):
                    yield document

    async def fetch_incremental(
        self,
        *,
        cursor: str | None = None,
    ) -> AsyncIterator[NormalizedDocument]:
        since, last_external_id = self._cursor_to_state(cursor)
        async with self._http_client() as http:
            for repo in self._repositories:
                async for document in self._fetch_repository_activity(
                    http,
                    repo,
                    since=since,
                    last_external_id=last_external_id,
                ):
                    yield document

    async def handle_webhook(self, payload: dict) -> list[NormalizedDocument]:
        return []

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers, timeout=30)

    async def _fetch_repository_activity(
        self,
        http: httpx.AsyncClient,
        repo_full_name: str,
        *,
        since: datetime | None,
        last_external_id: str | None = None,
    ) -> AsyncIterator[NormalizedDocument]:
        params: dict[str, Any] = {
            "state": "all",
            "sort": "updated",
            "direction": "asc",
        }
        if since is not None:
            params["since"] = since.isoformat().replace("+00:00", "Z")

        async for item in self._paginate_list(http, f"/repos/{repo_full_name}/issues", params=params):
            parent_document = self._to_normalized_document(repo_full_name, item)
            parent_updated_at = (
                parent_document.created_at if parent_document is not None else self._parse_datetime(
                    item.get("updated_at")
                )
            )
            parent_external_id = (
                parent_document.external_id if parent_document is not None else None
            )
            if (
                since is not None
                and parent_updated_at is not None
                and parent_external_id is not None
            ):
                if parent_updated_at < since:
                    continue
                if parent_updated_at == since and last_external_id:
                    if parent_external_id <= last_external_id:
                        continue

            if parent_document is not None:
                yield parent_document

            async for child in self._fetch_child_documents(http, repo_full_name, item):
                yield child

    async def _fetch_child_documents(
        self,
        http: httpx.AsyncClient,
        repo_full_name: str,
        item: dict[str, Any],
    ) -> AsyncIterator[NormalizedDocument]:
        number = item.get("number")
        if number is None:
            return

        async for comment in self._paginate_list(
            http,
            f"/repos/{repo_full_name}/issues/{number}/comments",
            params={"sort": "updated", "direction": "asc"},
        ):
            document = self._to_issue_comment_document(repo_full_name, item, comment)
            if document is not None:
                yield document

        if not item.get("pull_request"):
            return

        async for review in self._paginate_list(
            http,
            f"/repos/{repo_full_name}/pulls/{number}/reviews",
            params=None,
        ):
            document = self._to_pull_review_document(repo_full_name, item, review)
            if document is not None:
                yield document

        async for comment in self._paginate_list(
            http,
            f"/repos/{repo_full_name}/pulls/{number}/comments",
            params={"sort": "updated", "direction": "asc"},
        ):
            document = self._to_pull_review_comment_document(repo_full_name, item, comment)
            if document is not None:
                yield document

    async def _paginate_list(
        self,
        http: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any] | None,
    ) -> AsyncIterator[dict[str, Any]]:
        page = 1
        while True:
            page_params = {"per_page": 100, "page": page, **(params or {})}
            payload = await self._github_get(http, path, params=page_params)
            if not payload:
                break
            for item in payload:
                if isinstance(item, dict):
                    yield item
            if len(payload) < 100:
                break
            page += 1

    async def _github_get(
        self,
        http: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            response = await http.get(f"{self._api_base_url}{path}", params=params or {})
        except httpx.HTTPError as exc:
            raise ConnectorError(
                f"GitHub API request failed: {exc.__class__.__name__}"
            ) from exc

        if response.status_code == 401:
            raise AuthenticationError("GitHub auth failed")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            retry_after = self._retry_after_seconds(response.headers.get("X-RateLimit-Reset"))
            raise RateLimitError(retry_after)
        if response.status_code == 403:
            raise AuthenticationError("GitHub auth failed")
        if response.status_code == 429:
            retry_after = self._retry_after_seconds(response.headers.get("Retry-After"))
            raise RateLimitError(retry_after)
        if response.status_code != 200:
            raise ConnectorError(f"GitHub API returned HTTP {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ConnectorError("GitHub API returned malformed JSON") from exc
        if not isinstance(payload, list):
            raise ConnectorError("GitHub API returned an unexpected payload shape")
        return payload

    @classmethod
    def _to_normalized_document(
        cls,
        repo_full_name: str,
        item: dict[str, Any],
    ) -> NormalizedDocument | None:
        number = item.get("number")
        if number is None:
            return None
        title = (item.get("title") or "").strip()
        body = (item.get("body") or "").strip()
        if not title and not body:
            return None

        kind = "pull_request" if item.get("pull_request") else "issue"
        labels = [
            str(label.get("name")).strip()
            for label in item.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        ]
        assignees = [
            str(assignee.get("login")).strip()
            for assignee in item.get("assignees", [])
            if isinstance(assignee, dict) and assignee.get("login")
        ]
        author = cls._login_name(item.get("user"))
        updated_at = cls._parse_datetime(item.get("updated_at"))
        opened_at = cls._parse_datetime(item.get("created_at"))
        closed_at = cls._parse_datetime(item.get("closed_at"))
        merged_at = cls._parse_datetime(
            ((item.get("pull_request") or {}).get("merged_at"))
            if isinstance(item.get("pull_request"), dict)
            else None
        )
        references = cls._extract_references(repo_full_name, body)

        lines = [
            f"Repository: {repo_full_name}",
            f"{'Pull Request' if kind == 'pull_request' else 'Issue'} #{number}: {title or 'Untitled'}",
            f"State: {item.get('state') or 'unknown'}",
        ]
        if labels:
            lines.append(f"Labels: {', '.join(labels)}")
        if assignees:
            lines.append(f"Assignees: {', '.join(assignees)}")
        if opened_at is not None:
            lines.append(f"Opened At: {opened_at.isoformat()}")
        if closed_at is not None:
            lines.append(f"Closed At: {closed_at.isoformat()}")
        if merged_at is not None:
            lines.append(f"Merged At: {merged_at.isoformat()}")
        cls._append_reference_lines(lines, references)
        if body:
            lines.extend(["", body])

        external_id = f"github:{repo_full_name}:{kind}:{number}"
        metadata = {
            "repo_full_name": repo_full_name,
            "number": number,
            "title": title,
            "item_type": kind,
            "state": item.get("state"),
            "labels": labels,
            "assignees": assignees,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "closed_at": item.get("closed_at"),
            "merged_at": ((item.get("pull_request") or {}).get("merged_at"))
            if isinstance(item.get("pull_request"), dict)
            else None,
            "pull_request_references": references["pull_requests"],
            "issue_references": references["issues"],
            "commit_references": references["commits"],
            "source_type": f"github_{kind}",
        }

        return NormalizedDocument(
            external_id=external_id,
            content="\n".join(lines).strip(),
            author=author,
            source_url=item.get("html_url"),
            created_at=updated_at or opened_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], "")},
        )

    @classmethod
    def _to_issue_comment_document(
        cls,
        repo_full_name: str,
        parent_item: dict[str, Any],
        comment: dict[str, Any],
    ) -> NormalizedDocument | None:
        comment_id = comment.get("id")
        body = (comment.get("body") or "").strip()
        if comment_id is None or not body:
            return None
        parent_kind = "pull_request" if parent_item.get("pull_request") else "issue"
        parent_number = parent_item.get("number")
        parent_title = (parent_item.get("title") or "").strip()
        author = cls._login_name(comment.get("user"))
        updated_at = cls._parse_datetime(comment.get("updated_at"))
        created_at = cls._parse_datetime(comment.get("created_at"))
        references = cls._extract_references(repo_full_name, body)
        title = (
            f"Comment on {'Pull Request' if parent_kind == 'pull_request' else 'Issue'} "
            f"#{parent_number}: {parent_title or 'Untitled'}"
        )
        lines = [
            f"Repository: {repo_full_name}",
            title,
        ]
        if author:
            lines.append(f"Comment Author: {author}")
        if created_at is not None:
            lines.append(f"Commented At: {created_at.isoformat()}")
        cls._append_reference_lines(lines, references)
        lines.extend(["", body])

        metadata = {
            "repo_full_name": repo_full_name,
            "title": title,
            "item_type": "issue_comment",
            "parent_item_type": parent_kind,
            "parent_number": parent_number,
            "parent_title": parent_title,
            "parent_external_id": f"github:{repo_full_name}:{parent_kind}:{parent_number}",
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "pull_request_references": references["pull_requests"],
            "issue_references": references["issues"],
            "commit_references": references["commits"],
            "source_type": "github_issue_comment",
        }
        return NormalizedDocument(
            external_id=f"github:{repo_full_name}:issue_comment:{comment_id}",
            content="\n".join(lines).strip(),
            author=author,
            source_url=comment.get("html_url") or comment.get("url"),
            created_at=updated_at or created_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], "")},
        )

    @classmethod
    def _to_pull_review_document(
        cls,
        repo_full_name: str,
        parent_item: dict[str, Any],
        review: dict[str, Any],
    ) -> NormalizedDocument | None:
        review_id = review.get("id")
        state = (review.get("state") or "").strip()
        body = (review.get("body") or "").strip()
        if review_id is None or (not body and not state):
            return None

        parent_number = parent_item.get("number")
        parent_title = (parent_item.get("title") or "").strip()
        author = cls._login_name(review.get("user"))
        submitted_at = cls._parse_datetime(review.get("submitted_at"))
        created_at = cls._parse_datetime(review.get("submitted_at")) or cls._parse_datetime(
            review.get("body_updated_at")
        )
        references = cls._extract_references(repo_full_name, body)
        cls._append_commit_reference(references, review.get("commit_id"))
        title = f"Review on Pull Request #{parent_number}: {parent_title or 'Untitled'}"
        lines = [
            f"Repository: {repo_full_name}",
            title,
            f"Review State: {state or 'COMMENTED'}",
        ]
        if author:
            lines.append(f"Reviewer: {author}")
        if submitted_at is not None:
            lines.append(f"Reviewed At: {submitted_at.isoformat()}")
        cls._append_reference_lines(lines, references)
        cls._append_review_context_lines(
            lines,
            commit_id=review.get("commit_id"),
        )
        if body:
            lines.extend(["", body])

        metadata = {
            "repo_full_name": repo_full_name,
            "title": title,
            "item_type": "pull_request_review",
            "parent_item_type": "pull_request",
            "parent_number": parent_number,
            "parent_title": parent_title,
            "parent_external_id": f"github:{repo_full_name}:pull_request:{parent_number}",
            "review_state": state or None,
            "commit_id": review.get("commit_id"),
            "created_at": review.get("submitted_at"),
            "updated_at": review.get("submitted_at"),
            "pull_request_references": references["pull_requests"],
            "issue_references": references["issues"],
            "commit_references": references["commits"],
            "source_type": "github_pull_request_review",
        }
        return NormalizedDocument(
            external_id=f"github:{repo_full_name}:pull_review:{review_id}",
            content="\n".join(lines).strip(),
            author=author,
            source_url=review.get("html_url") or review.get("pull_request_url"),
            created_at=submitted_at or created_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], "")},
        )

    @classmethod
    def _to_pull_review_comment_document(
        cls,
        repo_full_name: str,
        parent_item: dict[str, Any],
        comment: dict[str, Any],
    ) -> NormalizedDocument | None:
        comment_id = comment.get("id")
        body = (comment.get("body") or "").strip()
        if comment_id is None or not body:
            return None

        parent_number = parent_item.get("number")
        parent_title = (parent_item.get("title") or "").strip()
        author = cls._login_name(comment.get("user"))
        updated_at = cls._parse_datetime(comment.get("updated_at"))
        created_at = cls._parse_datetime(comment.get("created_at"))
        references = cls._extract_references(repo_full_name, body)
        cls._append_commit_reference(references, comment.get("commit_id"))
        cls._append_commit_reference(references, comment.get("original_commit_id"))
        title = f"Review Comment on Pull Request #{parent_number}: {parent_title or 'Untitled'}"
        lines = [
            f"Repository: {repo_full_name}",
            title,
        ]
        if author:
            lines.append(f"Comment Author: {author}")
        if created_at is not None:
            lines.append(f"Commented At: {created_at.isoformat()}")
        cls._append_reference_lines(lines, references)
        cls._append_review_context_lines(
            lines,
            commit_id=comment.get("commit_id"),
            original_commit_id=comment.get("original_commit_id"),
            path=comment.get("path"),
            line=comment.get("line"),
            side=comment.get("side"),
        )
        lines.extend(["", body])

        metadata = {
            "repo_full_name": repo_full_name,
            "title": title,
            "item_type": "pull_request_review_comment",
            "parent_item_type": "pull_request",
            "parent_number": parent_number,
            "parent_title": parent_title,
            "parent_external_id": f"github:{repo_full_name}:pull_request:{parent_number}",
            "commit_id": comment.get("commit_id"),
            "original_commit_id": comment.get("original_commit_id"),
            "path": comment.get("path"),
            "line": comment.get("line"),
            "side": comment.get("side"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "pull_request_references": references["pull_requests"],
            "issue_references": references["issues"],
            "commit_references": references["commits"],
            "source_type": "github_pull_request_review_comment",
        }
        return NormalizedDocument(
            external_id=f"github:{repo_full_name}:pull_review_comment:{comment_id}",
            content="\n".join(lines).strip(),
            author=author,
            source_url=comment.get("html_url") or comment.get("pull_request_url"),
            created_at=updated_at or created_at,
            metadata={k: v for k, v in metadata.items() if v not in (None, [], "")},
        )

    @classmethod
    def _extract_references(cls, repo_full_name: str, text: str) -> dict[str, list[str]]:
        pull_requests: list[str] = []
        issues: list[str] = []
        commits: list[str] = []

        def add_unique(values: list[str], candidate: str) -> None:
            if candidate not in values:
                values.append(candidate)

        for match in _PULL_REFERENCE_RE.finditer(text or ""):
            repo = (match.group("repo") or repo_full_name).lower()
            add_unique(pull_requests, f"{repo}#{match.group('number')}")
        for match in _PULL_URL_RE.finditer(text or ""):
            add_unique(pull_requests, f"{match.group('repo').lower()}#{match.group('number')}")
        for match in _ISSUE_REFERENCE_RE.finditer(text or ""):
            repo = (match.group("repo") or repo_full_name).lower()
            add_unique(issues, f"{repo}#{match.group('number')}")
        for match in _ISSUE_URL_RE.finditer(text or ""):
            add_unique(issues, f"{match.group('repo').lower()}#{match.group('number')}")
        for match in _COMMIT_REFERENCE_RE.finditer(text or ""):
            add_unique(commits, match.group("sha").lower())
        for match in _COMMIT_URL_RE.finditer(text or ""):
            add_unique(commits, match.group("sha").lower())

        return {
            "pull_requests": pull_requests,
            "issues": issues,
            "commits": commits,
        }

    @staticmethod
    def _append_reference_lines(lines: list[str], references: dict[str, list[str]]) -> None:
        if references["pull_requests"]:
            lines.append(
                "Referenced Pull Requests: " + ", ".join(references["pull_requests"])
            )
        if references["issues"]:
            lines.append("Referenced Issues: " + ", ".join(references["issues"]))
        if references["commits"]:
            lines.append("Referenced Commits: " + ", ".join(references["commits"]))

    @staticmethod
    def _append_review_context_lines(
        lines: list[str],
        *,
        commit_id: Any | None = None,
        original_commit_id: Any | None = None,
        path: Any | None = None,
        line: Any | None = None,
        side: Any | None = None,
    ) -> None:
        if commit_id:
            lines.append(f"Review Commit: {commit_id}")
        if original_commit_id and original_commit_id != commit_id:
            lines.append(f"Original Review Commit: {original_commit_id}")
        if path:
            lines.append(f"File: {path}")
        if line is not None:
            lines.append(f"Line: {line}")
        if side:
            lines.append(f"Side: {side}")

    @staticmethod
    def _append_commit_reference(references: dict[str, list[str]], commit_id: Any | None) -> None:
        if not commit_id:
            return
        commit = str(commit_id).strip().lower()
        if commit and commit not in references["commits"]:
            references["commits"].append(commit)

    @staticmethod
    def _login_name(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        login = payload.get("login")
        if not login:
            return None
        return str(login).strip() or None

    @staticmethod
    def _cursor_to_state(cursor: str | None) -> tuple[datetime | None, str | None]:
        if not cursor:
            return None, None
        try:
            payload = json.loads(cursor)
            updated_at = payload.get("updated_at")
            external_id = payload.get("external_id")
        except (TypeError, ValueError, json.JSONDecodeError):
            return None, None
        return GitHubConnector._parse_datetime(updated_at), str(external_id or "") or None

    @staticmethod
    def _retry_after_seconds(raw_value: str | None) -> float | None:
        if raw_value is None:
            return None
        try:
            value = float(raw_value)
        except ValueError:
            return None
        now = datetime.now(timezone.utc).timestamp()
        if value > now:
            return max(value - now, 0.0)
        return max(value, 0.0)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value or not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
        except ValueError:
            return None
