#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-5173}"

API_PID=""
WEB_PID=""

cleanup() {
  trap - EXIT INT TERM

  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi

  if [[ -n "${WEB_PID}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi

  wait "${API_PID}" 2>/dev/null || true
  wait "${WEB_PID}" 2>/dev/null || true
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1"
    exit 1
  fi
}

if [[ ! -d "$API_DIR" || ! -d "$WEB_DIR" ]]; then
  echo "请在项目根目录下运行此脚本。"
  exit 1
fi

require_command npm

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "未找到 Python 虚拟环境: $VENV_PYTHON"
  echo "请先创建并安装依赖，例如: python3 -m venv .venv && .venv/bin/pip install -e packages/backend_core -e apps/api -e apps/worker"
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "未找到前端依赖，请先执行: npm --prefix apps/web install"
  exit 1
fi

trap cleanup EXIT INT TERM

echo "启动后端: http://127.0.0.1:${API_PORT}"
(
  cd "$API_DIR"
  exec "$VENV_PYTHON" -m uvicorn app.main:app --reload --host "$API_HOST" --port "$API_PORT"
) &
API_PID=$!

echo "启动前端: http://localhost:${WEB_PORT}"
(
  cd "$ROOT_DIR"
  exec npm --prefix apps/web run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
WEB_PID=$!

echo "前后端已启动，按 Ctrl+C 可同时停止。"

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "后端进程已退出。"
    exit 1
  fi

  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "前端进程已退出。"
    exit 1
  fi

  sleep 1
done
