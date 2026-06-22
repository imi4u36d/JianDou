#!/usr/bin/env bash
# One-command startup for JianDou in production / end-user mode.
# Builds the frontend, runs migrations, seeds the database, and starts
# the FastAPI server serving the compiled SPA.
#
# Usage:  bash scripts/start.sh
#
# Prerequisites: Node.js 20+, npm, uv
set -euo pipefail

cd "$(dirname "$0")/.."

info() { printf "\033[1;34m[info]\033[0m  %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[error]\033[0m %s\n" "$*"; exit 1; }

# ── Pre-checks ──────────────────────────────────────────────────────────────
command -v node >/dev/null 2>&1 || err "Node.js not found. Install Node.js 20+ first."
command -v npm  >/dev/null 2>&1 || err "npm not found. It usually comes with Node.js."
command -v uv   >/dev/null 2>&1 || err "uv not found. Install it: https://docs.astral.sh/uv/"

node_ver=$(node -v | sed 's/^v//' | cut -d. -f1)
if [ "$node_ver" -lt 20 ] 2>/dev/null; then
  err "Node.js 20+ required (found $(node -v))."
fi

# ── 1. Environment files ────────────────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.prod.example ]; then
    info "Creating .env from .env.prod.example ..."
    cp .env.prod.example .env
    warn "Review .env and set production values before first use."
  elif [ -f .env.example ]; then
    info "Creating .env from .env.example ..."
    cp .env.example .env
    warn "Review .env and set production values before first use."
  fi
fi

if [ ! -f config/model/providers.secrets.yml ]; then
  mkdir -p config/model
  cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
  warn "Edit config/model/providers.secrets.yml to add your API keys."
fi

# ── 2. Install dependencies ─────────────────────────────────────────────────
info "Installing Node.js dependencies ..."
npm install --silent

info "Installing Python dependencies ..."
uv sync --quiet

# ── 3. Build frontend ───────────────────────────────────────────────────────
info "Building frontend ..."
npm run web:build

# ── 4. Database migration + seed ────────────────────────────────────────────
info "Running database migrations ..."
uv run jiandou db migrate

info "Seeding database ..."
uv run jiandou seed

# ── 5. Start server ─────────────────────────────────────────────────────────
info "Starting JianDou server ..."
info "  App  : http://127.0.0.1:8100"
info "  Admin: http://127.0.0.1:8100/admin"
info ""
exec uv run jiandou serve
