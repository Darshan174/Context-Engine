# Product Positioning

## One-line position

Context Engine compiles verified project history into the minimum task-ready
context a coding agent needs to continue real work on a long-running codebase.

## What the product is

Context Engine is an open-source context and evidence layer for coding agents.
It collects project history from repositories, issues, pull requests, imported
agent sessions, decisions, documents, and verification output, then prepares a
focused, source-backed brief for one current task.

The product does two connected jobs:

1. **For agents:** compile the relevant facts, files, constraints, blockers,
   exclusions, repository state, and verification commands into a task-sized
   context pack.
2. **For people:** show the evidence and relationships behind the current
   project state so the user can understand, inspect, and control what the next
   agent receives.

The context compiler is the core product. The graph is the human-readable
explanation and navigation surface around that compiler; it is not a separate
generic knowledge-graph product.

## First audience

Solo founders and tiny teams using coding agents every day.

Their work is split across Codex, Claude Code, OpenCode, GitHub, local files,
and team tools. One agent proposes a change, another edits the code, a pull
request carries a partial implementation, and the next session starts without
the decisions or failed checks that led there.

## Product loop

1. Connect or import evidence from one project.
2. Preserve the raw sources and their revisions.
3. Select the current goal explicitly.
4. Compile only the context relevant to that goal and target model.
5. Let the user inspect the selected evidence and exclusions.
6. Run a user-supplied worker command or copy the brief into another agent.
7. Record repository changes, checks, blockers, and outcome evidence for the
   next session.

## Daily-use test

A user should be able to open Context Engine and quickly learn:

- what the current goal is;
- where the project stands;
- what changed in recent agent runs and code;
- which blockers, risks, and failed checks are real;
- why a fact is believed and where it came from;
- what context the next agent will receive;
- what remains unresolved after the last run.

## Product wedge

The wedge is:

**Reliable continuity between coding-agent sessions on real codebases.**

The initial proof is not that Context Engine makes a weak model magically
smarter. It is that better task selection, verified history, less irrelevant
context, and explicit verification can help cheaper, older, or open models
complete more useful work than they would with a blank chat or an undirected
context dump.

## Not the product

Context Engine is not positioned as:

- another autonomous coding agent;
- a generic company knowledge graph;
- enterprise search;
- an all-in-one RAG platform;
- a connector directory;
- a dashboard that merely lists project activity;
- proof that smaller models already match frontier models.

## Current honest boundary

Context Engine currently provides a React app, FastAPI API, `ctxe` CLI, MCP
server, context compiler, source-backed project views, and a local harness that
wraps a user-supplied worker command and records bounded execution evidence.

The UI prepares and copies an agent brief; it does not automatically launch
Codex, Claude Code, OpenCode, or another provider. The local harness runs only
the explicit command supplied by the user. Model-lift reports describe observed
runs and do not yet prove general model equivalence.

Local repository and session imports are available. GitHub, Slack, Gmail, and
Google Drive have configured backend paths, but public onboarding is unfinished.
Unsupported and coming-soon connectors must remain clearly labelled.
