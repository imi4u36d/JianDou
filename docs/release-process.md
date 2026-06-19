# Release Process

This project is still in alpha, but releases should be repeatable and auditable.

## Versioning

JianDou uses Semantic Versioning once public release tags are published:

- Patch releases fix bugs, documentation, packaging, or deployment behavior without changing supported APIs.
- Minor releases add backwards-compatible features or new supported provider/model capabilities.
- Major releases may remove compatibility aliases, migrate schemas in incompatible ways, or change public API contracts.

Keep these version fields aligned when cutting a release:

- `pyproject.toml`
- root `package.json`
- workspace package manifests under `frontends/` and `packages/` when their published contracts change.

## Before Opening A Release PR

1. Move completed entries from `CHANGELOG.md` `[Unreleased]` into a dated version section.
2. Update version fields.
3. Run `npm run release:check`.
4. For Docker-facing changes, run `docker build -t jiandou:release-check .` when Docker is available.
5. Confirm generated artifacts are not left in the worktree:
   - `build/`
   - `dist/`
   - `jiandou.egg-info/`
   - `docs/openapi.json`
   - `static/web/assets/`
   - `static/web/index.html`

## Release Notes Checklist

Release notes should call out:

- User-facing features.
- API or OpenAPI contract changes.
- Database migrations and upgrade notes.
- Configuration changes, especially new required environment variables.
- Security-relevant changes and secret rotation requirements.
- Known limitations, including provider-specific compatibility notes.

## After Tagging

1. Verify the CI workflow passed on the release commit.
2. Build and publish artifacts from the tagged commit only.
3. Keep `CHANGELOG.md` ready for the next cycle by adding a fresh `[Unreleased]` section when needed.
