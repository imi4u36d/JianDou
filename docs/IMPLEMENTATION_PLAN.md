# AI Cut Implementation Plan

## 1. Goal

Deliver a first runnable version of AI Cut that can:

- upload a local video
- create an editing job with constrained parameters
- run Qwen-assisted clip planning
- render multiple short-video outputs with FFmpeg
- show progress and final downloadable outputs in the web UI

This plan assumes the confirmed stack:

- Vue + TypeScript + Vite frontend
- FastAPI backend
- local MySQL and Redis
- Qwen provider
- local filesystem storage
- FFmpeg-based rendering pipeline
- `execution_mode` toggle for inline and queued execution

## 2. Delivery Principles

- Build one end-to-end happy path first.
- Keep all APIs and pipeline contracts stable before adding advanced editing features.
- Use `inline` mode to get the first vertical slice working, then switch to `queue`.
- Prefer deterministic rules around output count, duration range, and templates.

## 3. Phase Breakdown

## Phase 0: Project Baseline

Objective:

Create the minimum runtime baseline so every agent can work against the same constraints.

Scope:

- confirm config loading from `config/app.toml`
- confirm `execution_mode`, MySQL, Redis, storage, and model settings are readable
- define shared status enums and basic DTOs
- align local directory conventions under `storage/`

Exit criteria:

- API, web, and worker can boot with the same config contract
- directories for uploads, temp, and outputs are established

## Phase 1: Job Creation Vertical Slice

Objective:

Allow a user to upload a video and create an edit job from the web UI.

Frontend:

- upload form
- parameter form:
  - min duration
  - max duration
  - output count
  - aspect ratio
  - intro template
  - outro template
- task creation request
- task detail page with initial status

Backend:

- upload endpoint
- job creation endpoint
- job detail endpoint
- basic parameter validation against config limits
- MySQL persistence for source asset and edit job

Storage:

- save uploads to `storage/uploads`
- record relative paths and metadata

Exit criteria:

- a user can upload a source file and see a persisted pending job

## Phase 2: Inline Pipeline Happy Path

Objective:

Run the full pipeline in `execution_mode=inline` to validate stage contracts without queue complexity.

Pipeline stages:

1. ingest
2. normalize
3. analyze
4. plan
5. render
6. validate
7. publish

Implementation focus:

- central pipeline entrypoint in `packages/pipeline`
- FFprobe metadata extraction
- optional source normalization through FFmpeg
- structured Qwen request for clip candidate planning
- deterministic render assembly using intro, body, outro
- final output persistence under `storage/outputs`

Exit criteria:

- one job can generate at least one playable output end to end in inline mode
- job status and error states are visible in the UI

## Phase 3: Multi-Output Rendering

Objective:

Support generation of multiple assets from a single source within configured limits.

Scope:

- enforce `max_output_count`
- persist one output record per generated asset
- render multiple candidates in a single job
- expose preview and download URLs
- display per-output metadata in the UI

Validation focus:

- each output respects min and max duration
- each output is independently tracked for success or failure

Exit criteria:

- a single job can produce multiple valid outputs and partial failures are visible

## Phase 4: Queue Mode and Worker Split

Objective:

Move heavy work out of the API process while preserving the same business flow.

Scope:

- implement Redis-backed dispatch for `execution_mode=queue`
- worker consumes jobs and updates pipeline stage state
- API returns immediately after enqueue
- web UI polls job status until completion

Behavior requirements:

- inline and queue modes share the same pipeline code
- queue mode must not change request or response shapes
- status transitions remain consistent across modes

Exit criteria:

- the same job succeeds in both `inline` and `queue`
- API stays responsive during heavy rendering

## Phase 5: Operator Experience Hardening

Objective:

Make the system usable for repeated operator workflows instead of one-off demos.

Frontend:

- clearer progress timeline by stage
- failure display with actionable messages
- output gallery with duration and resolution
- retry or rerender entry points where supported

Backend and worker:

- retry policy for transient model failures
- better FFmpeg failure logging
- cleanup rules for temp artifacts
- basic audit fields such as created time and updated time

Exit criteria:

- operators can understand why a job failed and what completed successfully

## 4. Backend Work Packages

### 4.1 API Package

Primary work:

- config bootstrap
- health endpoint
- upload, create job, query job, list outputs APIs
- storage file serving for local previews

Acceptance:

- all write APIs validate request bounds and template ids

### 4.2 DB Package

Primary work:

- MySQL schema definition
- migration setup
- repositories for jobs, assets, outputs, pipeline runs

Acceptance:

- job lifecycle and output lifecycle are queryable by id

### 4.3 AI Package

Primary work:

- Qwen provider client
- prompt and response schema definition
- robust parsing and fallback behavior

Acceptance:

- malformed model output cannot crash the whole service path silently

### 4.4 Media Package

Primary work:

- probe helper
- normalize helper
- trim and concat helper
- aspect-ratio helper
- output validator

Acceptance:

- FFmpeg command composition is centralized rather than duplicated across services

### 4.5 Pipeline Package

Primary work:

- stage definitions
- state machine
- stage context model
- execution summary and error recording

Acceptance:

- pipeline logic is callable from both API inline mode and worker queue mode

## 5. Frontend Work Packages

### 5.1 Pages

- create job page
- job list page
- job detail page
- output preview page if separated from detail

### 5.2 Shared UI

- upload component
- parameter panel
- status badge and progress timeline
- output card list
- error panel

### 5.3 State and API

- typed API client
- job polling strategy
- optimistic loading states for upload and creation

Acceptance:

- the web app reflects stage transitions and output availability without manual refresh gymnastics

## 6. Configuration Plan

The following config areas must be treated as first-class runtime inputs:

- `[app]`
  - `execution_mode`
  - API host and port
  - allowed web origin
- `[database]`
  - MySQL connection string
- `[redis]`
  - Redis connection string
- `[storage]`
  - root, uploads, temp, outputs, public base URL
- `[model]`
  - provider, model name, endpoint, timeout, API key
- `[pipeline]`
  - default aspect ratio
  - max output count
  - max source minutes
  - default intro and outro template

Implementation rules:

- all config values should load once and be injected into API and worker
- validation errors in config should fail fast at startup
- `execution_mode` is required to avoid hidden defaults in production-like runs

## 7. Testing and Acceptance Plan

### 7.1 Must-pass acceptance cases

- upload a valid mp4 and create a job successfully
- reject invalid duration ranges
- reject output counts above configured limits
- generate at least one playable output in inline mode
- generate the same job successfully in queue mode
- surface model failure and FFmpeg failure in job detail

### 7.2 Recommended automated coverage

- backend unit tests for parameter validation and state transitions
- package-level tests for Qwen response parsing
- package-level tests for FFmpeg command generation
- integration tests for create job to publish output
- frontend tests for form validation and task status rendering

## 8. Risks and Mitigations During Implementation

### Risk: model output is inconsistent

Mitigation:

- use strict schema parsing
- clamp durations and output count after model planning
- allow heuristic fallback when rationale is usable but timestamps need normalization

### Risk: local FFmpeg processing is slow

Mitigation:

- keep inline mode for debugging only
- move to queue mode quickly after vertical slice validation
- cache normalized inputs where possible

### Risk: local disk usage grows rapidly

Mitigation:

- separate uploads, temp, and outputs
- define cleanup policy for temp artifacts
- reuse intermediates instead of duplicating them

### Risk: too many features enter MVP

Mitigation:

- postpone free-form timeline editing
- postpone multi-provider AI routing
- postpone cloud object storage and distributed execution

## 9. Out of Scope for Phase One

- browser-side non-linear timeline editing
- collaborative review workflow
- AB test analytics integration with ad platforms
- multi-tenant permission system
- cloud object storage migration
- GPU-intensive multimodal frame-by-frame analysis

## 10. Recommended Execution Order

1. finalize shared config and status contracts
2. implement upload and job persistence
3. implement inline pipeline happy path
4. add Qwen planning and FFmpeg intro/outro rendering
5. expose output preview and download in web
6. add multi-output support
7. switch to queue mode with Redis worker
8. harden failures, retries, and cleanup

## 11. Definition of Done for First Release

The first release is complete when:

- a user can upload a local video from the Vue app
- the FastAPI service persists the job and parameters in MySQL
- the system can run in `inline` and `queue` modes via config
- Qwen planning produces constrained candidate clips
- FFmpeg renders final outputs with configured intro and outro behavior
- final assets are stored locally and previewable from the web app
- failure states are visible and actionable enough for debugging
