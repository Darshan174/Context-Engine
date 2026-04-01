from __future__ import annotations

import math

import pytest

from app.processing.embedder import (
    EmbeddingError,
    HashingEmbedder,
    LiteLLMEmbedder,
    build_default_embedder,
)


class TestHashingEmbedder:
    async def test_returns_deterministic_normalized_vector(self):
        embedder = HashingEmbedder(dimension=8)
        vector1 = await embedder.embed_text("Enterprise pricing is $600/seat")
        vector2 = await embedder.embed_text("Enterprise pricing is $600/seat")

        assert vector1 == vector2
        assert len(vector1) == 8
        assert pytest.approx(math.sqrt(sum(value * value for value in vector1)), 0.0001) == 1.0


class TestLiteLLMEmbedder:
    async def test_uses_provider_embedding_path(self):
        class _FakeService:
            async def embed_texts(self, *, model, texts, dimensions):
                assert model == "openai/text-embedding-3-large"
                assert texts == ["Enterprise pricing is $600/seat"]
                assert dimensions == 3
                return [[0.1, 0.2, 0.3]]

        embedder = LiteLLMEmbedder(
            "openai/text-embedding-3-large",
            dimension=3,
            service=_FakeService(),
        )
        vector = await embedder.embed_text("Enterprise pricing is $600/seat")

        assert vector == [0.1, 0.2, 0.3]

    async def test_wraps_provider_errors(self):
        class _FailingService:
            async def embed_texts(self, *, model, texts, dimensions):
                raise RuntimeError("boom")

        embedder = LiteLLMEmbedder(
            "openai/text-embedding-3-large",
            service=_FailingService(),
        )

        with pytest.raises(EmbeddingError, match="boom"):
            await embedder.embed_text("Enterprise pricing is $600/seat")


class TestBuildDefaultEmbedder:
    def test_chooses_provider_embedder_when_model_is_configured(self, monkeypatch):
        monkeypatch.setattr(
            "app.processing.embedder.settings.embedding_model",
            "openai/text-embedding-3-large",
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.embedding_dimensions",
            768,
        )
        embedder = build_default_embedder()
        assert isinstance(embedder, LiteLLMEmbedder)
        assert embedder.dimension == 768

    def test_uses_default_provider_model_when_opted_in(self, monkeypatch):
        monkeypatch.setattr(
            "app.processing.embedder.settings.embedding_model",
            None,
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.litellm_api_key",
            "sk-live-test",
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.default_embedding_model",
            "openai/text-embedding-3-large",
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.enable_default_provider_models",
            True,
        )

        embedder = build_default_embedder()
        assert isinstance(embedder, LiteLLMEmbedder)

    def test_placeholder_key_does_not_force_provider_embedder(self, monkeypatch):
        monkeypatch.setattr(
            "app.processing.embedder.settings.embedding_model",
            None,
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.litellm_api_key",
            "your-litellm-api-key",
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.enable_default_provider_models",
            True,
        )

        embedder = build_default_embedder()
        assert isinstance(embedder, HashingEmbedder)

    def test_production_requires_real_embedding_model(self, monkeypatch):
        monkeypatch.setattr(
            "app.processing.embedder.settings.environment",
            "production",
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.embedding_model",
            None,
        )
        monkeypatch.setattr(
            "app.processing.embedder.settings.litellm_api_key",
            None,
        )

        with pytest.raises(EmbeddingError, match="Production retrieval requires"):
            build_default_embedder()
