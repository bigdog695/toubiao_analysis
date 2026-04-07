#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PORT="${PORT:-8000}"
HOST="127.0.0.1"
PYTHON_BIN="${PYTHON_BIN:-python3}"
APP_LOG="${APP_LOG:-/tmp/toubiao_demo_app.log}"
TUNNEL_LOG="${TUNNEL_LOG:-/tmp/toubiao_demo_tunnel.log}"

APP_PID=""
TUNNEL_PID=""
PUBLIC_URL=""

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
    if nc -z "$HOST" "$PORT" >/dev/null 2>&1; then
      return
    fi
    sleep 0.5
  done
  echo "[ERROR] 本地服务启动失败，日志: $APP_LOG"
  tail -n 40 "$APP_LOG" || true
  exit 1
}

start_local_app() {
  echo "[INFO] 启动本地 Demo 服务 http://$HOST:$PORT"
  : > "$APP_LOG"
  "$PYTHON_BIN" -c "from smart_score_demo.app import create_app; app=create_app(); app.run(host='0.0.0.0', port=${PORT}, debug=False, use_reloader=False)" > "$APP_LOG" 2>&1 &
  APP_PID=$!
  wait_for_local_app
}

extract_public_url() {
  local line
  line="$(grep -Eo 'https://[a-zA-Z0-9.-]+\.lhr\.life|[a-zA-Z0-9.-]+\.lhr\.life|https://[a-zA-Z0-9.-]+\.localhost.run' "$TUNNEL_LOG" | head -n 1 || true)"
  if [[ -z "$line" ]]; then
    return
  fi
  if [[ "$line" =~ ^https:// ]]; then
    echo "$line"
  else
    echo "https://$line"
  fi
}

start_tunnel_localhost_run() {
  echo "[INFO] 建立临时公网隧道（localhost.run）..."
  : > "$TUNNEL_LOG"
  ssh \
    -tt \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    -R 80:"$HOST":"$PORT" \
    nokey@localhost.run > "$TUNNEL_LOG" 2>&1 &
  TUNNEL_PID=$!

  for _ in $(seq 1 60); do
    if ! kill -0 "$TUNNEL_PID" >/dev/null 2>&1; then
      echo "[ERROR] 隧道进程提前退出，日志: $TUNNEL_LOG"
      tail -n 50 "$TUNNEL_LOG" || true
      exit 1
    fi
    local_url="$(extract_public_url)"
    if [[ -n "$local_url" ]]; then
      PUBLIC_URL="$local_url"
      return
    fi
    sleep 1
  done

  echo "[ERROR] 未能获取公网 URL，日志: $TUNNEL_LOG"
  tail -n 50 "$TUNNEL_LOG" || true
  exit 1
}

need_cmd "$PYTHON_BIN"
need_cmd ssh
need_cmd nc
need_cmd grep

ensure_flask
start_local_app
start_tunnel_localhost_run
if [[ -z "$PUBLIC_URL" ]]; then
  echo "[ERROR] 隧道已启动但未解析到公网地址，日志: $TUNNEL_LOG"
  tail -n 80 "$TUNNEL_LOG" || true
  exit 1
fi

echo ""
echo "=============================================="
echo "Demo 已发布到临时公网:"
echo "$PUBLIC_URL"
echo ""
echo "本地服务日志: $APP_LOG"
echo "隧道日志: $TUNNEL_LOG"
echo "按 Ctrl+C 结束并自动清理进程。"
echo "=============================================="

wait "$TUNNEL_PID"
