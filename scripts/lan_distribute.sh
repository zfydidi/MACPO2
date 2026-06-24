#!/usr/bin/env bash
# 从 Mac 向局域网 Windows+WSL 实验机分发 MACPO2 源码包（不依赖 GitHub）。
# 依赖: sshpass（brew install hudochenkov/sshpass/sshpass）
# 用法:
#   bash scripts/lan_distribute.sh
#   bash scripts/lan_distribute.sh --host 10.21.51.48
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
ARCHIVE_NAME="MACPO2-src.tgz"
ARCHIVE_PATH="/tmp/${ARCHIVE_NAME}"
FILTER_HOST=""
if [[ "${1:-}" == "--host" ]]; then
  FILTER_HOST="${2:-}"
fi

if ! command -v sshpass >/dev/null 2>&1; then
  echo "请先安装 sshpass: brew install hudochenkov/sshpass/sshpass"
  exit 1
fi

if [[ ! -f "$HOSTS_FILE" ]]; then
  echo "缺少 $HOSTS_FILE"
  echo "请复制 scripts/lan_hosts.example.tsv 为 lan_hosts.local.tsv 并填写 IP/用户/路径"
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no)

echo "==> 打包源码（排除 output / build / 大体积归档）..."
tar -czf "$ARCHIVE_PATH" -C "$ROOT" \
  --exclude='./output' \
  --exclude='./ablation_experiments' \
  --exclude='./MACPO_original_output' \
  --exclude='./experiments' \
  --exclude='.git' \
  --exclude='**/__pycache__' \
  --exclude='**/build' \
  --exclude='*.pdf' \
  --exclude='*.zip' \
  --exclude='*.docx' \
  .
echo "    包大小: $(du -h "$ARCHIVE_PATH" | awk '{print $1}')"

win_to_scp_path() {
  echo "$1" | sed 's|\\|/|g'
}

win_to_wsl_root() {
  local win="$1"
  local explicit="${2:-}"
  if [[ -n "$explicit" ]]; then
    echo "$explicit"
    return
  fi
  local drive rest
  drive=$(echo "$win" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
  rest=$(echo "$win" | sed -E 's/^[A-Za-z]:(.*)/\1/' | sed 's|\\|/|g')
  echo "/mnt/${drive}${rest}"
}

while read_lan_host_row; do
  if [[ -n "$FILTER_HOST" && "$ip" != "$FILTER_HOST" ]]; then
    continue
  fi

  scp_win=$(win_to_scp_path "$win_path")
  wsl_root=$(win_to_wsl_root "$win_path" "${wsl_path_extra:-}")
  remote_tgz="${scp_win}/${ARCHIVE_NAME}"
  wsl_tgz="${wsl_root}/${ARCHIVE_NAME}"

  echo ""
  echo "==> [$ip] ${ssh_user} -> $win_path (WSL: $wsl_root)"
  if ! nc -z -G 3 "$ip" 22 2>/dev/null; then
    echo "    跳过: 22 端口未开"
    continue
  fi
  if ! ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
    echo "    注意: ping 不通，但 22 端口可达，继续尝试 SSH"
  fi

  sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "powershell -NoProfile -Command \"New-Item -ItemType Directory -Force -Path '${scp_win}' | Out-Null\""

  sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$ARCHIVE_PATH" "${ssh_user}@${ip}:${remote_tgz}"

  if sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "wsl.exe bash -lc \"set -e; mkdir -p '${wsl_root}'; tar xzf '${wsl_tgz}' -C '${wsl_root}'; echo UNPACK_OK\"" 2>/dev/null | grep -q UNPACK_OK; then
    echo "    完成(WSL): ${ip}"
  elif sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "powershell -NoProfile -Command \"tar -xzf '${scp_win}/${ARCHIVE_NAME}' -C '${scp_win}'; Write-Output UNPACK_OK\"" 2>/dev/null | grep -q UNPACK_OK; then
    echo "    完成(Windows tar，WSL 远程不可用): ${ip}"
    echo "    请在本机 WSL 进入 ${wsl_root} 后编译运行"
  else
    echo "    失败: ${ip} 解压未成功"
    continue
  fi
done < "$HOSTS_FILE"

echo ""
echo "全部分发结束。远程进入 WSL 项目目录后按 scripts/WSL_REMOTE_RUNBOOK.md 编译并运行。"
