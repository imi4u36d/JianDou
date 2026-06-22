#!/bin/sh
# Docker entrypoint for JianDou.
# Handles auto-migration, seeding, and default server launch.
set -eu

# ── Auto-migrate (stamp-aware, handled by jiandou CLI) ──────────────────────
if [ "${JIANDOU_AUTO_MIGRATE:-true}" = "true" ]; then
  jiandou db migrate
  jiandou seed
fi

# ── Default command: start the backend server ────────────────────────────────
if [ "$#" -eq 0 ]; then
  set -- jiandou serve \
    --host "${JIANDOU_SERVER_ADDRESS:-0.0.0.0}" \
    --port "${JIANDOU_SERVER_PORT:-8000}"
fi

exec "$@"
