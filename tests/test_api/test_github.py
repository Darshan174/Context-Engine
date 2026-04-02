"""Tests for the GitHub connector path."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

import app.services.connector_service as connector_module
import app.services.sync_service as sync_module
from app.connectors.base import AuthenticationError, NormalizedDocument, RateLimitError
from app.connectors.github import GitHubConnector
from app.models.connector import Connector, ConnectorStatus
from app.models.source import ConnectorType, SourceDocument
from app.services.sync_service import SyncError as SyncExecutorError, SyncExecutor
from app.utils.crypto import decrypt_token, encrypt_token

from cryptography.fernet import Fernet

_TEST_FERNET_KEY = Fernet.generate_key().decode()


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        *,
        json_body=None,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self._json_body = json_body if json_body is not None else []
        self.headers = headers or {}

    def json(self):
        return self._json_body


class _FakeGitHubHttpClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None):
        self.calls.append((url, params))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


async def _mock_github_fetch(documents):
    for document in documents:
        yield document


def _make_item(
    *,
    number: int,
    title: str,
    body: str,
    repo: str = "acme/context-engine",
    updated_at: str = "2026-04-01T10:00:00Z",
    state: str = "open",
    is_pr: bool = False,
):
    item = {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "html_url": f"https://github.com/{repo}/issues/{number}",
        "updated_at": updated_at,
        "created_at": "2026-03-31T10:00:00Z",
        "labels": [{"name": "priority"}],
        "assignees": [{"login": "alice"}],
        "user": {"login": "octocat"},
    }
    if is_pr:
        item["pull_request"] = {"merged_at": None}
        item["html_url"] = f"https://github.com/{repo}/pull/{number}"
    return item


class TestGitHubNormalizedDocumentMapping:
    def test_maps_issue_to_normalized_document(self):
        document = GitHubConnector._to_normalized_document(
            "acme/context-engine",
            _make_item(
                number=42,
                title="Tighten accuracy gating",
                body="Track the regression command and CI thresholds.",
            ),
        )

        assert document is not None
        assert document.external_id == "github:acme/context-engine:issue:42"
        assert document.author == "octocat"
        assert document.source_url == "https://github.com/acme/context-engine/issues/42"
        assert document.created_at == datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)
        assert "Repository: acme/context-engine" in document.content
        assert "Issue #42: Tighten accuracy gating" in document.content
        assert document.metadata["repo_full_name"] == "acme/context-engine"
        assert document.metadata["title"] == "Tighten accuracy gating"
        assert document.metadata["item_type"] == "issue"

    def test_maps_pull_request_to_normalized_document(self):
        document = GitHubConnector._to_normalized_document(
            "acme/context-engine",
            _make_item(
                number=77,
                title="Add eval CLI",
                body="This adds the Phase 3B regression entrypoint.",
                is_pr=True,
            ),
        )

        assert document is not None
        assert document.external_id == "github:acme/context-engine:pull_request:77"
        assert document.metadata["item_type"] == "pull_request"
        assert document.source_url == "https://github.com/acme/context-engine/pull/77"

    def test_maps_issue_comment_with_issue_pull_request_and_commit_references(self):
        parent = _make_item(
            number=42,
            title="Tighten accuracy gating",
            body="Track the regression command.",
        )
        comment = {
            "id": 9001,
            "body": "This is ready in PR #77 after commit abc1234 and fixes #42.",
            "html_url": "https://github.com/acme/context-engine/issues/42#issuecomment-9001",
            "created_at": "2026-04-01T11:00:00Z",
            "updated_at": "2026-04-01T11:30:00Z",
            "user": {"login": "reviewer"},
        }

        document = GitHubConnector._to_issue_comment_document(
            "acme/context-engine",
            parent,
            comment,
        )

        assert document is not None
        assert document.external_id == "github:acme/context-engine:issue_comment:9001"
        assert document.metadata["parent_external_id"] == "github:acme/context-engine:issue:42"
        assert document.metadata["pull_request_references"] == ["acme/context-engine#77"]
        assert document.metadata["issue_references"] == ["acme/context-engine#42"]
        assert document.metadata["commit_references"] == ["abc1234"]
        assert "Referenced Pull Requests: acme/context-engine#77" in document.content
        assert "Referenced Issues: acme/context-engine#42" in document.content
        assert "Referenced Commits: abc1234" in document.content

    def test_maps_pull_request_review_without_body(self):
        parent = _make_item(
            number=77,
            title="Add eval CLI",
            body="This adds the Phase 3B regression entrypoint.",
            is_pr=True,
        )
        review = {
            "id": 701,
            "state": "APPROVED",
            "body": "",
            "html_url": "https://github.com/acme/context-engine/pull/77#pullrequestreview-701",
            "submitted_at": "2026-04-01T12:00:00Z",
            "user": {"login": "maintainer"},
        }

        document = GitHubConnector._to_pull_review_document(
            "acme/context-engine",
            parent,
            review,
        )

        assert document is not None
        assert document.external_id == "github:acme/context-engine:pull_review:701"
        assert document.metadata["item_type"] == "pull_request_review"
        assert document.metadata["review_state"] == "APPROVED"
        assert "Review State: APPROVED" in document.content

    def test_maps_pull_request_review_comment_with_review_context_and_references(self):
        parent = _make_item(
            number=77,
            title="Add eval CLI",
            body="This adds the Phase 3B regression entrypoint.",
            is_pr=True,
        )
        comment = {
            "id": 8001,
            "body": (
                "Decision: ship after merge.\n"
                "Rationale: closes issue #31 after commit abc1234."
            ),
            "html_url": "https://github.com/acme/context-engine/pull/77#discussion_r8001",
            "created_at": "2026-04-01T12:30:00Z",
            "updated_at": "2026-04-01T12:45:00Z",
            "user": {"login": "maintainer"},
            "commit_id": "deadbeef1",
            "original_commit_id": "cafebabe2",
            "path": "app/evals/runner.py",
            "line": 236,
            "side": "RIGHT",
        }

        document = GitHubConnector._to_pull_review_comment_document(
            "acme/context-engine",
            parent,
            comment,
        )

        assert document is not None
        assert document.metadata["item_type"] == "pull_request_review_comment"
        assert document.metadata["issue_references"] == ["acme/context-engine#31"]
        assert document.metadata["commit_references"] == ["abc1234", "deadbeef1", "cafebabe2"]
        assert document.metadata["commit_id"] == "deadbeef1"
        assert document.metadata["original_commit_id"] == "cafebabe2"
        assert document.metadata["path"] == "app/evals/runner.py"
        assert document.metadata["line"] == 236
        assert document.metadata["side"] == "RIGHT"
        assert "Referenced Issues: acme/context-engine#31" in document.content
        assert "Review Commit: deadbeef1" in document.content
        assert "Original Review Commit: cafebabe2" in document.content
        assert "File: app/evals/runner.py" in document.content
        assert "Line: 236" in document.content
        assert "Side: RIGHT" in document.content


class TestGitHubConnectorFetch:
    async def test_fetch_initial_downloads_issue_documents(self):
        connector = GitHubConnector(
            "github-test-token",
            repositories=["acme/context-engine"],
        )
        fake_http = _FakeGitHubHttpClient(
            [
                _FakeResponse(
                    json_body=[
                        _make_item(
                            number=42,
                            title="Tighten accuracy gating",
                            body="Track the regression command and CI thresholds.",
                        )
                    ]
                ),
                _FakeResponse(json_body=[]),
            ]
        )
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        documents = [doc async for doc in connector.fetch_initial()]

        assert len(documents) == 1
        assert documents[0].external_id == "github:acme/context-engine:issue:42"
        assert fake_http.calls[0][0].endswith("/repos/acme/context-engine/issues")
        assert fake_http.calls[0][1]["state"] == "all"
        assert fake_http.calls[0][1]["sort"] == "updated"

    async def test_fetch_initial_downloads_pr_reviews_and_comments(self):
        connector = GitHubConnector(
            "github-test-token",
            repositories=["acme/context-engine"],
        )
        fake_http = _FakeGitHubHttpClient(
            [
                _FakeResponse(
                    json_body=[
                        _make_item(
                            number=77,
                            title="Add eval CLI",
                            body="Implements PR #12 after commit abc1234.",
                            is_pr=True,
                        )
                    ]
                ),
                _FakeResponse(
                    json_body=[
                        {
                            "id": 9002,
                            "body": "Looks good to me.",
                            "html_url": "https://github.com/acme/context-engine/pull/77#issuecomment-9002",
                            "created_at": "2026-04-01T11:00:00Z",
                            "updated_at": "2026-04-01T11:10:00Z",
                            "user": {"login": "reviewer"},
                        }
                    ]
                ),
                _FakeResponse(
                    json_body=[
                        {
                            "id": 701,
                            "state": "APPROVED",
                            "body": "",
                            "html_url": "https://github.com/acme/context-engine/pull/77#pullrequestreview-701",
                            "submitted_at": "2026-04-01T12:00:00Z",
                            "user": {"login": "maintainer"},
                        }
                    ]
                ),
                _FakeResponse(
                    json_body=[
                        {
                            "id": 8001,
                            "body": "See PR #13 before merge.",
                            "html_url": "https://github.com/acme/context-engine/pull/77#discussion_r8001",
                            "created_at": "2026-04-01T12:30:00Z",
                            "updated_at": "2026-04-01T12:45:00Z",
                            "user": {"login": "maintainer"},
                        }
                    ]
                ),
            ]
        )
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        documents = [doc async for doc in connector.fetch_initial()]

        assert [doc.external_id for doc in documents] == [
            "github:acme/context-engine:pull_request:77",
            "github:acme/context-engine:issue_comment:9002",
            "github:acme/context-engine:pull_review:701",
            "github:acme/context-engine:pull_review_comment:8001",
        ]
        assert documents[0].metadata["pull_request_references"] == ["acme/context-engine#12"]
        assert documents[0].metadata["commit_references"] == ["abc1234"]
        assert documents[3].metadata["item_type"] == "pull_request_review_comment"

    async def test_fetch_incremental_filters_out_older_documents(self):
        connector = GitHubConnector(
            "github-test-token",
            repositories=["acme/context-engine"],
        )
        fake_http = _FakeGitHubHttpClient(
            [
                _FakeResponse(
                    json_body=[
                        _make_item(
                            number=1,
                            title="Old issue",
                            body="Old content",
                            updated_at="2026-04-01T09:59:59Z",
                        ),
                        _make_item(
                            number=2,
                            title="New issue",
                            body="New content",
                            updated_at="2026-04-01T10:00:01Z",
                        ),
                    ]
                ),
                _FakeResponse(json_body=[]),
            ]
        )
        connector._http_client = lambda: fake_http  # type: ignore[method-assign]

        cursor = json.dumps(
            {
                "updated_at": "2026-04-01T10:00:00+00:00",
                "external_id": "github:acme/context-engine:issue:1",
            }
        )
        documents = [doc async for doc in connector.fetch_incremental(cursor=cursor)]

        assert [doc.external_id for doc in documents] == [
            "github:acme/context-engine:issue:2"
        ]
        assert fake_http.calls[0][1]["since"] == "2026-04-01T10:00:00Z"

    async def test_github_get_raises_auth_error(self):
        connector = GitHubConnector(
            "github-test-token",
            repositories=["acme/context-engine"],
        )
        fake_http = _FakeGitHubHttpClient([_FakeResponse(status_code=401)])

        with pytest.raises(AuthenticationError, match="GitHub auth failed"):
            await connector._github_get(fake_http, "/repos/acme/context-engine/issues")

    async def test_github_get_raises_rate_limit(self):
        connector = GitHubConnector(
            "github-test-token",
            repositories=["acme/context-engine"],
        )
        fake_http = _FakeGitHubHttpClient(
            [
                _FakeResponse(
                    status_code=403,
                    headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "5"},
                )
            ]
        )

        with pytest.raises(RateLimitError):
            await connector._github_get(fake_http, "/repos/acme/context-engine/issues")


class TestGitHubConnectorResolution:
    def test_resolve_returns_github_connector(self):
        executor = SyncExecutor.__new__(SyncExecutor)
        executor._current_connector_config = {"repositories": ["acme/context-engine"]}

        connector = executor._resolve_connector(ConnectorType.GITHUB, "github-test-token")

        assert isinstance(connector, GitHubConnector)

    def test_resolve_without_repositories_raises(self):
        executor = SyncExecutor.__new__(SyncExecutor)
        executor._current_connector_config = {}

        with pytest.raises(
            SyncExecutorError,
            match="requires at least one configured repository",
        ):
            executor._resolve_connector(ConnectorType.GITHUB, "github-test-token")


class TestGitHubConnect:
    async def test_connect_creates_connector(
        self, client, workspace, db_session, monkeypatch
    ):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

        response = await client.post(
            "/api/connectors/github/connect",
            json={
                "workspace_id": str(workspace.id),
                "token": "github_test_token",
                "repositories": ["acme/context-engine", "acme/platform"],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["connector_type"] == "github"
        assert body["status"] == "connected"
        assert body["provider"] == "official_api"
        assert body["config"]["sync_delivery_mode"] == "polling_only"
        assert body["config"]["repositories"] == [
            "acme/context-engine",
            "acme/platform",
        ]

        connector = await db_session.scalar(
            select(Connector).where(Connector.id == body["id"])
        )
        assert connector is not None
        assert decrypt_token(connector.oauth_token_encrypted) == "github_test_token"


class TestGitHubSync:
    def _setup(self, monkeypatch):
        monkeypatch.setattr(connector_module.settings, "encryption_key", _TEST_FERNET_KEY)

    async def test_github_sync_persists_issue_source_documents(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.GITHUB,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("github_test_token"),
            config={"repositories": ["acme/context-engine"]},
        )
        db_session.add(connector)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="github:acme/context-engine:issue:42",
                content="Repository: acme/context-engine\nIssue #42: Tighten accuracy gating\n\nTrack the regression command.",
                author="octocat",
                source_url="https://github.com/acme/context-engine/issues/42",
                created_at=datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc),
                metadata={
                    "repo_full_name": "acme/context-engine",
                    "title": "Tighten accuracy gating",
                    "item_type": "issue",
                },
            )
        ]
        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_github_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, connector_type, token: mock_connector,
        )

        await SyncExecutor(db_session).run(connector, "github_test_token")

        rows = list(
            await db_session.scalars(
                select(SourceDocument).where(SourceDocument.connector_id == connector.id)
            )
        )
        assert len(rows) == 1
        assert rows[0].connector_type == ConnectorType.GITHUB
        assert rows[0].metadata_json["repo_full_name"] == "acme/context-engine"
        assert rows[0].metadata_json["title"] == "Tighten accuracy gating"

    async def test_github_sync_persists_review_comment_source_documents(
        self, workspace, db_session, monkeypatch
    ):
        self._setup(monkeypatch)
        connector = Connector(
            workspace_id=workspace.id,
            connector_type=ConnectorType.GITHUB,
            status=ConnectorStatus.CONNECTED,
            oauth_token_encrypted=encrypt_token("github_test_token"),
            config={"repositories": ["acme/context-engine"]},
        )
        db_session.add(connector)
        await db_session.flush()

        sample_docs = [
            NormalizedDocument(
                external_id="github:acme/context-engine:pull_review_comment:8001",
                content=(
                    "Repository: acme/context-engine\n"
                    "Review Comment on Pull Request #77: Add eval CLI\n\n"
                    "decision: ship after PR #13 and commit abc1234."
                ),
                author="maintainer",
                source_url="https://github.com/acme/context-engine/pull/77#discussion_r8001",
                created_at=datetime(2026, 4, 1, 12, 45, tzinfo=timezone.utc),
                metadata={
                    "repo_full_name": "acme/context-engine",
                    "title": "Review Comment on Pull Request #77: Add eval CLI",
                    "item_type": "pull_request_review_comment",
                    "parent_external_id": "github:acme/context-engine:pull_request:77",
                    "pull_request_references": ["acme/context-engine#13"],
                    "commit_references": ["abc1234"],
                },
            )
        ]
        mock_connector = AsyncMock()
        mock_connector.fetch_initial = lambda: _mock_github_fetch(sample_docs)
        monkeypatch.setattr(
            sync_module.SyncExecutor,
            "_resolve_connector",
            lambda self, connector_type, token: mock_connector,
        )

        await SyncExecutor(db_session).run(connector, "github_test_token")

        rows = list(
            await db_session.scalars(
                select(SourceDocument).where(SourceDocument.connector_id == connector.id)
            )
        )
        assert len(rows) == 1
        assert rows[0].external_id == "github:acme/context-engine:pull_review_comment:8001"
        assert rows[0].metadata_json["pull_request_references"] == ["acme/context-engine#13"]
        assert rows[0].metadata_json["commit_references"] == ["abc1234"]
