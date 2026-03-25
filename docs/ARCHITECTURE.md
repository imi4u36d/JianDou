# AI Cut Architecture

## 1. Scope

AI Cut is a local-first AI short-drama editing platform. Users upload a source video, configure editing parameters, and generate multiple ad-ready assets for distribution platforms. The first phase focuses on stable batch generation rather than a full non-linear editor.

Confirmed technical constraints:

- Frontend: Vue 3 + TypeScript + Vite
- Backend: FastAPI
- Database: local MySQL
- Queue/cache: local Redis
- Model provider: Qwen-compatible API
- Storage: local filesystem under `storage/`
- Media engine: FFmpeg pipeline
- Runtime switch: `execution_mode` in `config/app.toml`

## 2. Architecture Goals

- Keep the first phase runnable on a single developer machine.
- Separate AI understanding from deterministic media processing.
- Make long-running work asynchronous by default.
- Preserve reusable intermediate artifacts to control cost.
- Keep the repo modular without splitting into multiple repositories.

## 3. Repository Layout

The current repository is implemented as:

- `apps/web`
  - Vue + TypeScript + Vite operator console
- `apps/api`
  - FastAPI HTTP API, task creation, result query, config exposure
- `apps/worker`
  - background execution entrypoint for queued jobs
- `packages/backend_core`
  - shared backend runtime, config loader, models, storage, planner, FFmpeg helpers, worker utilities
- `config`
  - local TOML configuration
- `storage`
  - uploads, outputs, temporary files, reusable intermediates

The long-term split can evolve from `packages/backend_core` into finer packages such as `db`, `storage`, `ai`, `media`, and `pipeline`, but the current implementation keeps them together to reduce early-stage complexity.

## 4. Technology Stack

### 4.1 Frontend

- Vue 3 for the operator UI
- TypeScript for typed request and response contracts
- Vite for fast local development and build
- Recommended supporting libraries:
  - Vue Router for task list, create task, detail, and preview routes
  - Pinia for UI state and task polling state
  - Axios or native `fetch` wrapper for API access
  - Video.js or native video element for preview playback

### 4.2 Backend

- FastAPI for synchronous APIs and lightweight admin endpoints
- Pydantic models for request validation and structured responses
- SQLAlchemy or SQLModel for MySQL access
- Redis for queue coordination, task status cache, and worker signaling

### 4.3 AI Layer

- Qwen-compatible provider defined in `[model]`
- Structured prompt output for:
  - plot segmentation
  - highlight candidate selection
  - title and copy suggestions
  - optional intro/outro copy variants

The model layer does not produce frame-accurate editing commands. It only returns structured candidate plans and metadata.

### 4.4 Media Layer

- FFmpeg for normalize, trim, concat, scale, subtitle burn-in, intro/outro stitching
- FFprobe for metadata extraction
- Optional heuristic preprocessors:
  - transcript ingestion if available
  - silence detection
  - scene split heuristics

## 5. Service Boundaries

### 5.1 `apps/web`

Responsibilities:

- upload source files
- collect editing parameters
- submit generation jobs
- display task progress and failure reasons
- preview outputs and download artifacts

Non-responsibilities:

- no in-browser rendering
- no direct model invocation
- no heavy media processing

### 5.2 `apps/api`

Responsibilities:

- expose upload and task APIs
- validate business rules
- persist job records and asset metadata
- dispatch pipeline execution according to `execution_mode`
- serve storage-backed preview URLs

Non-responsibilities:

- no long-running FFmpeg execution in request handlers unless explicitly allowed by `execution_mode=inline`

### 5.3 `apps/worker`

Responsibilities:

- run asynchronous pipeline stages
- update progress and stage state
- manage retries and failure persistence
- isolate heavy FFmpeg and AI calls from the API process

### 5.4 `packages/pipeline`

Responsibilities:

- define stage order
- define input and output contracts per stage
- centralize state transitions and idempotency rules

Suggested stage sequence:

1. ingest
2. normalize
3. analyze
4. plan
5. render
6. validate
7. publish

### 5.5 `packages/ai`

Responsibilities:

- provider abstraction for Qwen
- prompt versioning
- parsing and validation of structured model outputs
- graceful fallback to heuristics if model output is incomplete

### 5.6 `packages/media`

Responsibilities:

- FFmpeg/FFprobe wrapper layer
- reusable render primitives
- deterministic asset generation
- output validation such as duration, resolution, and playability

## 6. Core Data Flow

### 6.1 Upload and Job Creation

1. User uploads a source video from the web app.
2. API stores the file under `storage/uploads`.
3. API creates:
   - source asset record
   - edit job record
   - requested output spec records
4. API starts execution inline or enqueues to worker based on `execution_mode`.

### 6.2 Analysis and Planning

1. Pipeline reads source metadata with FFprobe.
2. Pipeline normalizes the source if codec or timing is unsuitable.
3. Pipeline prepares analysis inputs:
   - transcript if available
   - scene or silence hints
   - basic metadata
4. Qwen provider returns structured candidate clips and rationale.
5. Pipeline converts model output into constrained edit plans:
   - duration range
   - output count limit
   - aspect ratio
   - intro/outro template selection

### 6.3 Rendering and Publishing

1. Render stage executes FFmpeg commands for each output candidate.
2. Intro/outro assets are prepended or appended based on templates.
3. Outputs are stored under `storage/outputs`.
4. Validation stage checks:
   - file exists
   - duration matches constraints
   - output is decodable
   - expected dimensions are correct
5. API exposes final asset metadata for preview and download.

## 7. Async Execution and `execution_mode`

`execution_mode` is the runtime switch for development and local deployment.

Supported modes for phase one:

- `inline`
  - API executes the full pipeline in-process after job creation
  - useful for local debugging and simplest startup path
  - not suitable for concurrent production-like workloads

- `queue`
  - API only creates records and pushes tasks to Redis-backed workers
  - worker executes AI and FFmpeg stages out of band
  - recommended default once the first end-to-end flow is stable

Behavior rules:

- Both modes must share the same pipeline entrypoint and stage definitions.
- Job state semantics must remain identical across modes.
- Inline mode is for convenience, not a separate implementation path.

## 8. Data Model Overview

The exact schema can evolve, but the first version should include these entities:

- `source_assets`
  - original upload metadata and local path
- `edit_jobs`
  - one user request with parameters and current status
- `edit_job_outputs`
  - one generated asset target per candidate result
- `pipeline_runs`
  - stage-level execution records, retries, errors, timings
- `templates`
  - intro/outro template metadata and storage paths

Important fields:

- source duration and resolution
- requested min and max duration
- requested output count
- aspect ratio and target platform
- intro/outro template identifiers
- status, stage, progress percent, error message

## 9. Local Storage Strategy

Phase one uses local filesystem storage only.

Directory responsibilities:

- `storage/uploads`
  - original user uploads
- `storage/temp`
  - normalized source files, extracted clips, transient work files
- `storage/outputs`
  - final generated assets and preview derivatives

Rules:

- persist relative paths in MySQL, not absolute machine-specific paths
- keep temp and output naming deterministic by job id and output id
- allow reuse of normalized intermediates for rerendering

## 10. FFmpeg Pipeline Design

The media pipeline is deterministic and template-driven.

Primary operations:

- source probe
- normalize codec and frame rate if needed
- trim by time range
- optional scale and pad to target aspect ratio
- stitch intro segment
- stitch main clip
- stitch outro segment
- optional subtitle or text overlay
- export mp4 with platform-safe defaults

Pipeline constraints for MVP:

- prioritize mp4/h264/aac output
- prioritize 9:16 first, extend later to 16:9 and 1:1
- no timeline editor in phase one
- no arbitrary multi-track composition beyond intro/outro and simple overlays

## 11. Cost and Scalability Strategy

### 11.1 Cost Control

- cache intermediate analysis outputs
- reuse normalized media for repeated runs
- ask Qwen for candidate segments and rationale, not full editing scripts
- limit `max_output_count` through config and API validation
- keep intro/outro assets template-based instead of per-job custom composition

### 11.2 Scalability

- move from `inline` to `queue` without changing API contracts
- split worker concurrency by stage if needed later
- preserve storage abstraction so local files can later migrate to object storage
- preserve provider abstraction so Qwen can later coexist with other providers

## 12. Failure Handling

Expected failure classes:

- invalid or corrupted source media
- unsupported codecs
- model timeout or malformed output
- FFmpeg render failure
- filesystem path collision or missing file
- queue or Redis unavailability

Required handling:

- persist stage-level error messages
- make retries explicit and bounded
- fail individual outputs without always failing the whole job
- allow rerender from cached analysis when only render fails

## 13. Security and Operational Notes

- API keys stay only in local config and environment, never in frontend runtime config
- file upload validation must include extension and probe-based verification
- static preview URLs should be scoped to generated assets only
- local storage cleanup needs a retention rule to avoid disk exhaustion

## 14. Phase-One Architecture Summary

The phase-one system is a modular monorepo with a Vue operator UI, FastAPI application layer, Redis-backed asynchronous execution option, Qwen-based planning, local MySQL persistence, local filesystem storage, and an FFmpeg-centered render pipeline. The architecture intentionally optimizes for local development speed and clear upgrade paths rather than early microservice complexity.
