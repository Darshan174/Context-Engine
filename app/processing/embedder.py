"""Embeddings generation used for hybrid retrieval."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.config import settings
from app.services.llm_service import (
    LLMConfigurationError,
    LLMResponseError,
    LLMServiceError,
    LiteLLMService,
    has_live_litellm_api_key,
)


class EmbeddingError(Exception):
    """Raised when an embedding request fails."""


class BaseEmbedder(ABC):
    dimension: int = 1024

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Return a normalized embedding vector."""


class HashingEmbedder(BaseEmbedder):
    """Deterministic local baseline embedder for tests and offline development."""

    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode(), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            magnitude = 1.0 + (digest[5] / 255.0)
            vector[index] += sign * magnitude

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class LiteLLMEmbedder(BaseEmbedder):
    """Optional provider-backed embedder for production deployments."""

    def __init__(
        self,
        model: str,
        dimension: int = 1024,
        *,
        service: LiteLLMService | None = None,
    ) -> None:
        self.model = model
        self.dimension = dimension
        self.service = service or LiteLLMService()

    async def embed_text(self, text: str) -> list[float]:
        try:
            vectors = await self.service.embed_texts(
                model=self.model,
                texts=[text],
                dimensions=self.dimension,
            )
        except (
            LLMConfigurationError,
            LLMServiceError,
            LLMResponseError,
            Exception,
        ) as exc:
            raise EmbeddingError(str(exc)) from exc

        return vectors[0]


def build_default_embedder() -> BaseEmbedder:
    model = _resolved_embedding_model()
    if model:
        return LiteLLMEmbedder(
            model,
            dimension=settings.embedding_dimensions,
        )
    if settings.environment == "production":
        raise EmbeddingError(
            "Production retrieval requires EMBEDDING_MODEL or LITELLM_API_KEY "
            "with DEFAULT_EMBEDDING_MODEL."
        )
    return HashingEmbedder()


def cosine_similarity(lhs: list[float] | None, rhs: list[float] | None) -> float:
    if not lhs or not rhs:
        return 0.0
    return float(sum(a * b for a, b in zip(lhs, rhs)))


def _resolved_embedding_model() -> str | None:
    if settings.embedding_model:
        return settings.embedding_model
    if (
        settings.enable_default_provider_models
        and has_live_litellm_api_key()
        and settings.default_embedding_model
    ):
        return settings.default_embedding_model
    return None
