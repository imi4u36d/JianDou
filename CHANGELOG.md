# Changelog

All notable changes to JianDou will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-07-13

### Added

- Added explicit backend and frontend application bootstrap modules while preserving existing public entry points.
- Added domain-specific frontend contract entry points, shared query serialization, compatibility checks, and import-boundary lint rules.
- Added maintainability and incremental refactoring guides with automated module-boundary and source-size guardrails.
- Expanded backend regression coverage and frontend component, composable, presenter, and API tests.

### Changed

- Split oversized backend repositories, routers, provider integrations, task execution services, and workflow services into focused collaborators behind stable facades.
- Split large Vue views into focused components, composables, presenters, type modules, and view-owned styles.
- Standardized frontend API query serialization, identifier encoding, domain-owned type imports, and lazy admin application setup.
- Upgraded Vue, Vue Router, TypeScript, Vite, Vitest, ESLint, Tailwind CSS, and related frontend tooling.
- Made frontend lint and test failures mandatory CI gates, sourced the Node version from `.nvmrc`, and updated the deployment SSH action.
- Updated backend dependency constraints and the bundled OpenAI-compatible provider base URL.

### Fixed

- Improved task detail progress presentation and styling.
- Tightened lightweight task-query regression assertions after dependency integration.

### Compatibility

- No database migration is required when upgrading from `0.2.0-rc.1`.
- Existing backend entry points, route paths, compatibility type exports, and request/response contracts remain supported.

### Known limitations

- Database-backed integration tests still require `JIANDOU_TEST_DATABASE_URL`.
- Provider availability depends on deployment-specific endpoints and credentials; deployments using the bundled OpenAI-compatible endpoint should verify network reachability.

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
