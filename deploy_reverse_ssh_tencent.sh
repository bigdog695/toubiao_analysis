#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# ===== 可配置参数（可用环境变量覆盖） =====
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOCAL_HOST="${LOCAL_HOST:-127.0.0.1}"
LOCAL_PORT="${LOCAL_PORT:-8000}"
REMOTE_HOST="${REMOTE_HOST:-193.112.168.154}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_SSH_PORT="${REMOTE_SSH_PORT:-22}"
REMOTE_BIND_HOST="${REMOTE_BIND_HOST:-0.0.0.0}"
REMOTE_BIND_PORT="${REMOTE_BIND_PORT:-18080}"
SSH_KEY_PATH="${SSH_KEY_PATH:-}"
START_LOCAL_APP="${START_LOCAL_APP:-1}"

APP_LOG="${APP_LOG:-/tmp/toubiao_demo_app.log}"
TUNNEL_LOG="${TUNNEL_LOG:-/tmp/toubiao_demo_reverse_ssh.log}"

APP_PID=""
TUNNEL_PID=""

cleanup() {
  local exit_code=$?
  if [[ -n "${TUNNEL_PID}" ]] && kill -0 "${TUNNEL_PID}" >/dev/null 2>&1; then
    kill "${TUNNEL_PID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${APP_PID}" ]] && kill -0 "${APP_PID}" >/dev/null 2>&1; then
    kill "${APP_PID}" >/dev/null 2>&1 || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令: $cmd"
    exit 1
  fi
}

ensure_flask() {
  if "$PYTHON_BIN" -c 'import flask' >/dev/null 2>&1; then
    return
  fi
  echo "[INFO] Flask 未安装，正在安装..."
  "$PYTHON_BIN" -m pip install 'Flask>=3.0.0'
}

wait_for_local_app() {
  for _ in $(seq 1 40); do
    if nc -z "$LOCAL_HOST" "$LOCAL_PORT" >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done
  echo "[ERROR] 本地服务启动失败，日志: $APP_LOG"
  tail -n 40 "$APP_LOG" || true
  exit 1
}

start_local_app() {
  echo "[INFO] 启动本地 Demo 服务 http://$LOCAL_HOST:$LOCAL_PORT"
  : > "$APP_LOG"
  "$PYTHON_BIN" -c "from smart_score_demo.app import create_app; app=create_app(); app.run(host='0.0.0.0', port=${LOCAL_PORT}, debug=False, use_reloader=False)" > "$APP_LOG" 2>&1 &
  APP_PID=$!
  wait_for_local_app
}

build_ssh_cmd() {
  local -a cmd=(
    ssh
    -N
    -T
    -p "$REMOTE_SSH_PORT"
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o ExitOnForwardFailure=yes
    -o StrictHostKeyChecking=accept-new
    -R "${REMOTE_BIND_HOST}:${REMOTE_BIND_PORT}:${LOCAL_HOST}:${LOCAL_PORT}"
  )

  if [[ -n "$SSH_KEY_PATH" ]]; then
    cmd+=( -i "$SSH_KEY_PATH" )
  fi

  cmd+=( "${REMOTE_USER}@${REMOTE_HOST}" )
  printf '%q ' "${cmd[@]}"
}

start_reverse_ssh() {
  local ssh_cmd
  ssh_cmd="$(build_ssh_cmd)"

  echo "[INFO] 建立 SSH 反向隧道到 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_SSH_PORT}"
  echo "[INFO] 映射关系: ${REMOTE_BIND_HOST}:${REMOTE_BIND_PORT} -> ${LOCAL_HOST}:${LOCAL_PORT}"

  : > "$TUNNEL_LOG"
  # shellcheck disable=SC2086
  eval "$ssh_cmd" > "$TUNNEL_LOG" 2>&1 &
  TUNNEL_PID=$!

  sleep 2
  if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
    echo "[ERROR] SSH 隧道建立失败，日志: $TUNNEL_LOG"
    tail -n 80 "$TUNNEL_LOG" || true
    exit 1
  fi
}

need_cmd "$PYTHON_BIN"
need_cmd ssh
need_cmd nc

if [[ "$START_LOCAL_APP" == "1" ]]; then
  ensure_flask
  start_local_app
else
  wait_for_local_app
fi

start_reverse_ssh

PUBLIC_URL="http://${REMOTE_HOST}:${REMOTE_BIND_PORT}/"

echo ""
echo "==========================================================="
echo "腾讯云反向隧道已建立"
echo "公网访问地址: $PUBLIC_URL"
echo ""
echo "本地服务日志: $APP_LOG"
echo "隧道日志: $TUNNEL_LOG"
echo "按 Ctrl+C 结束并自动清理进程。"
echo "==========================================================="

wait "$TUNNEL_PID"
