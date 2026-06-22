<p align="center">
  <strong>English</strong> | <a href="README_zh-CN.md">简体中文</a> | <a href="README_ja-JP.md">日本語</a>
</p>

<p align="center">
  <img src="static/web/brand/logo.png" alt="JianDou Logo" width="120" />
</p>

<h1 align="center">JianDou (煎豆)</h1>

<p align="center">
  An open-source text-to-video workstation powered by a configurable multi-model pipeline.
</p>

<p align="center">
  <a href="https://github.com/imi4u36d/JianDou/blob/main/License"><img src="https://img.shields.io/badge/license-Apache--2.0-blue.svg" alt="License" /></a>
  <a href="https://github.com/imi4u36d/JianDou/releases"><img src="https://img.shields.io/badge/release-0.1.0-orange.svg" alt="Release" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/python-3.12%2B-green.svg" alt="Python" /></a>
  <a href="https://github.com/imi4u36d/JianDou"><img src="https://img.shields.io/badge/node-20%2B-brightgreen.svg" alt="Node" /></a>
</p>

---

Upload novel chapters, paste text, or enter a prompt — JianDou turns your words into video through a chain of configurable AI models (text, visual, keyframe, and video). Each stage can be independently assigned to different providers and model versions, giving you full control over the generation pipeline.

## Key Features

**Flexible Input**
- Upload `.txt` files or paste text directly — content is automatically extracted for prompt generation.
- Enter custom prompts for full creative control.
- Attach reference images as the first or last keyframe.

**Multi-Model Pipeline**
- Four independently configurable stages: Text Model (script/storyboard) → Visual Model (reference image understanding) → Keyframe Model (first/last frame generation) → Video Model (video synthesis).
- Mix and match providers: Alibaba Cloud (Qwen/Wanxiang), Volcengine (Doubao/Seedream/Seedance), and any OpenAI-compatible endpoint.
- Output parameters (aspect ratio, resolution, duration, count, seed) are dynamically filtered by the selected model's capabilities.

**Task Management**
- Real-time progress tracking with stage-level status, elapsed time, and video preview.
- Full task lifecycle: create, filter, detail view, retry, pause, resume, abort, delete, and rate.
- Seed management: automatically collect high-rated seeds and one-click backfill for consistent results.

**Admin Console**
- Dedicated admin portal separated from the user-facing frontend.
- Role-based access control (admin / user) with invite-code registration.
- Designed for content production teams and ops management.

**Security & Deployment**
- Rate limiting on auth endpoints, origin validation, encrypted API key storage.
- Docker-first deployment with automatic database migrations and health checks.
- Comprehensive configuration via environment variables and YAML files.

## Architecture

```
Text Input --> Text Model (script/storyboard generation)
                --> Visual Model (reference image understanding)
                        --> Keyframe Model (first/last frame generation)
                                --> Video Model (video synthesis)
                                        --> Preview / Download / Rate
```

Each pipeline stage is independently configurable with its own provider and model version.

## Quick Start

### Prerequisites

- **Python** 3.12+
- **Node.js** 20+
- **npm** (comes with Node.js)
- **[uv](https://docs.astral.sh/uv/)** (Python package manager)

### Option 1: Docker (Recommended)

```bash
# 1. Prepare environment
cp .env.docker.example .env.docker

# 2. Build and run
docker build -t jiandou .
docker run -d -p 8100:8000 \
  --env-file .env.docker \
  -v ./config:/app/config \
  -v ./data:/app/data \
  -v ./storage:/app/storage \
  jiandou
```

The image exposes port `8000` inside the container and runs database migrations on startup. Set `JIANDOU_AUTO_MIGRATE=false` to skip automatic migration.

### Option 2: Local Development

```bash
# 1. Environment setup
cp .env.dev.example .env
cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
# Edit providers.secrets.yml with your API keys

# 2. Install dependencies
npm install
uv sync

# 3. Apply database migrations
uv run jiandou db migrate

# 4. Start the server
npm run serve
```

After startup:
- **User Frontend**: `http://127.0.0.1:8100`
- **Admin Portal**: `http://127.0.0.1:8100/admin`

### Health Checks

- **Liveness**: `GET /api/v3/health`
- **Readiness**: `GET /api/v3/ready` (validates database and storage availability)

## Model Configuration

Model configuration lives in `config/model/`:

```
config/model/
├── models.yml                    # Available model definitions
├── providers/                    # Provider base configs (base_url, etc.)
│   ├── volcengine.yml
│   ├── deepseek.yml
│   └── openai.yml
├── providers.secrets.example.yml # API key template (committed)
└── providers.secrets.yml         # Your API keys (local, not committed)
```

Supported providers:
- **Alibaba Cloud** — Qwen (通义千问), Wanxiang (万相)
- **Volcengine** — Doubao (豆包), Seedream, Seedance
- **OpenAI-compatible** — Any OpenAI-compatible API endpoint

## Configuration

All runtime settings are controlled via environment variables. See [docs/configuration.md](docs/configuration.md) for the full reference.

Key variables:

| Variable | Description | Default |
|---|---|---|
| `JIANDOU_SERVER_PORT` | Backend listen port | `8100` |
| `JIANDOU_DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./data/jiandou.db` |
| `JIANDOU_SECRET_KEY` | JWT signing key | (must be set) |
| `JIANDOU_WEB_ORIGIN` | Frontend origin for CORS | `http://127.0.0.1:8100` |
| `JIANDOU_TRUSTED_ORIGINS` | Additional trusted origins (comma-separated) | — |
| `JIANDOU_COOKIE_SECURE` | Enable secure cookies + HSTS | `false` |
| `JIANDOU_WORKER_CONCURRENCY` | Async worker thread count | `2` |
| `JIANDOU_DEFAULT_ASPECT_RATIO` | Default video aspect ratio | `16:9` |
| `JIANDOU_DEFAULT_DURATION_SECONDS` | Default video duration | `8` |

Authentication endpoints have built-in rate limiting. Tune via `JIANDOU_AUTH_LOGIN_RATE_LIMIT`, `JIANDOU_AUTH_INVITE_ACTIVATION_RATE_LIMIT`, and `JIANDOU_AUTH_RATE_LIMIT_WINDOW_SECONDS`.

## Development

### Frontend

The frontend is built with **Vue 3 + TypeScript + Element Plus + Tailwind CSS**, using Vite as the dev server with automatic API proxying.

```bash
# Copy frontend env template
cp frontends/web/.env.example frontends/web/.env

# Dev server (default http://localhost:5173)
npm run web:dev

# Type checking
npm run web:typecheck

# Lint & format
npm run web:lint
npm run web:format

# Unit tests
npm run web:test

# Test coverage
npx vitest run --coverage
```

See [docs/frontend-architecture.md](docs/frontend-architecture.md) for the monorepo layout and component conventions.

### Backend

The backend is built with **FastAPI + SQLAlchemy + Alembic**, using SQLite via aiosqlite.

```bash
# Lint (ruff, zero errors expected)
uv run ruff check backend/

# Run all tests (314 tests, zero failures expected)
uv run pytest

# Run by test category
uv run pytest -m unit      # Fast unit tests (64)
uv run pytest -m api       # API endpoint tests (90)
uv run pytest -m domain    # Domain layer tests (33)
uv run pytest -m "not slow" # Skip slow tests

# Export OpenAPI schema
uv run jiandou openapi --output docs/openapi.json

# API-only dev server
npm run api:dev
```

See [docs/backend-architecture.md](docs/backend-architecture.md) for module ownership and [docs/database-design.md](docs/database-design.md) for schema constraints.

### Verification

```bash
# Full test suite (backend lint + tests + frontend typecheck)
npm test

# Verify migrations against a fresh temporary database
TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && \
  JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && \
  rm -f "$TMP_DB"

# Package type checks
npm run packages:typecheck
npm run web:typecheck

# Release preflight (cleans generated artifacts)
npm run release:check
```

## Documentation

| Document | Description |
|---|---|
| [Configuration](docs/configuration.md) | Full environment variable reference |
| [Backend Architecture](docs/backend-architecture.md) | Module ownership and change boundaries |
| [Frontend Architecture](docs/frontend-architecture.md) | Monorepo layout and component conventions |
| [Database Design](docs/database-design.md) | Schema constraints and migration rules |
| [Release Process](docs/release-process.md) | Versioning and release workflow |
| [API Reference](docs/openapi.json) | OpenAPI 3.1 specification (generated) |

## Community & Support

- **QQ Group**: `1090387362`
- [Report a Bug / Request a Feature](https://github.com/imi4u36d/JianDou/issues)
- For security issues, see [SECURITY.md](SECURITY.md)
- For usage questions and contribution guidelines, see [SUPPORT.md](SUPPORT.md) and [CONTRIBUTING.md](CONTRIBUTING.md)

## Star History

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
  </picture>
</a>

## License

This project is licensed under the [Apache License 2.0](./License).
