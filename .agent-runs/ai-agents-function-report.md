# AI Agents Function Report

Date: 2026-05-04

## Scope

This report covers the in-project AI-agent surfaces related to knowledge-graph engineering:

- `GraphBuilderAgent`
- `GapDetectorAgent`
- `RelationshipAgent`
- `ContextPackAgent`
- API wrappers under `/api/agents/*`
- graph build/status endpoints under `/api/graph/build` and `/api/graph/agent-status`

It does not evaluate connector availability or provider OAuth.

## Summary

| Agent / Surface | Status | Evidence | Main Gap |
|---|---|---|---|
| `GraphBuilderAgent` | Partially functioning | `app/agents/graph_builder.py` processes pending `SourceDocument` rows through `IngestionService`, commits, and returns stats. `/api/graph/build` wraps it in `app/api/graph.py`. | Cross-document relationship inference is naive name-substring matching and creates `related_to` edges without explicit evidence/confidence/status fields in the constructor. |
| `GapDetectorAgent` | Functioning, rule-based; AI optional | `app/agents/gap_detector.py` loads components/relationships, computes stats, returns gaps/ready/blocked without an AI key. `tests/test_agents.py` verifies model-name normalization and unimplemented-decision behavior. | Rules depend heavily on existing relationship quality. If graph relationships are noisy or missing, gap output will be noisy or incomplete. |
| `RelationshipAgent` | Partially functioning | `app/agents/relationship_agent.py` returns a no-key message when API key/model are absent. With AI enabled, it parses suggestions and persists high-confidence proposed relationships. `tests/test_agents.py` verifies high-confidence persistence. | It trusts AI reasoning as evidence and needs stronger validation against source text before proposed relationships are shown prominently. |
| `ContextPackAgent` | Functioning, but under-tested | `app/agents/context_pack.py` has rule-based fallback and optional AI generation. It groups graph components and emits markdown handoff content. | No direct test coverage found in `tests/test_agents.py`; output quality depends on graph ontology and relationship evidence. |
| `/api/agents/gaps` | Functioning wrapper | `app/api/agents_api.py` instantiates `GapDetectorAgent` and returns Pydantic output. | Needs API-level tests if this is a product-critical endpoint. |
| `/api/agents/context-pack` | Functioning wrapper | `app/api/agents_api.py` instantiates `ContextPackAgent` and returns content/entity count/timestamp. | Needs API-level tests and selection/slice support for source-specific context packs. |
| `/api/agents/relationships` | Partially functioning wrapper | `app/api/agents_api.py` instantiates `RelationshipAgent` and returns suggestions/duplicates/message. | Should expose proposed relationship review semantics clearly in UI/API. |
| `/api/graph/build` | Partially functioning wrapper | `app/api/graph.py` instantiates `GraphBuilderAgent` with optional key/model and returns build stats. | Needs stronger tests around evidence-backed relationship inference and GitHub/AI-session source behavior. |
| `/api/graph/agent-status` | Functioning simple status | `app/api/graph.py` reports whether LLM extraction settings are configured. | Only reports configured extraction model, not live health or last build result. |

## Detailed Findings

### GraphBuilderAgent

Observed behavior:

- Selects pending `SourceDocument` rows where `processed_at` is null.
- Processes each document through `IngestionService.process_document`.
- Supports per-request `api_key` and `model`.
- Captures LLM fallback warnings from extractor `last_error`.
- Runs `_infer_cross_doc_relationships` after extraction.

Risk:

- `_infer_cross_doc_relationships` matches component names as substrings in other component values and creates `related_to` edges. This is useful as a rough bootstrap, but it is not yet robust knowledge-graph engineering. It can create weak relationships unless constrained by evidence, confidence, and status.

Recommendation:

- Keep document processing.
- Replace or downgrade substring inference into proposed/candidate edges with explicit evidence.
- Add adversarial tests before expanding this agent.

### GapDetectorAgent

Observed behavior:

- Works without an AI key.
- Computes graph stats by canonical model name.
- Flags missing owners, unimplemented decisions, blocked items, and orphaned entities.
- Can call AI analysis when both `api_key` and `model` are provided.

Test evidence:

- `tests/test_agents.py` includes `test_gap_detector_normalizes_legacy_plural_model_names`.

Risk:

- It is only as good as the graph. If relationships are missing, decisions appear unimplemented. If relationships are noisy, blockers and ready-to-ship lists may be misleading.

Recommendation:

- Keep it.
- Add tests against GitHub PR/issue and AI-session-derived graphs.

### RelationshipAgent

Observed behavior:

- Requires `api_key` and `model`; otherwise returns a configuration message.
- Sends a compact component/relationship dump to LiteLLM.
- Parses JSON suggestions.
- Persists suggestions with confidence >= 0.6 as `status="proposed"`.
- Canonicalizes relationship types.

Test evidence:

- `tests/test_agents.py` includes `test_relationship_agent_persists_high_confidence_suggestions`.

Risk:

- The AI prompt asks for hidden relationships and persists them as proposed. That is acceptable only if UI treats them as review candidates, not truth.
- Evidence is currently the AI-provided reasoning, not necessarily a source quote.

Recommendation:

- Keep it as a proposal agent.
- Require source evidence before promoting relationships to active.
- Hide proposed relationships by default or visually distinguish them.

### ContextPackAgent

Observed behavior:

- Works without an AI key via `_rule_pack`.
- Optional AI generation when `api_key` and `model` are present.
- Includes current state, decisions, blockers, past AI agent attempts, next tasks, and key relationships when present.

Risk:

- No direct tests were found for generated context-pack behavior.
- Current output is whole-graph oriented, not source/slice oriented. For GitHub PR or AI markdown session workflows, context packs should be generated from selected graph slices.

Recommendation:

- Add tests.
- Add selection/slice support.
- Include evidence/provenance in context packs when used for coding-agent handoff.

## Overall Assessment

The project AI agents are present and mostly callable. The rule-based agents can function without an AI key, and the AI-backed agents degrade gracefully when no key/model is provided.

They are not yet sufficient for the new knowledge-graph product bar. The main missing engineering is not whether the agents run; it is whether their outputs are evidence-backed, source-specific, reviewable, and safe to display as knowledge.

## Priority Fixes

1. Add direct tests for `ContextPackAgent`.
2. Constrain `GraphBuilderAgent` relationship inference to evidence-backed or proposed relationships.
3. Add API tests for `/api/agents/gaps`, `/api/agents/context-pack`, and `/api/agents/relationships`.
4. Add GitHub issue/PR and AI markdown session fixtures to test graph-agent behavior.
5. Ensure proposed relationships from `RelationshipAgent` are visually distinct and not treated as confirmed truth.
