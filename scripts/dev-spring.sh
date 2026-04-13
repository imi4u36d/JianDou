#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
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

collect_listen_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
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
}

require_command npm
require_command mvn

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "未找到前端依赖，请先执行: npm --prefix apps/web install"
  exit 1
fi

stop_service_if_running "后端" "$API_PORT"
stop_service_if_running "前端" "$WEB_PORT"

trap cleanup EXIT INT TERM

echo "启动 Spring Boot 后端: http://127.0.0.1:${API_PORT}"
(
  cd "$ROOT_DIR/apps/api-spring"
  exec env SERVER_PORT="$API_PORT" mvn spring-boot:run
) &
API_PID=$!

echo "启动前端: http://localhost:${WEB_PORT}"
(
  cd "$ROOT_DIR"
  exec npm --prefix apps/web run dev -- --host "$WEB_HOST" --port "$WEB_PORT"
) &
WEB_PID=$!

echo "Spring API / web 已启动，按 Ctrl+C 可同时停止。"

while true; do
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "Spring 后端进程已退出。"
    exit 1
  fi

  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "前端进程已退出。"
    exit 1
  fi

  sleep 1
done
