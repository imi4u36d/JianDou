#!/bin/sh
# Docker entrypoint for JianDou.
# Handles auto-migration, seeding, and default server launch.
set -eu

log() {
  printf '%s\n' "$*"
}

wait_for_url() {
  label="$1"
  url="$2"
  timeout="${3:-90}"

  if [ -z "$url" ]; then
    return 0
  fi

  python - "$label" "$url" "$timeout" <<'PY'
import socket
import sys
import time
from urllib.parse import urlsplit

label, url, timeout_text = sys.argv[1], sys.argv[2], sys.argv[3]
timeout = max(1, int(timeout_text))
parsed = urlsplit(url)
scheme = parsed.scheme.split("+", 1)[0]

if scheme in {"sqlite", "aiosqlite"}:
    raise SystemExit(0)

default_ports = {
    "mysql": 3306,
    "mariadb": 3306,
    "postgresql": 5432,
    "postgres": 5432,
    "redis": 6379,
}
host = parsed.hostname
port = parsed.port or default_ports.get(scheme)

if not host or not port:
    print(f"Skipping {label} readiness wait; could not parse host/port from URL.", flush=True)
    raise SystemExit(0)

deadline = time.monotonic() + timeout
attempt = 1
while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"{label} is reachable at {host}:{port}.", flush=True)
            raise SystemExit(0)
    except OSError as exc:
        if time.monotonic() >= deadline:
            print(f"Timed out waiting for {label} at {host}:{port}: {exc}", flush=True)
            raise SystemExit(1)
        print(f"Waiting for {label} at {host}:{port} (attempt {attempt})...", flush=True)
        attempt += 1
        time.sleep(1)
PY
}

run_with_retries() {
  label="$1"
  shift
  attempts="${JIANDOU_STARTUP_RETRIES:-30}"
  delay="${JIANDOU_STARTUP_RETRY_DELAY_SECONDS:-2}"
  current=1

  while :; do
    if "$@"; then
      return 0
    fi
    if [ "$current" -ge "$attempts" ]; then
      log "$label failed after $attempts attempts."
      return 1
    fi
    log "$label failed; retrying in ${delay}s (${current}/${attempts})..."
    current=$((current + 1))
    sleep "$delay"
  done
}

# ── Dependency readiness ────────────────────────────────────────────────────
wait_for_url "database" "${JIANDOU_DATABASE_URL:-}" "${JIANDOU_STARTUP_WAIT_SECONDS:-90}"
wait_for_url "redis" "${JIANDOU_REDIS_URL:-}" "${JIANDOU_STARTUP_WAIT_SECONDS:-90}"

# ── Auto-migrate (stamp-aware, handled by jiandou CLI) ──────────────────────
if [ "${JIANDOU_AUTO_MIGRATE:-true}" = "true" ]; then
  run_with_retries "Database migration" jiandou db migrate
  run_with_retries "Database seed" jiandou seed
fi

# ── Default command: start the backend server ────────────────────────────────
if [ "$#" -eq 0 ]; then
  set -- jiandou serve \
    --host "${JIANDOU_SERVER_ADDRESS:-0.0.0.0}" \
    --port "${JIANDOU_SERVER_PORT:-8000}"
fi

exec "$@"
