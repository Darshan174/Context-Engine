# Qwen Task — Deterministic Founder Scrutiny

## Role

You are Qwen, graph reasoning checker, schema reviewer, and hard-bug solver. Start
after the focused run contract and observation payload are stable.

## Mission

Implement and adversarially verify a small scrutiny engine that tells a founder
what lacks evidence without pretending to judge code or infer agent intent.

## Initial supported findings

- required verification is missing;
- verification failed;
- a recorded blocker is unresolved;
- a required context item has no completion evidence;
- the claimed outcome conflicts with recorded checks;
- provider or repository state is too stale for a current-state claim.

Every finding must contain:

- deterministic rule identifier and version;
- factual title and founder-readable explanation;
- severity based on an explicit rule, not an LLM score;
- context-pack/run/focus identifiers;
- triggering evidence or observation identifiers;
- observed and evaluated timestamps;
- resolution state without deleting its history.

## Product representation

- Project map: compact counts for Blocked, Unverified, and Drifted/Stale only when
  non-zero or explicitly requested.
- Inspector/run timeline: finding detail, exact evidence, and the next useful action.
- `Challenge agent`: generate questions from findings, citing the triggering source.
  Generated questions are prompts for scrutiny, not new factual Components.
- No new route, generic score, autonomous rejection, or uncited criticism.

## Reasoning constraints

- `No completion evidence` is not the same as `ignored`.
- A changed production file without a matching test is a review signal, not proof of
  bad code.
- A passing unrelated test is not verification of a requirement.
- The latest statement does not automatically override higher-authority evidence.
- Findings must respect workspace and project relevance before graph expansion.

## Acceptance gates

- Unit tests cover every rule's positive, negative, stale, cross-workspace, and
  duplicate-evaluation cases.
- Adversarial tests prove the service does not create findings from ambiguous text.
- Every UI finding links to the exact evidence used by the rule.
- Empty/healthy projects remain calm; the Attention surface does not become a
  permanent wall of green status cards.
- Focused/full tests and production build pass.

## Report

Include changed files, rules implemented, tests, evidence, false-positive risks,
remaining gaps, and any proposed bi-temporal follow-up. Do not overclaim agent
quality measurement.
