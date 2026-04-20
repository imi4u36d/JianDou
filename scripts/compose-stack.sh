#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
用法:
  bash scripts/compose-stack.sh <dev|prod> <up|down|logs|ps|build|restart|pull|config> [service...]

示例:
  bash scripts/compose-stack.sh dev up
  bash scripts/compose-stack.sh dev logs api
  bash scripts/compose-stack.sh prod up
  bash scripts/compose-stack.sh prod down
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

warn_missing_dev_config() {
  if [[ ! -d "$ROOT_DIR/config/app" ]]; then
    echo "提示: 未找到 config/app 目录，请检查本地配置是否完整。"
  fi
}

ensure_dev_env() {
  if [[ ! -f "$ROOT_DIR/.env.dev" ]]; then
    echo "缺少 .env.dev，请先执行:"
    echo "  cp .env.dev.example .env.dev"
    exit 1
  fi
}

ensure_prod_env() {
  if [[ ! -f "$ROOT_DIR/.env.prod" ]]; then
    echo "缺少 .env.prod，请先执行:"
    echo "  cp .env.prod.example .env.prod"
    exit 1
  fi
}

MODE="${1:-}"
ACTION="${2:-up}"

if [[ -z "$MODE" ]]; then
  usage
  exit 1
fi

shift 2 || true

require_compose
ensure_local_dirs

case "$MODE" in
  dev)
    COMPOSE_FILE="$ROOT_DIR/docker-compose.dev.yml"
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-jiandou-dev}"
    ensure_dev_env
    COMPOSE_ARGS=(--env-file "$ROOT_DIR/.env.dev" -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE")
    PUBLIC_WEB_URL="http://127.0.0.1"
    PUBLIC_ADMIN_URL="http://127.0.0.1:5174"
    PUBLIC_API_URL="http://127.0.0.1/api/v2"
    warn_missing_dev_config
    ;;
  prod)
    COMPOSE_FILE="$ROOT_DIR/docker-compose.prod.yml"
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-jiandou-prod}"
    ensure_prod_env
    COMPOSE_ARGS=(--env-file "$ROOT_DIR/.env.prod" -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE")
    PUBLIC_WEB_URL="http://127.0.0.1"
    PUBLIC_ADMIN_URL="http://127.0.0.1:5174"
    PUBLIC_API_URL="http://127.0.0.1/api/v2"
    ;;
  *)
    echo "不支持的模式: $MODE"
    usage
    exit 1
    ;;
esac

compose() {
  (
    cd "$ROOT_DIR"
    docker compose "${COMPOSE_ARGS[@]}" "$@"
  )
}

case "$ACTION" in
  up)
    compose up -d --build "$@"
    echo "$MODE 容器已启动:"
    echo "  Web:   $PUBLIC_WEB_URL"
    echo "  Admin: $PUBLIC_ADMIN_URL"
    echo "  API:   $PUBLIC_API_URL"
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
