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
JIANDOU_EXECUTION_MODE="${JIANDOU_EXECUTION_MODE:-queue}"

API_PID=""
WORKER_PID=""
WEB_PID=""

cleanup() {
  trap - EXIT INT TERM

  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi

  if [[ -n "${WORKER_PID}" ]] && kill -0 "${WORKER_PID}" 2>/dev/null; then
    kill "${WORKER_PID}" 2>/dev/null || true
  fi

  if [[ -n "${WEB_PID}" ]] && kill -0 "${WEB_PID}" 2>/dev/null; then
    kill "${WEB_PID}" 2>/dev/null || true
  fi

  wait "${API_PID}" 2>/dev/null || true
  wait "${WORKER_PID}" 2>/dev/null || true
  wait "${WEB_PID}" 2>/dev/null || true
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "缺少命令: $1"
    exit 1
  fi
}

collect_listen_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -lptn "sport = :${port}" 2>/dev/null | awk -F'pid=' 'NR>1 && NF>1 {split($2,a,","); print a[1]}' || true
    return
  fi
}

stop_service_if_running() {
  local service_name="$1"
  local port="$2"
  local pids=""
  pids="$(collect_listen_pids "$port" | tr '\n' ' ')"

  if [[ -z "${pids// }" ]]; then
    return
  fi

  echo "检测到 ${service_name} 端口 ${port} 已被占用，尝试关闭旧进程: ${pids}"
  for pid in $pids; do
    if [[ "$pid" != "$$" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  sleep 1

  for pid in $pids; do
    if [[ "$pid" != "$$" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "进程 ${pid} 未退出，发送 SIGKILL"
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

if [[ ! -d "$API_DIR" || ! -d "$WEB_DIR" ]]; then
  echo "请在项目根目录下运行此脚本。"
  exit 1
fi

require_command npm

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "未找到 Python 虚拟环境: $VENV_PYTHON"
  echo "请先创建并安装依赖，例如: python3 -m venv .venv && .venv/bin/pip install -e packages/shared -e packages/db -e packages/storage -e packages/media -e packages/ai -e packages/pipeline -e packages/backend_core -e apps/api -e apps/worker"
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "未找到前端依赖，请先执行: npm --prefix apps/web install"
  exit 1
fi

stop_service_if_running "后端" "$API_PORT"
stop_service_if_running "前端" "$WEB_PORT"
if command -v pgrep >/dev/null 2>&1; then
  EXISTING_WORKER_PIDS="$(pgrep -f "$VENV_PYTHON -m app.main" || true)"
  if [[ -n "${EXISTING_WORKER_PIDS// }" ]]; then
    echo "检测到 worker 旧进程，尝试关闭: ${EXISTING_WORKER_PIDS//$'\n'/ }"
    while read -r pid; do
      [[ -z "$pid" ]] && continue
      if [[ "$pid" != "$$" ]] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
      fi
    done <<< "$EXISTING_WORKER_PIDS"
  fi
fi

trap cleanup EXIT INT TERM

echo "启动后端: http://127.0.0.1:${API_PORT}"
(
  cd "$API_DIR"
  exec env JIANDOU_EXECUTION_MODE="$JIANDOU_EXECUTION_MODE" "$VENV_PYTHON" -m uvicorn app.main:app \
    --reload \
    --reload-dir "$ROOT_DIR/apps/api" \
    --reload-dir "$ROOT_DIR/packages" \
    --reload-dir "$ROOT_DIR/config" \
    --host "$API_HOST" \
    --port "$API_PORT"
) &
API_PID=$!

echo "启动 worker: queue consumer"
(
  cd "$ROOT_DIR/apps/worker"
  exec env JIANDOU_EXECUTION_MODE="$JIANDOU_EXECUTION_MODE" "$VENV_PYTHON" -m app.main
) &
WORKER_PID=$!

echo "启动前端: http://localhost:${WEB_PORT}"
(
  cd "$ROOT_DIR"
  exec npm --prefix apps/web run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
WEB_PID=$!

echo "API / worker / web 已启动，按 Ctrl+C 可同时停止。"

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "后端进程已退出。"
    exit 1
  fi

  if ! kill -0 "$WORKER_PID" 2>/dev/null; then
    echo "worker 进程已退出。"
    exit 1
  fi

  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "前端进程已退出。"
    exit 1
  fi

  sleep 1
done
