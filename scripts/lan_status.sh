#!/usr/bin/env bash
# 从 Mac 查看局域网实验机进度（需 lan_hosts.local.tsv + sshpass）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
PLAN="$ROOT/scripts/lan_dispatch_plan.tsv"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "请先安装 sshpass: brew install hudochenkov/sshpass/sshpass"
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)

win_to_wsl_root() {
  local win="$1" explicit="${2:-}"
  if [[ -n "$explicit" ]]; then echo "$explicit"; return; fi
  local drive rest
  drive=$(echo "$win" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
  rest=$(echo "$win" | sed -E 's/^[A-Za-z]:(.*)/\1/' | sed 's|\\|/|g')
  echo "/mnt/${drive}${rest}"
}

wsl_run() {
  local pass=$1 ssh_user=$2 ip=$3
  shift 3
  sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "wsl.exe bash -lc $(printf '%q' "$*")" 2>&1 | grep -vE 'WARNING|post-quantum|store now|pq.html' || true
}

echo "======== 通信率 F13–F18 ========"
while IFS=$'\t' read -r pip kind func; do
  [[ -z "${pip:-}" || "$pip" =~ ^# ]] && continue
  [[ "$kind" != comm ]] && continue
  while read_lan_host_row; do
    [[ "$ip" != "$pip" ]] && continue
    wsl_root=$(win_to_wsl_root "$win_path" "${wsl_path_extra:-}")
    line=$(wsl_run "$pass" "$ssh_user" "$ip" \
      "cd ${wsl_root} && n=\$(find ablation_experiments/results/comm_rate_f1_f18/F7_F18/${func} -name '*_final_comm_*.txt' 2>/dev/null | wc -l); m=\$(pgrep -c mpirun 2>/dev/null || echo 0); t=\$(grep -E 'done |FAILED|SKIP|^\\[' logs/comm_${func}*.log 2>/dev/null | tail -1); echo \"\${n}/25 mpirun=\${m} \${t}\"")
    printf "%-16s %-4s  %s\n" "$pip" "$func" "$(echo "$line" | tail -1 | tr -d '\r')"
    break
  done < "$HOSTS_FILE"
done < "$PLAN"

echo ""
echo "======== 基线 DPSO / GFPDO ========"
while IFS=$'\t' read -r pip kind _; do
  [[ -z "${pip:-}" || "$pip" =~ ^# ]] && continue
  [[ "$kind" != baselines_* ]] && continue
  while read_lan_host_row; do
    [[ "$ip" != "$pip" ]] && continue
    wsl_root=$(win_to_wsl_root "$win_path" "${wsl_path_extra:-}")
    if [[ "$kind" == baselines_dpso ]]; then
      line=$(wsl_run "$pass" "$ssh_user" "$ip" \
        "cd ${wsl_root} && grep -E 'Batch complete|^\\[60/' logs/dpso_mac_ssh.log 2>/dev/null | tail -1; find MACPO_sourcecode/output_baselines_dpso_5runs -name '*.txt' 2>/dev/null | wc -l | xargs echo -n files:")
      label="DPSO"
    else
      line=$(wsl_run "$pass" "$ssh_user" "$ip" \
        "cd ${wsl_root} && grep -E '^\[|final fitness|Batch complete' logs/gfpdo_1run.log logs/gfpdo_mac_ssh.log 2>/dev/null | tail -2; find MACPO_sourcecode/output_baselines_gfpdo_1run MACPO_sourcecode/output_baselines_gfpdo_5runs -name '*.txt' 2>/dev/null | wc -l | xargs echo -n files:")
      label="GFPDO"
    fi
    printf "%-16s %-5s %s\n" "$pip" "$label" "$(echo "$line" | tr '\n' ' ' | sed 's/  */ /g')"
    break
  done < "$HOSTS_FILE"
done < "$PLAN"

echo ""
echo "Mac 长连接: ps aux | grep '10.21.51.2[57]' | grep -v grep"
