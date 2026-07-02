# Changelog

All notable changes to JianDou will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0-rc.1] - 2026-07-02

### Added

- Image task management with dedicated image task list, selection, preview, and backend query support.
- Material asset renaming so users can update asset names from the material library.
- Prompt detail dialog for viewing and managing task prompts.
- Persisted user generation preferences with a resumable database migration.
- Manual deployment workflow and main-branch deployment trigger after pull request merges.
- Login carousel background assets and page zoom prevention for the web frontend.

### Changed

- Refined task detail, workflow, and material library experiences for image-generation tasks.
- Removed style preset references from task and workflow request paths.
- Updated OpenAI provider default base URL configuration.
- Enabled gzip compression in the web nginx configuration.

### Fixed

- Improved task preview cache handling for updated image task outputs.

## [0.1.0] - 2026-06-26

### Added

- Initial alpha codebase for JianDou text-to-video workflows.
- Frontend open-source readiness: ESLint + Prettier code-quality tooling, Vitest test framework with 15 initial unit tests, and frontend architecture documentation at `docs/frontend-architecture.md`.
- `.editorconfig`, `.nvmrc`, and `.gitattributes` for consistent editor settings and line endings across contributors.
- Frontend-specific UI bug issue template.
- CI frontend-checks job: lint, typecheck, test, and build gates before Docker image build.
- Frontend `.env.example` documenting `VITE_API_PROXY_TARGET`.
- README development section covering frontend and backend dev workflows.
- CONTRIBUTING.md frontend guidelines and updated PR checklist with web:lint, web:typecheck, and web:test.

- Open-source project hygiene: contribution guide, security policy, code of conduct, issue templates, pull request template, and CI.
- Alembic baseline migrations and database metadata/constraint tests.
- Backend security hardening for DB-backed admin role checks, origin validation, auth rate limiting, security headers, readiness checks, and encrypted user model credentials.
- Docker deployment path with frontend build, automatic migrations, readiness healthcheck, and Docker-specific environment example.
- OpenAPI export command and release preflight script.
- Configuration, database design, and backend architecture documentation.

- **Backend refactoring — infrastructure layer**:
  - Extracted HTTP middleware into `backend/middleware/` (OriginGuard, SecurityHeaders, SPA fallback).
  - Centralised exception hierarchy in `backend/exceptions.py` with backward-compatible aliases.
  - DI container (`AppContainer`) in `backend/container.py` for lazy, testable service wiring.
  - Standardised HTTP error helpers in `backend/errors.py` for consistent router responses.
  - Centralised logging configuration in `backend/logging_config.py`.
  - `backend/shared.py` module with 20+ utility functions, eliminating ~80 duplicated helper definitions across 30+ files.

- **Backend refactoring — tests**:
  - Tests for new infrastructure modules: `test_errors.py`, `test_middleware.py`, `test_exceptions.py`, `test_container.py`, `test_shared.py` (106 new tests, 47 for shared utilities alone).

### Changed

- Removed generated frontend assets, local secrets, and runtime files from the tracked source tree.
- Clarified package metadata and Python wheel contents.

- **Backend refactoring — code organisation**:
  - Populated empty `__init__.py` files (domain, infrastructure, routers, schemas, services) with module-level docstrings.
  - Replaced wildcard imports in `models/__init__.py` with explicit class imports.
  - Added section-header comments to large files for navigability.
  - Extracted stub classes from `task_worker_service.py` into `backend/services/stubs.py`.
  - Removed global singletons from `generation_service.py`; wired through DI container.
  - Improved `config.py` with structured `validate_settings()` diagnostics.
  - Reorganised `.env.example` with section headers and comments for contributors.
  - Integrated exception hierarchy into `auth.py` with FastAPI exception handlers in `main.py`.
  - Achieved zero ruff lint errors across the entire `backend/` package.

### Security

- Platform secrets are kept out of version control via examples and repository hygiene tests.
- User-scoped model provider keys are encrypted at rest with a key derived from `JIANDOU_SECRET_KEY`.
