#!/usr/bin/env bash
# 向 GFPDO 分机推送 run_gfpdo_single.sh（及 GFPDO_overlap.cpp 若需修复）
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
DISPATCH="$ROOT/scripts/lan_gfpdo_dispatch.tsv"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)

if ! command -v sshpass >/dev/null 2>&1; then
  echo "需要 sshpass: brew install hudochenkov/sshpass/sshpass"
  exit 1
fi

push_file() {
  local pass=$1 ssh_user=$2 ip=$3 scp_win=$4 wsl=$5 rel=$6
  local src="$ROOT/$rel"
  [[ -f "$src" ]] || { echo "缺少 $src"; return 1; }
  if sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$src" "${ssh_user}@${ip}:${scp_win}/${rel}" 2>/dev/null; then
    echo "  scp $rel"
  else
    cat "$src" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
      "wsl.exe bash -lc \"mkdir -p '${wsl}/$(dirname "$rel")' && tee '${wsl}/${rel}' > /dev/null\""
    echo "  tee $rel"
  fi
}

# 去重 IP
IPS=()
while IFS= read -r pip; do
  [[ -n "$pip" ]] && IPS+=("$pip")
done < <(grep -v '^#' "$DISPATCH" | grep -v '^$' | awk -F'\t' '{print $1}' | sort -u)

for pip in "${IPS[@]}"; do
  pushed=false
  while read_lan_host_row; do
    [[ "$ip" != "$pip" ]] && continue
    pushed=true
    scp_win=$(echo "$win_path" | sed 's|\\|/|g')
    drive=$(echo "$win_path" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
    rest=$(echo "$win_path" | sed -E 's/^[A-Za-z]:(.*)/\1/' | sed 's|\\|/|g')
    wsl="/mnt/${drive}${rest}"
    [[ -n "${wsl_path_extra:-}" ]] && wsl="$wsl_path_extra"
    echo "==> $ip ($ssh_user) $wsl"
    push_file "$pass" "$ssh_user" "$ip" "$scp_win" "$wsl" "MACPO_sourcecode/run_gfpdo_single.sh" || echo "  !! run_gfpdo_single.sh 失败"
    push_file "$pass" "$ssh_user" "$ip" "$scp_win" "$wsl" "MACPO_sourcecode/GFPDO_overlap.cpp" || echo "  !! GFPDO_overlap.cpp 失败"
    break
  done < "$HOSTS_FILE"
  [[ "$pushed" == true ]] || echo "!! 未在 lan_hosts.local.tsv 找到 $pip"
done
echo "推送完成。各机 WSL 按 scripts/lan_gfpdo_manual_run.txt 编译并运行。"
