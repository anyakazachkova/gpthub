# AI Workspace Fork

This fork uses Open WebUI as the base platform and adds an orchestration layer for a single conversational workspace.

## Product goal

The target experience is a single chat window where the user can handle:

- text requests
- voice and audio scenarios
- image generation and image understanding
- file Q&A
- web search and link-driven research
- long-running conversations that reuse saved user context

## What is already added in this fork

### 1. AI Workspace Router

Backend route: `POST /api/v1/ai-workspace/route`

The router inspects:

- prompt text
- attached files
- currently selected models
- current feature state

It classifies the request into one of the workspace tasks:

- `general_chat`
- `file_analysis`
- `image_analysis`
- `image_generation`
- `image_editing`
- `audio_workflow`
- `web_research`
- `link_parsing`

Then it returns:

- the recommended model for this turn
- the capabilities that mattered
- per-turn feature flags such as `web_search` and `image_generation`
- a short explanation that can be shown in the UI

### 2. Auto / Manual model routing in the chat UI

The chat header now includes:

- `Auto` mode: the router picks the best model and features for the current request
- `Manual` mode: the user keeps explicit control over model selection

The selected route is shown inline in the header so the auto behavior is visible and debuggable.

### 3. Live route preview in the composer

The workspace now previews routing before the message is sent.

As the user types, attaches files, or adds links, the UI updates with:

- detected task type
- suggested model
- enabled tools and features for the turn
- workflow steps for the request
- whether memory is recommended for continuity

This makes the orchestration transparent instead of feeling like a hidden rule engine.

### 4. Reuse of existing Open WebUI strengths

This fork intentionally builds on native Open WebUI capabilities instead of replacing them:

- memories for persistent user facts
- retrieval and file context for document chat
- web search integrations
- image generation integrations
- audio stack already present in the base project

## Current implementation notes

- Auto routing is request-level, not a permanent change to the user's default model list.
- Manual `@model` targeting still wins over auto routing.
- Saved memories are not reimplemented; the router is designed to work with Open WebUI's existing memory system.
- Route previews are debounced in the chat composer so the UX stays responsive while typing.

## Recommended next steps

1. Add a dedicated workspace settings screen for routing policies and memory behavior.
2. Extend routing from heuristic rules to scored policies configurable per team.
3. Add task-specific tool presets, especially for link parsing and structured web extraction.
4. Add analytics for route decisions, selected models, and fallback reasons.
5. Add end-to-end frontend checks once a Node-enabled CI environment is available.
