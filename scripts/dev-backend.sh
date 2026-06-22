#!/usr/bin/env bash
# Start the JianDou backend in development mode with hot-reload.
# Usage:  bash scripts/dev-backend.sh
#
# Prerequisites: uv  (https://docs.astral.sh/uv/)
#
# The Vite frontend dev server can be started separately:
#   bash scripts/dev-frontend.sh
set -euo pipefail

cd "$(dirname "$0")/.."

info() { printf "\033[1;34m[info]\033[0m  %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[error]\033[0m %s\n" "$*"; exit 1; }

# ── Pre-checks ──────────────────────────────────────────────────────────────
command -v uv >/dev/null 2>&1 || err "uv not found. Install it: https://docs.astral.sh/uv/"

# ── 1. Environment files ────────────────────────────────────────────────────
if [ ! -f .env ]; then
  info "Creating .env from .env.dev.example ..."
  cp .env.dev.example .env
fi

if [ ! -f config/model/providers.secrets.yml ]; then
  mkdir -p config/model
  cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
  warn "Edit config/model/providers.secrets.yml to add your API keys."
fi

# ── 2. Install Python dependencies ──────────────────────────────────────────
info "Installing Python dependencies ..."
uv sync --quiet

# ── 3. Database migration (stamp-aware) ─────────────────────────────────────
info "Running database migrations ..."
uv run jiandou db migrate

# ── 4. Start backend with hot-reload ────────────────────────────────────────
info "Starting backend on http://127.0.0.1:8100  (--reload enabled)"
info "  API docs : http://127.0.0.1:8100/docs"
info ""
exec uv run jiandou serve --reload
