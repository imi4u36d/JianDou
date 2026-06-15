#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
用法:
  bash scripts/compose-stack.sh <up|down|logs|ps|build|restart|pull|config> [service...]

示例:
  bash scripts/compose-stack.sh up
  bash scripts/compose-stack.sh logs app
  bash scripts/compose-stack.sh down
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1"
    exit 1
  fi
}

require_compose() {
  require_command docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "当前环境未安装 Docker Compose Plugin，无法执行 docker compose"
    exit 1
  fi
}

ensure_local_dirs() {
  mkdir -p \
    "$ROOT_DIR/storage/uploads" \
    "$ROOT_DIR/storage/outputs" \
    "$ROOT_DIR/storage/temp"
}

ACTION="${1:-up}"
shift || true

require_compose
ensure_local_dirs

COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-jiandou}"
COMPOSE_ARGS=(-p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE")

compose() {
  (
    cd "$ROOT_DIR"
    docker compose "${COMPOSE_ARGS[@]}" "$@"
  )
}

case "$ACTION" in
  up)
    compose up -d --no-build "$@"
    echo "容器已启动:"
    echo "  App: http://127.0.0.1:80"
    ;;
  down)
    compose down "$@"
    ;;
  logs)
    compose logs -f --tail=200 "$@"
    ;;
  ps)
    compose ps
    ;;
  build)
    compose build "$@"
    ;;
  restart)
    if [[ "$#" -eq 0 ]]; then
      compose restart
    else
      compose restart "$@"
    fi
    ;;
  pull)
    compose pull "$@"
    ;;
  config)
    compose config
    ;;
  *)
    echo "不支持的动作: $ACTION"
    usage
    exit 1
    ;;
esac
