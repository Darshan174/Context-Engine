from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.services.llm_service import (
    LLMConfigurationError,
    LLMResponseError,
    LiteLLMService,
    has_live_litellm_api_key,
)


class TestLiteLLMService:
    async def test_completion_json_returns_message_content(self):
        seen_kwargs = {}

        async def _complete(**kwargs):
            seen_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"facts": []}')
                    )
                ]
            )

        service = LiteLLMService(completion_fn=_complete)
        content = await service.completion_json(
            model="openai/gpt-4.1-mini",
            messages=[{"role": "user", "content": "extract facts"}],
        )

        assert content == '{"facts": []}'
        assert seen_kwargs["model"] == "openai/gpt-4.1-mini"
        assert seen_kwargs["response_format"] == {"type": "json_object"}
        assert seen_kwargs["temperature"] == 0

    async def test_completion_json_accepts_pydantic_response_format(self):
        seen_kwargs = {}

        class _Schema(BaseModel):
            facts: list[dict] = []

        async def _complete(**kwargs):
            seen_kwargs.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"facts": []}')
                    )
                ]
            )

        service = LiteLLMService(completion_fn=_complete)
        content = await service.completion_json(
            model="openai/gpt-4.1-mini",
            messages=[{"role": "user", "content": "extract facts"}],
            response_format=_Schema,
        )

        assert content == '{"facts": []}'
        assert seen_kwargs["response_format"] is _Schema

    async def test_completion_json_requires_model(self):
        service = LiteLLMService(completion_fn=lambda **kwargs: None)

        with pytest.raises(LLMConfigurationError, match="No extraction model"):
            await service.completion_json(model=None, messages=[])

    async def test_completion_json_rejects_missing_content(self):
        async def _complete(**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))])

        service = LiteLLMService(completion_fn=_complete)

        with pytest.raises(LLMResponseError, match="empty content"):
            await service.completion_json(
                model="openai/gpt-4.1-mini",
                messages=[{"role": "user", "content": "extract facts"}],
            )

    async def test_embed_texts_returns_vectors(self):
        seen_kwargs = {}

        async def _embed(**kwargs):
            seen_kwargs.update(kwargs)
            return SimpleNamespace(data=[{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}])

        service = LiteLLMService(embedding_fn=_embed)
        vectors = await service.embed_texts(
            model="openai/text-embedding-3-large",
            texts=["one", "two"],
            dimensions=2,
        )

        assert vectors == [[0.1, 0.2], [0.3, 0.4]]
        assert seen_kwargs["dimensions"] == 2

    async def test_embed_texts_rejects_mismatched_count(self):
        async def _embed(**kwargs):
            return SimpleNamespace(data=[{"embedding": [0.1, 0.2]}])

        service = LiteLLMService(embedding_fn=_embed)

        with pytest.raises(LLMResponseError, match="count did not match"):
            await service.embed_texts(
                model="openai/text-embedding-3-large",
                texts=["one", "two"],
            )

    async def test_embed_texts_rejects_mismatched_vector_dimension(self):
        async def _embed(**kwargs):
            return SimpleNamespace(data=[{"embedding": [0.1, 0.2, 0.3]}])

        service = LiteLLMService(embedding_fn=_embed)

        with pytest.raises(LLMResponseError, match="pgvector size"):
            await service.embed_texts(
                model="openai/text-embedding-3-large",
                texts=["one"],
                dimensions=2,
            )


class TestLiteLLMKeyDetection:
    def test_placeholder_key_is_not_treated_as_live(self):
        assert has_live_litellm_api_key("your-litellm-api-key") is False
        assert has_live_litellm_api_key("test-key") is False

    def test_realistic_key_is_treated_as_live(self):
        assert has_live_litellm_api_key("sk-live-123") is True
