"""Schema-constrained fact extraction from SourceDocuments.

Hierarchy:
  BaseExtractor            — async interface
  RegexExtractor           — local pattern fallback
  StructuredLLMExtractor   — strict structured extraction only
  FallbackExtractor        — tries structured extraction, falls back to regex

Document truncation / chunking:
  Long documents are truncated to ``settings.extraction_max_input_chars``
  or split into overlapping chunks (``extraction_chunk_size_chars`` /
  ``extraction_chunk_overlap_chars``).  Each chunk is extracted independently
  and the resulting fact lists are merged and deduplicated.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.models.source import ConnectorType
from app.services.llm_service import (
    LLMConfigurationError,
    LLMResponseError,
    LLMServiceError,
    LiteLLMService,
    has_live_litellm_api_key,
)

if TYPE_CHECKING:
    from app.models.source import SourceDocument

EXTRACTION_SCHEMA_VERSION = "fact_extraction.v1"
FactType = Literal["decision", "action_item", "blocker", "discussion"]
RelationshipTypeName = Literal[
    "depends_on",
    "blocked_by",
    "enables",
    "contradicts",
    "supersedes",
    "related_to",
]
_DEFAULT_FACT_NAMES: dict[str, str] = {
    "decision": "Decision",
    "action_item": "Action Item",
    "blocker": "Blocker",
    "discussion": "Discussion",
}
_GENERIC_FACT_NAMES = {
    "action",
    "action item",
    "action_item",
    "blocker",
    "decision",
    "discussion",
    "fact",
    "item",
    "note",
    "todo",
}
_MEETING_OUTCOME_RE = re.compile(
    r"(?im)^\s*(?:(?P<speaker>[^:\n]{1,80}):\s*)?(?:meeting outcome|outcome)\s*:\s*(?P<text>.+?)\s*$"
)
_MEETING_ACTION_OWNER_RE = re.compile(
    r"(?im)^\s*(?P<speaker>[^:\n]{1,80}):\s*(?:action item|todo|ai)\s*:\s*(?P<text>.+?)\s*$"
)
_MEETING_DECISION_RE = re.compile(
    r"(?im)^\s*(?:(?P<speaker>[^:\n]{1,80}):\s*)?(?:decision|decided)\s*:\s*(?P<text>.+?)\s*$"
)

# ── Few-shot examples per connector type ──────────────────────────

FEW_SHOT_EXAMPLES: dict[str, str] = {
    "slack": (
        "Example Slack message:\n"
        "```\n"
        "Channel: #engineering\n"
        "Author: alice@acme.com\n"
        "decision: migrate the user-service to Postgres 16\n"
        "action item: bob to prepare the migration runbook by Friday\n"
        "blocker: staging environment is currently down\n"
        "```\n"
        "Expected output:\n"
        "```json\n"
        '{\n'
        '  "facts": [\n'
        '    {"name": "Migrate user-service to Postgres 16", "value": "migrate the user-service to Postgres 16", "confidence": 0.9, "fact_type": "decision", "relationships": []},\n'
        '    {"name": "Prepare migration runbook", "value": "bob to prepare the migration runbook by Friday", "confidence": 0.85, "fact_type": "action_item", "relationships": []},\n'
        '    {"name": "Staging environment down", "value": "staging environment is currently down", "confidence": 0.88, "fact_type": "blocker", "relationships": []}\n'
        "  ]\n"
        "}\n"
        "```\n"
    ),
    "zoom": (
        "Example Zoom meeting transcript:\n"
        "```\n"
        "Meeting topic: Weekly Product Review\n"
        "Founder: meeting outcome: launch pricing page on April 15.\n"
        "Alice: action item: prepare demo environment.\n"
        "Bob: AI: draft launch email.\n"
        "```\n"
        "Expected output:\n"
        "```json\n"
        '{\n'
        '  "facts": [\n'
        '    {"name": "Launch pricing page on April 15", "value": "launch pricing page on April 15", "confidence": 0.92, "fact_type": "decision", "relationships": []},\n'
        '    {"name": "Prepare demo environment", "value": "Owner: Alice - prepare demo environment", "confidence": 0.88, "fact_type": "action_item", "relationships": []},\n'
        '    {"name": "Draft launch email", "value": "Owner: Bob - draft launch email", "confidence": 0.88, "fact_type": "action_item", "relationships": []}\n'
        "  ]\n"
        "}\n"
        "```\n"
    ),
    "github": (
        "Example GitHub PR description / review:\n"
        "```\n"
        "Repository: acme/context-engine\n"
        "Pull Request #77: Migration plan\n"
        "Decision: use Postgres 16 rolling migration.\n"
        "Rationale: avoids downtime during cutover.\n"
        "```\n"
        "Expected output:\n"
        "```json\n"
        '{\n'
        '  "facts": [\n'
        '    {"name": "Use Postgres 16 rolling migration", "value": "use Postgres 16 rolling migration", "confidence": 0.9, "fact_type": "decision", "relationships": []},\n'
        '    {"name": "Rationale for rolling migration", "value": "avoids downtime during cutover", "confidence": 0.8, "fact_type": "discussion", "relationships": [{"target_fact_name": "Use Postgres 16 rolling migration", "relationship_type": "related_to", "confidence": 0.8}]}\n'
        "  ]\n"
        "}\n"
        "```\n"
    ),
}


@dataclass(frozen=True, slots=True)
class ExtractorMetadata:
    extractor_name: str
    extractor_kind: str
    schema_version: str = EXTRACTION_SCHEMA_VERSION


@dataclass
class ExtractedRelationship:
    target_fact_name: str
    relationship_type: str  # matches RelationshipType enum value
    confidence: float


@dataclass
class ExtractedFact:
    name: str
    value: str
    confidence: float
    fact_type: str  # "decision" | "action_item" | "blocker" | "discussion"
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    extractor: ExtractorMetadata = field(
        default_factory=lambda: ExtractorMetadata(
            extractor_name="regex",
            extractor_kind="regex",
        )
    )


class ExtractionError(Exception):
    """Raised when structured extraction is unavailable or malformed."""


class StructuredRelationshipPayload(BaseModel):
    target_fact_name: str = Field(min_length=1, max_length=255)
    relationship_type: RelationshipTypeName
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredFactPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    fact_type: FactType
    relationships: list[StructuredRelationshipPayload] = Field(default_factory=list)


class StructuredExtractionPayload(BaseModel):
    facts: list[StructuredFactPayload] = Field(default_factory=list)


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, doc: "SourceDocument") -> list[ExtractedFact]:
        """Extract structured facts from a source document."""


class RegexExtractor(BaseExtractor):
    """Pattern-based extractor. No external API required."""

    def __init__(self, *, extractor_name: str = "regex") -> None:
        self._metadata = ExtractorMetadata(
            extractor_name=extractor_name,
            extractor_kind="regex",
        )

    async def extract(self, doc: "SourceDocument") -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        content = doc.content
        meta = doc.metadata_json or {}
        source_context = self._source_context_label(meta)

        if doc.connector_type == ConnectorType.GITHUB:
            facts.extend(self._extract_github_decision_and_rationale(content, source_context))
        if doc.connector_type == ConnectorType.ZOOM or meta.get("meeting_topic"):
            facts.extend(self._extract_meeting_outcomes_and_owned_actions(content, source_context))

        for m in re.finditer(
            r"(?:decision|decided)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append(
                ExtractedFact(
                    name=f"Decision in {source_context}",
                    value=m.group(1).strip(),
                    confidence=0.75,
                    fact_type="decision",
                    extractor=self._metadata,
                )
            )

        for m in re.finditer(
            r"(?:action item|todo|AI)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append(
                ExtractedFact(
                    name=f"Action Item in {source_context}",
                    value=m.group(1).strip(),
                    confidence=0.70,
                    fact_type="action_item",
                    extractor=self._metadata,
                )
            )

        for m in re.finditer(
            r"(?:blocker|blocked by)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            value = m.group(1).strip()
            rels = self._extract_blocked_by_relationships(value)
            facts.append(
                ExtractedFact(
                    name=f"Blocker in {source_context}",
                    value=value,
                    confidence=0.80,
                    fact_type="blocker",
                    relationships=rels,
                    extractor=self._metadata,
                )
            )

        if not facts and meta.get("reply_count"):
            author = doc.author or "Unknown"
            preview = content[:200].replace("\n", " ")
            facts.append(
                ExtractedFact(
                    name=f"Discussion in {source_context}",
                    value=f"{author}: {preview}",
                    confidence=0.55,
                    fact_type="discussion",
                    extractor=self._metadata,
                )
            )

        return self._dedupe_facts(facts)

    @staticmethod
    def _source_context_label(meta: dict) -> str:
        if channel := meta.get("channel_name"):
            return f"#{channel}"
        if meeting_topic := meta.get("meeting_topic"):
            return str(meeting_topic)
        if title := meta.get("title"):
            return str(title)
        if repo_full_name := meta.get("repo_full_name"):
            return str(repo_full_name)
        if page_title := meta.get("page_title"):
            return str(page_title)
        if location := meta.get("location"):
            return str(location)
        return "unknown"

    @staticmethod
    def _extract_blocked_by_relationships(
        blocker_value: str,
    ) -> list[ExtractedRelationship]:
        rels: list[ExtractedRelationship] = []
        for m in re.finditer(
            r"blocked by\s+(.+?)(?:\.|$|,|\n)", blocker_value, re.IGNORECASE
        ):
            target_name = m.group(1).strip()
            if target_name:
                rels.append(
                    ExtractedRelationship(
                        target_fact_name=target_name,
                        relationship_type="blocked_by",
                        confidence=0.70,
                    )
                )
        return rels

    def _extract_github_decision_and_rationale(
        self,
        content: str,
        source_context: str,
    ) -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        decision_name = f"Decision in {source_context}"
        decision_patterns = (
            r"(?:^|\n)\s*(?:chosen approach|decision)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:^|\n)\s*we decided to\s+(.+?)(?:\n|$)",
        )
        for pattern in decision_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = re.sub(r"\s+", " ", match.group(1)).strip(" .:-")
                if not value:
                    continue
                facts.append(
                    ExtractedFact(
                        name=decision_name,
                        value=value,
                        confidence=0.78,
                        fact_type="decision",
                        extractor=self._metadata,
                    )
                )

        rationale_patterns = (
            r"(?:^|\n)\s*(?:rationale|why)\s*[:\-]\s*(.+?)(?:\n|$)",
            r"(?:^|\n)\s*because\s+(.+?)(?:\n|$)",
        )
        for pattern in rationale_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                value = re.sub(r"\s+", " ", match.group(1)).strip(" .:-")
                if not value:
                    continue
                relationships = (
                    [
                        ExtractedRelationship(
                            target_fact_name=decision_name,
                            relationship_type="related_to",
                            confidence=0.65,
                        )
                    ]
                    if any(fact.name == decision_name for fact in facts)
                    else []
                )
                facts.append(
                    ExtractedFact(
                        name=f"Discussion in {source_context}",
                        value=f"Rationale: {value}",
                        confidence=0.68,
                        fact_type="discussion",
                        relationships=relationships,
                        extractor=self._metadata,
                    )
                )

        return facts

    def _extract_meeting_outcomes_and_owned_actions(
        self,
        content: str,
        source_context: str,
    ) -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        for outcome in extract_meeting_outcomes(content):
            facts.append(
                ExtractedFact(
                    name=f"Decision in {source_context}",
                    value=outcome,
                    confidence=0.77,
                    fact_type="decision",
                    extractor=self._metadata,
                )
            )
        for owner, action in extract_meeting_action_items(content):
            owner_prefix = f"Owner: {owner} - " if owner else ""
            facts.append(
                ExtractedFact(
                    name=f"Action Item in {source_context}",
                    value=f"{owner_prefix}{action}",
                    confidence=0.72,
                    fact_type="action_item",
                    extractor=self._metadata,
                )
            )
        return facts

    @staticmethod
    def _dedupe_facts(facts: list[ExtractedFact]) -> list[ExtractedFact]:
        deduped: list[ExtractedFact] = []
        seen: set[tuple[str, str, str]] = set()
        for fact in facts:
            normalized_value = re.sub(r"\s+", " ", fact.value).strip(" .:-").lower()
            if fact.fact_type == "action_item":
                normalized_value = re.sub(
                    r"^owner\s*:\s*[^-–—]+[\-–—]\s*",
                    "",
                    normalized_value,
                )
            key = (fact.name.lower(), normalized_value, fact.fact_type)
            if key in seen:
                continue
            deduped.append(fact)
            seen.add(key)
        return deduped


def extract_meeting_outcomes(content: str) -> list[str]:
    outcomes: list[str] = []
    seen: set[str] = set()
    for pattern in (_MEETING_OUTCOME_RE, _MEETING_DECISION_RE):
        for match in pattern.finditer(content):
            text = re.sub(r"\s+", " ", match.group("text")).strip(" .:-")
            key = text.lower()
            if not text or key in seen:
                continue
            outcomes.append(text)
            seen.add(key)
    return outcomes


def extract_meeting_action_items(content: str) -> list[tuple[str | None, str]]:
    items: list[tuple[str | None, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in _MEETING_ACTION_OWNER_RE.finditer(content):
        owner = re.sub(r"\s+", " ", (match.group("speaker") or "")).strip(" .:-") or None
        text = re.sub(r"\s+", " ", match.group("text")).strip(" .:-")
        key = ((owner or "").lower(), text.lower())
        if not text or key in seen:
            continue
        items.append((owner, text))
        seen.add(key)
    return items


class LiteLLMStructuredClient:
    """Thin adapter around LiteLLM for strict JSON-only extraction.

    Uses ``response_format`` with the Pydantic model when the provider
    supports it (OpenAI, Anthropic, recent LiteLLM versions).  Falls back
    to ``json_object`` mode automatically for older providers.
    """

    def __init__(self, model: str, *, service: LiteLLMService | None = None) -> None:
        self.model = model
        self.service = service or LiteLLMService()

    async def complete(self, prompt: str) -> str:
        try:
            return await self.service.completion_json(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract only structured facts and relationships. "
                            "Return strict JSON matching the requested schema. "
                            "Do not add commentary or summaries."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=settings.extraction_temperature,
                response_format=StructuredExtractionPayload,
            )
        except (LLMConfigurationError, LLMServiceError, LLMResponseError) as exc:
            raise ExtractionError(str(exc)) from exc


class StructuredLLMExtractor(BaseExtractor):
    """Strict structured extractor that validates every field before ingestion.

    Supports document truncation and overlapping chunk extraction for long
    documents.  Few-shot examples are injected per connector type to improve
    extraction quality.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        completion_fn: Callable[[str], Awaitable[Any]] | None = None,
        extractor_name: str = "structured_llm",
    ) -> None:
        self.model = model or _resolved_extraction_model()
        self._metadata = ExtractorMetadata(
            extractor_name=extractor_name,
            extractor_kind="llm_structured",
        )
        self._completion_fn = completion_fn
        if self._completion_fn is None and self.model:
            self._completion_fn = LiteLLMStructuredClient(self.model).complete

    async def extract(self, doc: "SourceDocument") -> list[ExtractedFact]:
        if self._completion_fn is None:
            raise ExtractionError("Structured extraction model is not configured")

        content = self._prepare_content(doc.content)
        chunks = self._chunk_content(content)
        all_facts: list[ExtractedFact] = []

        for chunk_text in chunks:
            chunk_doc = self._make_chunk_document(doc, chunk_text)
            prompt = self._build_prompt(chunk_doc)
            raw_output = await self._completion_fn(prompt)
            payload = self._parse_payload(raw_output)
            all_facts.extend(self._normalize_facts(doc, payload))

        return self._dedupe_extracted_facts(all_facts)

    # ── Truncation / chunking ─────────────────────────────────────

    @staticmethod
    def _prepare_content(content: str) -> str:
        """Truncate content to the configured maximum character count."""
        max_chars = settings.extraction_max_input_chars
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n\n[... truncated for extraction ...]"

    @staticmethod
    def _chunk_content(content: str) -> list[str]:
        """Split content into overlapping chunks if it exceeds the chunk size."""
        chunk_size = settings.extraction_chunk_size_chars
        overlap = settings.extraction_chunk_overlap_chars

        if len(content) <= chunk_size:
            return [content]

        chunks: list[str] = []
        start = 0
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk = content[start:end]
            chunks.append(chunk)
            if end >= len(content):
                break
            start = end - overlap if overlap < chunk_size else end
        return chunks

    @staticmethod
    def _make_chunk_document(
        doc: "SourceDocument",
        chunk_content: str,
    ) -> "SourceDocument":
        """Create a lightweight SourceDocument-like wrapper for a single chunk."""
        from unittest.mock import MagicMock

        mock = MagicMock(spec=type(doc))
        mock.content = chunk_content
        mock.metadata_json = doc.metadata_json
        mock.author = doc.author
        mock.connector_type = doc.connector_type
        mock.source_url = doc.source_url
        mock.external_id = doc.external_id
        return mock

    @staticmethod
    def _dedupe_extracted_facts(facts: list[ExtractedFact]) -> list[ExtractedFact]:
        """Deduplicate facts across chunks by (name, value, fact_type)."""
        deduped: list[ExtractedFact] = []
        seen: set[tuple[str, str, str]] = set()
        for fact in facts:
            key = (fact.name.lower(), fact.value.lower(), fact.fact_type)
            if key in seen:
                continue
            deduped.append(fact)
            seen.add(key)
        return deduped

    # ── Prompt building ───────────────────────────────────────────

    def _build_prompt(self, doc: "SourceDocument") -> str:
        metadata = doc.metadata_json or {}
        source_context = RegexExtractor._source_context_label(metadata)
        connector_key = doc.connector_type.value.lower()
        few_shot = FEW_SHOT_EXAMPLES.get(connector_key, "")

        prompt_parts = [
            "You are an extraction system for source-backed startup knowledge.",
            "Return strict JSON only.",
            "Schema: ",
            '{"facts":[{"name":"","value":"","confidence":0.0,"fact_type":"decision",'
            '"relationships":[{"target_fact_name":"","relationship_type":"related_to","confidence":0.0}]}]}.',
            "Rules:",
            "- Extract only explicit atomic facts grounded in the source text.",
            "- Never output summaries, implications, or combined facts.",
            "- Use fact_type only from: decision, action_item, blocker, discussion.",
            "- Prefer concise, canonical fact names.",
            "- Use relationships only when the source text explicitly states them.",
            "- Confidence should reflect extraction certainty, not business importance.",
            "- If the document contains more than the limit, keep only the highest-signal facts: decisions first, then blockers, then action items, then discussion.",
            f"- Return at most {settings.extraction_max_facts_per_document} facts.",
            f"- Source context label: {source_context}",
            f"- Connector: {doc.connector_type.value}",
            f"- Metadata: {json.dumps(metadata, sort_keys=True)}",
            f"- Author: {doc.author or ''}",
            f"- Source URL: {doc.source_url or ''}",
        ]

        if few_shot:
            prompt_parts.append(f"\nExamples for {connector_key}:\n{few_shot}")

        prompt_parts.append(f"\nDocument:\n{doc.content}")
        return "\n".join(prompt_parts)

    def _normalize_facts(
        self,
        doc: "SourceDocument",
        payload: StructuredExtractionPayload,
    ) -> list[ExtractedFact]:
        source_context = RegexExtractor._source_context_label(doc.metadata_json or {})
        deduped: list[ExtractedFact] = []
        seen: set[tuple[str, str, str]] = set()

        for fact in payload.facts:
            name = self._normalize_fact_name(
                fact.name,
                fact.fact_type,
                source_context=source_context,
            )
            value = re.sub(r"\s+", " ", fact.value).strip()
            key = (name.lower(), value.lower(), fact.fact_type)
            if key in seen:
                continue

            relationships = self._normalize_relationships(fact.relationships)
            deduped.append(
                ExtractedFact(
                    name=name,
                    value=value,
                    confidence=round(min(max(fact.confidence, 0.0), 1.0), 2),
                    fact_type=fact.fact_type,
                    relationships=relationships,
                    extractor=self._metadata,
                )
            )
            seen.add(key)
            if len(deduped) >= settings.extraction_max_facts_per_document:
                break

        return deduped

    @staticmethod
    def _normalize_relationships(
        relationships: list[StructuredRelationshipPayload],
    ) -> list[ExtractedRelationship]:
        deduped: list[ExtractedRelationship] = []
        seen: set[tuple[str, str]] = set()
        for relationship in relationships:
            target_name = re.sub(r"\s+", " ", relationship.target_fact_name).strip()
            key = (target_name.lower(), relationship.relationship_type)
            if not target_name or key in seen:
                continue
            deduped.append(
                ExtractedRelationship(
                    target_fact_name=target_name,
                    relationship_type=relationship.relationship_type,
                    confidence=round(
                        min(max(relationship.confidence, 0.0), 1.0),
                        2,
                    ),
                )
            )
            seen.add(key)
        return deduped

    @staticmethod
    def _normalize_fact_name(
        name: str,
        fact_type: FactType,
        *,
        source_context: str,
    ) -> str:
        cleaned = re.sub(r"\s+", " ", name).strip(" :")
        cleaned_lower = cleaned.lower()
        if not cleaned or cleaned_lower in _GENERIC_FACT_NAMES:
            return f"{_DEFAULT_FACT_NAMES[fact_type]} in {source_context}"
        return cleaned

    @staticmethod
    def _parse_payload(raw_output: Any) -> StructuredExtractionPayload:
        try:
            if isinstance(raw_output, StructuredExtractionPayload):
                return raw_output
            if isinstance(raw_output, str):
                return StructuredExtractionPayload.model_validate_json(raw_output)
            return StructuredExtractionPayload.model_validate(raw_output)
        except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ExtractionError("Structured extraction returned malformed output") from exc


class FallbackExtractor(BaseExtractor):
    """Attempt structured extraction first, then fall back to regex."""

    def __init__(self, primary: BaseExtractor, fallback: BaseExtractor) -> None:
        self.primary = primary
        self.fallback = fallback

    async def extract(self, doc: "SourceDocument") -> list[ExtractedFact]:
        try:
            facts = await self.primary.extract(doc)
            if facts:
                return facts
        except ExtractionError:
            pass
        return await self.fallback.extract(doc)


def build_default_extractor() -> BaseExtractor:
    regex = RegexExtractor()
    model = _resolved_extraction_model()
    if not model:
        if settings.environment == "production":
            raise ExtractionError(
                "Production extraction requires EXTRACTION_MODEL or LITELLM_API_KEY "
                "with DEFAULT_EXTRACTION_MODEL."
            )
        return regex
    structured = StructuredLLMExtractor(model=model)
    if settings.enable_regex_extraction_fallback:
        return FallbackExtractor(
            primary=structured,
            fallback=RegexExtractor(extractor_name="regex_fallback"),
        )
    return structured


def _resolved_extraction_model() -> str | None:
    if settings.extraction_model:
        return settings.extraction_model
    if (
        settings.enable_default_provider_models
        and has_live_litellm_api_key()
        and settings.default_extraction_model
    ):
        return settings.default_extraction_model
    return None
