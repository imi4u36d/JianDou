#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
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

display_host() {
  local host="$1"
  if [[ "$host" == "0.0.0.0" ]]; then
    echo "127.0.0.1"
    return
  fi
  echo "$host"
}

collect_listen_pids() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
  fi
}

collect_managed_parent_pids() {
  local pid="$1"
  shift
  local current="$pid"

  while true; do
    local parent=""
    parent="$(ps -o ppid= -p "$current" 2>/dev/null | tr -d ' ')"
    if [[ -z "$parent" || "$parent" -le 1 || "$parent" == "$$" ]]; then
      break
    fi

    local command_line=""
    command_line="$(ps -o command= -p "$parent" 2>/dev/null || true)"
    if [[ -z "$command_line" ]]; then
      break
    fi

    local matched="false"
    local pattern=""
    for pattern in "$@"; do
      if [[ "$command_line" == *"$pattern"* ]]; then
        matched="true"
        break
      fi
    done

    if [[ "$matched" != "true" ]]; then
      break
    fi

    echo "$parent"
    current="$parent"
  done
}

terminate_pids() {
  local pids=("$@")
  local pid=""

  for pid in "${pids[@]}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  local deadline=$((SECONDS + 8))
  while (( SECONDS < deadline )); do
    local remaining="false"
    for pid in "${pids[@]}"; do
      if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        remaining="true"
        break
      fi
    done
    if [[ "$remaining" != "true" ]]; then
      return
    fi
    sleep 0.2
  done

  for pid in "${pids[@]}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  done
}

wait_for_port_release() {
  local port="$1"
  local deadline=$((SECONDS + 10))

  while (( SECONDS < deadline )); do
    if [[ -z "$(collect_listen_pids "$port")" ]]; then
      return
    fi
    sleep 0.2
  done
}

stop_service_if_running() {
  local service_name="$1"
  local port="$2"
  shift 2
  local pids=""
  pids="$(collect_listen_pids "$port" | tr '\n' ' ')"

  if [[ -z "${pids// }" ]]; then
    return
  fi

  local all_pids=()
  local pid=""
  for pid in $pids; do
    if [[ "$pid" == "$$" ]]; then
      continue
    fi
    all_pids+=("$pid")
    while IFS= read -r parent_pid; do
      [[ -n "$parent_pid" ]] && all_pids+=("$parent_pid")
    done < <(collect_managed_parent_pids "$pid" "$@")
  done

  local unique_pids=()
  local seen=""
  for pid in "${all_pids[@]}"; do
    if [[ -z "$pid" || " $seen " == *" $pid "* ]]; then
      continue
    fi
    unique_pids+=("$pid")
    seen+=" $pid"
  done

  echo "检测到 ${service_name} 端口 ${port} 已被占用，尝试关闭旧进程: ${unique_pids[*]}"
  terminate_pids "${unique_pids[@]}"
  wait_for_port_release "$port"
}

require_command npm
require_command mvn

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "未找到前端依赖，请先执行: npm --prefix apps/web install"
  exit 1
fi

stop_service_if_running "后端" "$API_PORT" "spring-boot:run" "JianDouSpringApiApplication"
stop_service_if_running "前端" "$WEB_PORT" "npm --prefix" "vite"

trap cleanup EXIT INT TERM

echo "启动 Spring Boot 后端: http://$(display_host "$API_HOST"):${API_PORT}"
(
  cd "$ROOT_DIR/apps/api-spring"
  exec env SERVER_ADDRESS="$API_HOST" SERVER_PORT="$API_PORT" mvn spring-boot:run
) &
API_PID=$!

echo "启动前端: http://$(display_host "$WEB_HOST"):${WEB_PORT}"
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
