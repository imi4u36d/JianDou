# Changelog

All notable changes to JianDou will be documented in this file.

The format follows Keep a Changelog, and this project uses Semantic Versioning once release tags are published.

## [Unreleased]

### Added

- Open-source project hygiene: contribution guide, security policy, code of conduct, issue templates, pull request template, and CI.
- Alembic baseline migrations and database metadata/constraint tests.
- Backend security hardening for DB-backed admin role checks, origin validation, auth rate limiting, security headers, readiness checks, and encrypted user model credentials.
- Docker deployment path with frontend build, automatic migrations, readiness healthcheck, and Docker-specific environment example.
- OpenAPI export command and release preflight script.
- Configuration, database design, and backend architecture documentation.

### Changed

- Removed generated frontend assets, local secrets, and runtime files from the tracked source tree.
- Clarified package metadata and Python wheel contents.

### Security

- Platform secrets are kept out of version control via examples and repository hygiene tests.
- User-scoped model provider keys are encrypted at rest with a key derived from `JIANDOU_SECRET_KEY`.

## [0.1.0] - 2026-06-19

### Added

- Initial alpha codebase for JianDou text-to-video workflows.
