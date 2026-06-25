# Product Positioning

## One-Line Position

Context Engine is the open-source project graph for AI-native builders. It turns
agent runs, PRs, issues, chats, decisions, and documents into a visual map of
what happened, what is connected, what is blocked, and what to do next.

## First Audience

Solo founders and tiny teams using AI coding agents aggressively.

Their work is split across Codex, Claude Code, OpenCode, GitHub, chat, and local
files. One agent proposes a change, another edits the code, a PR carries a
partial implementation, and the next session starts without the decisions that
led there.

## Daily-Use Test

The graph is useful only if a user can open it and quickly learn:

- where the project stands;
- which work is blocked;
- what changed across AI sessions and code;
- which decisions are missing from implementation or documentation;
- which issues or assumptions are stale;
- what the next agent should know and do.

A connector directory or generic search dashboard is not enough.

## Product Wedge

The wedge is:

**Visual project mapping for people building with AI coding agents.**

AI coding-session memory and project progress tracking feed the graph. The graph
is the primary navigation surface and the headline product experience.

## Not The Product

Context Engine is not positioned as:

- enterprise search;
- a generic company knowledge graph;
- an all-in-one RAG platform;
- a dashboard that merely lists connected tools.

## Current Honest Boundary

Context Engine can import Codex, Claude Code, and OpenCode session content and
extract tasks, decisions, blockers, risks, and file references. A session ID is
stored for identity and provenance, but the project cannot currently retrieve a
remote session using only that ID.

GitHub, Slack, Gmail, Google Drive, local files, and imported AI sessions can
contribute source evidence. Unsupported or coming-soon connectors must remain
clearly labelled.
