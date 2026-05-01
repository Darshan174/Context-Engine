# Xiaomi MiMo V2.5 Pro Task

## Role

You are the long-context repo reader, documentation reviewer, UX reviewer, and OSS readiness reviewer.

Work in this repo:

```text
/Users/darshann/Desktop/context-engine
```

Preferred branch:

```bash
agent/xiaomi-repo-review-docs
```

## Focus

Keep public docs, review docs, and OSS onboarding honest.

Review for:

- stale claims after implementation changes;
- connector claims that overstate support;
- frontend/backend catalog mismatch;
- broken onboarding commands;
- missing tests, CI, license, or contributor docs;
- graph provenance and relationship clarity.

## Required Workload

1. Fix the latest Codex doc findings:
   - `docs/oss-readiness.md` must not say backend catalog has only five connector types if code now has eight catalog entries.
   - `docs/connectors-graph-contract.md` must not say Zoom/GDrive/Wispr are absent from the backend catalog.
   - update the stale `pytest -q` result from 99 passed to the latest verified count after tests are rerun.
2. Refresh public docs for OSS contributors:
   - README/project docs should accurately describe the six current tables;
   - connector docs should explain real ingestion vs catalogued coming-soon stubs;
   - AI Context docs should explain local storage and source provenance clearly.
3. Add or update an OSS readiness checklist:
   - install/bootstrap command;
   - backend test command;
   - frontend build/test command;
   - known unsupported providers;
   - current launch blockers.
4. Review UI wording for connector honesty:
   - no provider should be described as seamless/connected unless there is a tested flow;
   - coming-soon providers should tell contributors what is missing.
5. Final review pass:
   - search for stale phrases such as old test counts, old table counts, and unsupported-provider overclaims;
   - report exact files/lines for anything left unfixed.

## Final Report

Include files changed, tests/docs reviewed, stale claims removed, top findings by severity, OSS readiness score, and remaining launch blockers.
