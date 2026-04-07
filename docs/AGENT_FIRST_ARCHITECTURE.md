# Agent-First Architecture

## Goal

Replace tool-specific flows with a unified multi-agent runtime. The system treats:

- `drama-editor`
- `media-artist`
- `script-writer`

as first-class AI agents with the same lifecycle, observability model, and operator experience.

## Core Model

### Agent Definition

Static capability metadata used by frontend and backend:

- key
- title
- summary
- capability tags
- accepted input schema
- supported output artifact kinds
- default visual theme tokens

### Agent Run

A persisted execution record for any agent invocation:

- `id`
- `agent_key`
- `title`
- `status`
- `input_payload_json`
- `output_summary`
- `model_name`
- `started_at`
- `finished_at`
- `duration_ms`
- `error_message`

### Agent Artifact

Any produced or attached material:

- `id`
- `run_id`
- `kind`
- `role`
- `name`
- `mime_type`
- `storage_path`
- `public_url`
- `text_content`
- `metadata_json`

Examples:

- uploaded source video
- generated image
- generated video
- markdown script
- clip plan JSON

### Agent Event

Structured timeline entries for logs and monitoring:

- `id`
- `run_id`
- `level`
- `stage`
- `event`
- `message`
- `payload_json`
- `created_at`

## Backend Boundaries

### Agent Registry

Single registry maps `agent_key` to:

- public agent metadata
- input normalization
- handler implementation
- output artifact shaping

### Agent Runtime

Unified methods:

- list agents
- create run
- execute run
- list run history
- fetch run detail
- fetch dashboard summary

### Agent Handlers

Each handler implements domain-specific execution but returns the same runtime contract.

- `drama-editor`: short drama planning / clip generation flow
- `media-artist`: text-to-image / text-to-video generation
- `script-writer`: text-to-script generation

## API Shape

- `GET /api/v1/agents`
- `GET /api/v1/agents/dashboard`
- `POST /api/v1/agents/runs`
- `GET /api/v1/agents/runs`
- `GET /api/v1/agents/runs/{id}`
- `POST /api/v1/uploads/videos`

The frontend should not need agent-specific endpoints for history, logs, or monitoring.

## Frontend Shape

Single operator workspace:

- top hero + mission control summary
- equal-weight agent cards
- unified run composer panel
- unified run history rail
- unified run detail inspector
- artifact preview region
- event/log timeline

## UX Rules

- All agents share one information hierarchy.
- Each agent gets its own accent and copy, but not a different IA.
- History, logs, and monitoring are visually and structurally consistent.
- Artifact previews adapt by type, not by page.

## Non-Goals

- Backward compatibility with legacy pages or payloads
- Preserving old route structure
- Preserving old task-only naming
