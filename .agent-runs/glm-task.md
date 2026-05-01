# GLM 5.1 Task

## Role

You are the primary implementation agent.

Work in this repo:

```text
/Users/darshann/Desktop/context-engine
```

Preferred branch:

```bash
agent/glm-connector-ai-context-implementation
```

## Focus

Implement the connector honesty and ingestion hardening slice without faking unsupported providers.

Current priorities:

- fix Slack so it cannot appear as a working/setup-complete connector unless real backend support exists;
- keep backend connector catalog and frontend connector catalog aligned;
- ensure AI Context and local import are the only clearly working ingestion paths unless tests prove otherwise;
- keep unsupported providers disabled, coming soon, or explicitly unsupported;
- preserve AI-context metadata and source provenance;
- add focused backend and frontend tests for connector behavior where patterns already exist.

## Required Workload

1. Fix the latest Codex P1 finding:
   - Slack is currently catalogued as available while `supported: false`.
   - The UI can expose setup paths that call missing `/connectors/slack/oauth-settings`.
   - Choose the smallest honest fix: mark Slack as `coming_soon` or fully implement the missing setup endpoint and tests. Prefer `coming_soon` unless the repo already has enough Slack backend structure.
2. Add tests proving unsupported provider behavior:
   - unsupported/coming-soon connectors cannot become connected;
   - unsupported/coming-soon sync attempts fail honestly;
   - connector records do not overstate readiness.
3. Add one positive AI Context/local ingestion regression test if missing:
   - source document is created;
   - source type and metadata are preserved;
   - processing summary counts AI-context variants correctly.
4. Check frontend connector controls:
   - no visible connect/setup path should post to a backend endpoint that does not exist;
   - backend coming-soon status should be reflected as disabled or unavailable in UI state.
5. Keep changes scoped. Do not build real OAuth integrations in this round.

## Boundaries

- Do not implement real Slack, Discord, Gmail, Zoom, or Google OAuth unless explicitly assigned.
- Do not mark an external provider as connected unless sync is tested.
- Do not rewrite graph extraction unless coordinating with Qwen.
- Do not hide AI Context or local ingestion while disabling external stubs.

## Final Report

Include files changed, endpoints changed, UI behavior changed, tests run, evidence for connector claims, and limitations.
