"""Provider-backed LLM helpers for structured extraction and embeddings."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.config import settings

_PLACEHOLDER_LITELLM_KEYS = {
    "changeme",
    "dummy",
    "placeholder",
    "test-key",
    "your-litellm-api-key",
    "your-provider-key",
}


class LLMServiceError(Exception):
    """Base provider error."""


class LLMConfigurationError(LLMServiceError):
    """Raised when a model path is configured incorrectly or unavailable."""


class LLMResponseError(LLMServiceError):
    """Raised when a provider returns an unexpected shape."""


class LiteLLMService:
    def __init__(
        self,
        *,
        completion_fn: Callable[..., Awaitable[Any]] | None = None,
        embedding_fn: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._completion_fn = completion_fn
        self._embedding_fn = embedding_fn

    async def completion_json(
        self,
        *,
        model: str | None,
        messages: list[dict[str, str]],
        temperature: float = 0,
    ) -> str:
        if not model:
            raise LLMConfigurationError("No extraction model is configured")

        completion = self._completion_fn or self._load_completion()
        if self._completion_fn is None and not has_live_litellm_api_key():
            raise LLMConfigurationError("LiteLLM API key is not configured")
        try:
            response = await completion(
                model=model,
                api_key=settings.litellm_api_key,
                api_base=settings.litellm_api_base,
                timeout=settings.litellm_timeout_seconds,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
        except Exception as exc:
            raise LLMServiceError(
                f"Structured completion failed: {exc.__class__.__name__}"
            ) from exc

        try:
            content = response.choices[0].message.content
        except Exception as exc:
            raise LLMResponseError("Completion response did not contain message content") from exc

        if not content:
            raise LLMResponseError("Completion response returned empty content")
        return content

    async def embed_texts(
        self,
        *,
        model: str | None,
        texts: list[str],
        dimensions: int | None = None,
    ) -> list[list[float]]:
        if not model:
            raise LLMConfigurationError("No embedding model is configured")

        embedding = self._embedding_fn or self._load_embedding()
        if self._embedding_fn is None and not has_live_litellm_api_key():
            raise LLMConfigurationError("LiteLLM API key is not configured")
        request_kwargs = {
            "model": model,
            "api_key": settings.litellm_api_key,
            "api_base": settings.litellm_api_base,
            "timeout": settings.litellm_timeout_seconds,
            "input": texts,
        }
        if dimensions is not None:
            request_kwargs["dimensions"] = dimensions
        try:
            response = await embedding(**request_kwargs)
        except Exception as exc:
            raise LLMServiceError(
                f"Embedding request failed: {exc.__class__.__name__}"
            ) from exc

        try:
            vectors = [item["embedding"] for item in response.data]
        except Exception as exc:
            raise LLMResponseError("Embedding response did not contain vectors") from exc

        if len(vectors) != len(texts):
            raise LLMResponseError("Embedding response count did not match input count")
        if dimensions is not None:
            invalid = next(
                (
                    len(vector)
                    for vector in vectors
                    if not isinstance(vector, list) or len(vector) != dimensions
                ),
                None,
            )
            if invalid is not None:
                raise LLMResponseError(
                    "Embedding vector dimension did not match configured pgvector size"
                )
        return vectors

    @staticmethod
    def _load_completion() -> Callable[..., Awaitable[Any]]:
        try:
            from litellm import acompletion
        except Exception as exc:  # pragma: no cover - optional dependency
            raise LLMConfigurationError("LiteLLM is not installed") from exc
        return acompletion

    @staticmethod
    def _load_embedding() -> Callable[..., Awaitable[Any]]:
        try:
            from litellm import aembedding
        except Exception as exc:  # pragma: no cover - optional dependency
            raise LLMConfigurationError("LiteLLM is not installed") from exc
        return aembedding


def has_live_litellm_api_key(api_key: str | None = None) -> bool:
    value = (api_key if api_key is not None else settings.litellm_api_key) or ""
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized in _PLACEHOLDER_LITELLM_KEYS:
        return False
    return not normalized.startswith("your-")
