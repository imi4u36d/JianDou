#!/usr/bin/env bash
# Start the JianDou frontend Vite dev server with HMR.
# Usage:  bash scripts/dev-frontend.sh
#
# Prerequisites: Node.js 20+, npm
#
# The Vite dev server runs on http://localhost:5173 and proxies
# API requests to the backend (default http://127.0.0.1:8100).
# Start the backend first or in a separate terminal:
#   bash scripts/dev-backend.sh
set -euo pipefail

cd "$(dirname "$0")/.."

info() { printf "\033[1;34m[info]\033[0m  %s\n" "$*"; }
err()  { printf "\033[1;31m[error]\033[0m %s\n" "$*"; exit 1; }

# ── Pre-checks ──────────────────────────────────────────────────────────────
command -v node >/dev/null 2>&1 || err "Node.js not found. Install Node.js 20+ first."
command -v npm  >/dev/null 2>&1 || err "npm not found. It usually comes with Node.js."

node_ver=$(node -v | sed 's/^v//' | cut -d. -f1)
if [ "$node_ver" -lt 20 ] 2>/dev/null; then
  err "Node.js 20+ required (found $(node -v))."
fi

# ── 1. Install Node.js dependencies ─────────────────────────────────────────
info "Installing Node.js dependencies ..."
npm install --silent

# ── 2. Start Vite dev server ────────────────────────────────────────────────
info "Starting Vite dev server on http://localhost:5173"
info "  Proxy target: ${VITE_API_PROXY_TARGET:-http://127.0.0.1:8100}"
info ""
exec npm run dev
