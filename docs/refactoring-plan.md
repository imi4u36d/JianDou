# Refactoring Plan

This document tracks the incremental standardization of JianDou. Each phase should stay reviewable, preserve compatibility, and pass the existing quality gates before merge.

## Phase 1: Application foundation

- Extract backend application assembly from `backend/main.py` while preserving the public import path.
- Extract frontend bootstrap and lazy admin UI registration from `src/main.ts`.
- Make frontend lint and test failures fail CI instead of being silently ignored.

## Phase 2: Frontend domain boundaries

- Split the large `src/types/index.ts` barrel into domain-focused modules.
- Keep a compatibility barrel while callers migrate gradually.
- Reduce lint exclusions by decomposing oversized views.

## Phase 3: Backend service boundaries

- Split large orchestration services by use case and provider responsibility.
- Remove file-level Ruff exceptions as modules become focused.
- Strengthen repository and transaction boundaries.

## Phase 4: Infrastructure hardening

- Evaluate migration from string timestamps to timezone-aware database columns.
- Move distributed rate limiting to Redis-backed infrastructure.
- Add focused architecture tests for dependency direction and module ownership.
