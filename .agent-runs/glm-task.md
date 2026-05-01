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

Implement connector and AI-context ingestion slices without faking unsupported providers.

Current priorities:

- keep backend connector catalog and frontend connector catalog aligned;
- expose AI Context in the frontend connector data;
- keep unsupported providers disabled or explicitly unsupported;
- preserve AI-context metadata and source provenance;
- add focused backend tests for connector behavior.

## Boundaries

- Do not implement real Slack, Discord, Gmail, Zoom, or Google OAuth unless explicitly assigned.
- Do not mark an external provider as connected unless sync is tested.
- Do not rewrite graph extraction unless coordinating with Qwen.

## Final Report

Include files changed, endpoints changed, tests run, evidence for connector claims, and limitations.

