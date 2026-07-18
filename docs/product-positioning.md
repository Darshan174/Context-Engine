# Product Positioning

## One-line position

Context Engine is the open-source, self-hosted project-continuity layer for
people building software with coding agents. It preserves source-backed project
evidence, keeps the current goal explicit, prepares a focused handoff, and
records observed run results for the next agent.

## First audience

Solo founders and tiny teams using coding agents every day.

Their work is split across Codex, Claude Code, OpenCode, GitHub, chat, and local
files. One agent proposes a change, another edits the code, a pull request carries
part of the implementation, and the next session starts without the decisions
that led there.

## Product loop

1. **Sources and connectors** preserve repository state, coding sessions, issues,
   pull requests, documents, decisions, and verification evidence.
2. **Now** shows the active or latest coding work, its newest update and stated
   reason, verified outcomes, and evidence-backed blockers or risks.
3. **Prepare** compiles a bounded `context_pack.v2` brief with citations and
   explicit exclusions for one concrete task.
4. **The user runs the coding agent they choose.** The browser product does not
   select a provider or dispatch an agent.
5. **Runs** shows evidence captured by the optional local harness, which executes
   only the worker command the user supplied.
6. **Explain** visualizes the evidence and relationships behind the other
   surfaces.

The daily-use test is whether a user can identify where the project stands, what
is current, what is blocked or unverified, what changed, and what the next agent
needs without reconstructing the project from chat history.

## Role of the graph

The knowledge graph is an explanation and inspection surface. It supports Now,
Prepare, and Runs by showing why evidence is connected. It is not the primary
handoff artifact, a generic company knowledge graph, or the whole product.

## Not the product

Context Engine is not:

- another autonomous coding agent or provider router;
- enterprise search or an all-in-one RAG platform;
- a generic memory store or company knowledge graph;
- an autonomous code reviewer;
- a claim that a smaller model matches a frontier model.

## Current honest boundary

Context Engine can import Codex, Claude Code, and OpenCode session content and
extract tasks, decisions, blockers, risks, and file references. A session ID is
stored for identity and provenance, but the project cannot retrieve a remote
session using only that ID.

Already-imported local sessions refresh while Now is open. This reads only the
linked local session; it does not discover unrelated sessions or launch an agent.

Local repositories and files work as source evidence. GitHub, Slack, Gmail, and
Google Drive have configured integration paths. Discord, Zoom, and Wispr Flow are
coming soon; Notion is not catalogued. Availability must not be presented as a
hosted, zero-configuration connection flow.
