# Refactoring Plan

This document tracks the incremental standardization of JianDou. Each phase should stay reviewable, preserve compatibility, and pass the existing quality gates before merge.

## Phase 1: Application foundation — completed

- [x] Extract backend application assembly from `backend/main.py` while preserving the public import path.
- [x] Extract frontend bootstrap and lazy admin UI registration from `src/main.ts`.
- [x] Make frontend lint and test failures fail CI instead of being silently ignored.

## Phase 2: Frontend domain boundaries — in progress

- [x] Introduce domain-scoped type entry points while keeping `src/types/index.ts` as a compatibility barrel.
- [x] Migrate authentication and the first API modules to explicit domain contract imports.
- [x] Centralize optional query-string serialization and cover its edge cases with unit tests.
- [x] Move auth, credit, health, public-share, and upload definitions out of `src/types/index.ts`.
- [x] Migrate generation, workflow, and material API modules to explicit domain contract imports.
- [ ] Move task, generation, workflow, material, and admin definitions out of `src/types/index.ts`.
- [ ] Migrate the remaining component and composable imports.
- [ ] Reduce lint exclusions by decomposing oversized views.

## Phase 3: Backend service boundaries

- [ ] Split large orchestration services by use case and provider responsibility.
- [ ] Remove file-level Ruff exceptions as modules become focused.
- [ ] Strengthen repository and transaction boundaries.

## Phase 4: Infrastructure hardening

- [ ] Evaluate migration from string timestamps to timezone-aware database columns.
- [ ] Move distributed rate limiting to Redis-backed infrastructure.
- [ ] Add focused architecture tests for dependency direction and module ownership.
