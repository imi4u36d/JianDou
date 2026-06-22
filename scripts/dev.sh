#!/usr/bin/env bash
# One-click local development setup for JianDou (煎豆).
# Handles environment files, dependencies, migrations, and server startup.
set -euo pipefail

cd "$(dirname "$0")/.."

info()  { printf "\033[1;34m[info]\033[0m  %s\n" "$*"; }
warn()  { printf "\033[1;33m[warn]\033[0m  %s\n" "$*"; }
err()   { printf "\033[1;31m[error]\033[0m %s\n" "$*"; exit 1; }

# ── Pre-checks ────────────────────────────────────────────────────────────────
command -v node  >/dev/null 2>&1 || err "Node.js not found. Install Node.js 20+ first."
command -v npm   >/dev/null 2>&1 || err "npm not found. It usually comes with Node.js."
command -v uv    >/dev/null 2>&1 || err "uv not found. Install it: https://docs.astral.sh/uv/"

node_ver=$(node -v | sed 's/^v//' | cut -d. -f1)
if [ "$node_ver" -lt 20 ] 2>/dev/null; then
  err "Node.js 20+ required (found $(node -v))."
fi

# ── 1. Environment files ─────────────────────────────────────────────────────
if [ ! -f .env ]; then
  info "Creating .env from .env.dev.example ..."
  cp .env.dev.example .env
else
  info ".env already exists, skipping."
fi

if [ ! -f config/model/providers.secrets.yml ]; then
  info "Creating providers.secrets.yml from template ..."
  mkdir -p config/model
  cp config/model/providers.secrets.example.yml config/model/providers.secrets.yml
  warn "Edit config/model/providers.secrets.yml to add your API keys before using model features."
else
  info "providers.secrets.yml already exists, skipping."
fi

# ── 2. Install dependencies ───────────────────────────────────────────────────
info "Installing Node.js dependencies ..."
npm install --silent

info "Installing Python dependencies ..."
uv sync --quiet

# ── 3. Database migration ─────────────────────────────────────────────────────
info "Running database migrations ..."
uv run jiandou db migrate

# ── 4. Start server ───────────────────────────────────────────────────────────
info "Starting JianDou server ..."
info "  User frontend : http://127.0.0.1:8100"
info "  Admin portal  : http://127.0.0.1:8100/admin"
info ""
uv run jiandou serve
