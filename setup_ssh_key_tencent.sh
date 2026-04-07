#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-193.112.168.154}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_PORT="${REMOTE_PORT:-22}"
KEY_PATH="${KEY_PATH:-$HOME/.ssh/id_ed25519}"
PUB_PATH="${PUB_PATH:-${KEY_PATH}.pub}"

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令: $cmd"
    exit 1
  fi
}

need_cmd ssh
need_cmd ssh-copy-id
need_cmd ssh-keygen

if [[ ! -f "$KEY_PATH" || ! -f "$PUB_PATH" ]]; then
  echo "[INFO] 未检测到密钥，正在生成: $KEY_PATH"
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
  ssh-keygen -t ed25519 -N "" -f "$KEY_PATH" -C "$(whoami)@$(hostname)-$(date +%Y%m%d)"
fi

echo "[INFO] 即将把公钥安装到 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PORT}"
echo "[INFO] 需要输入一次服务器登录密码"
ssh-copy-id -i "$PUB_PATH" -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}"

echo "[INFO] 校验免密登录..."
ssh -o BatchMode=yes -o ConnectTimeout=8 -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_HOST}" 'echo SSH_KEY_OK'

echo "[SUCCESS] 公钥已安装，后续可免密连接 ${REMOTE_USER}@${REMOTE_HOST}"
