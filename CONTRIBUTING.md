# Contributing to JianDou

Thanks for helping improve JianDou. This project is still young, so small, focused pull requests are easier to review than broad rewrites.

## Local Setup

```bash
cp .env.dev.example .env
cp .env.docker.example .env.docker
cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml

npm install
uv sync
```

Model API keys are optional for backend tests, but real generation providers need values in `config/model/providers.secrets.yml`.

## Common Commands

```bash
# Run backend lint and tests
npm test

# Lint backend
npm run api:lint

# Run only backend tests
npm run api:test

# Run only frontend tests
npm run web:test

# Apply database migrations
uv run jiandou db migrate

# Verify migrations against a fresh temporary SQLite database
TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && \
  JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && \
  rm -f "$TMP_DB"

# Start the full local server
npm run serve

# Start only the API server
npm run api:dev

# Start only the frontend dev server
npm run web:dev

# Build the web app
npm run web:build

# Export the OpenAPI schema for local review or client generation
npm run api:openapi

# Run the release preflight locally
npm run release:check
```

## Backend Guidelines

- Keep routers thin: parse HTTP input, call application services, and map exceptions to HTTP responses.
- Put business rules in `backend/domain` or `backend/services`, not directly in routers.
- Keep provider-specific API details behind service/provider classes so tests can replace them.
- Use [docs/backend-architecture.md](docs/backend-architecture.md) for backend module ownership and change boundaries.
- Avoid committing local secrets, generated media, database files, or built SPA assets.
- Keep generated SPA files out of commits: `static/web/assets/` and `static/web/index.html` are rebuilt by `npm run web:build`; checked-in files under `static/web/brand/` are source assets.
- Repository hygiene tests intentionally fail when local secrets, database files, or generated build outputs are tracked.
- Prefer `uv` for Python dependency, test, and script commands.
- For release-facing changes, update `CHANGELOG.md` and follow [docs/release-process.md](docs/release-process.md).
- Keep `.github/CODEOWNERS` current when module ownership changes.
- Dependabot opens weekly dependency update pull requests for Python, npm workspaces, and GitHub Actions; review them like normal code changes and run the relevant gates before merging.

## Frontend Guidelines

- Read [docs/frontend-architecture.md](docs/frontend-architecture.md) before making frontend changes to understand the monorepo layout, component layering, and state management conventions.
- Keep the admin portal code under `frontends/web/src/admin/` behind its lazy-loading boundary so it doesn't bloat the user-facing bundle.
- Put pure logic in `utils/` or `composables/` rather than duplicating it inline inside components.
- Use TypeScript types from `src/types/index.ts` for API responses; add new interfaces there rather than using inline type assertions.
- Style components with `<style scoped>` blocks and Tailwind utility classes. Avoid global style overrides unless necessary for layout or theming.
- Run `npm run web:typecheck` and `npm run web:lint` before committing.

## Pull Request Checklist

- Backend lint and tests pass with `npm test`.
- Frontend typecheck passes with `npm run web:typecheck`.
- Frontend lint passes with `npm run web:lint`.
- Frontend tests pass with `npm run web:test`.
- Database migrations apply cleanly to a fresh database.
- Frontend/package type checks pass with `npm run packages:typecheck` and `npm run web:typecheck`.
- Release preflight passes with `npm run release:check` for release-facing changes.
- Release-facing changes update `CHANGELOG.md`.
- New behavior has focused tests where practical.
- Configuration changes are reflected in `.env.*.example` and README when they affect setup.
- Security-sensitive changes avoid unsafe production defaults.
