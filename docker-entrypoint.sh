#!/bin/sh
set -eu

if [ "${JIANDOU_AUTO_MIGRATE:-true}" = "true" ]; then
  jiandou db migrate
fi

if [ "$#" -eq 0 ]; then
  set -- uvicorn backend.main:app
fi

if [ "$1" = "uvicorn" ]; then
  set -- "$@" \
    --host "${JIANDOU_SERVER_ADDRESS:-0.0.0.0}" \
    --port "${JIANDOU_SERVER_PORT:-8000}"
fi

exec "$@"
