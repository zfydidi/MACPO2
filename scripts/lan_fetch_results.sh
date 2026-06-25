#!/usr/bin/env bash
# 从局域网实验机拉回结果到本机。
# 用法:
#   bash scripts/lan_fetch_results.sh --all          # 按 lan_dispatch_plan.tsv 从各机拉对应函数
#   bash scripts/lan_fetch_results.sh --host 10.21.51.48
#   bash scripts/lan_fetch_results.sh --baselines    # 拉 GFPDO/DPSO 基线输出
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
PLAN="$ROOT/scripts/lan_dispatch_plan.tsv"
LOCAL_COMM="$ROOT/ablation_experiments/results/comm_rate_f1_f18/F7_F18"
FILTER_HOST=""
FETCH_ALL=false
FETCH_BASELINES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) FILTER_HOST="${2:-}"; shift 2 ;;
    --all) FETCH_ALL=true; shift ;;
    --baselines) FETCH_BASELINES=true; shift ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if ! command -v sshpass >/dev/null 2>&1; then
  echo "请先安装 sshpass"
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no)

win_to_wsl_root() {
  local win="$1" explicit="${2:-}"
  if [[ -n "$explicit" ]]; then echo "$explicit"; return; fi
  local drive rest
  drive=$(echo "$win" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
  rest=$(echo "$win" | sed -E 's/^[A-Za-z]:(.*)/\1/' | sed 's|\\|/|g')
  echo "/mnt/${drive}${rest}"
}

lookup_host() {
  local want_ip="$1"
  while read_lan_host_row; do
    if [[ "$ip" == "$want_ip" ]]; then
      echo "$ip	$user	$pass	$win_path	$wsl_path_extra	$ssh_user"
      return 0
    fi
  done < "$HOSTS_FILE"
  return 1
}

fetch_comm_func() {
  local ip="$1" pass="$2" win_path="$3" func="$4"
  local wsl_root
  wsl_root=$(win_to_wsl_root "$win_path" "")
  local rel="ablation_experiments/results/comm_rate_f1_f18/F7_F18/${func}"
  local drive
  drive=$(echo "$win_path" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
  local tgz_name="macpo_${func}_${ip}.tgz"
  local scp_tgz
  scp_tgz=$(echo "$win_path" | sed 's|\\|/|g')"/tmp/${tgz_name}"

  echo "==> [$ip] 拉取 $func"
  pack_cmd="wsl.exe bash -lc \"cd '${wsl_root}' && mkdir -p tmp && tar czf tmp/${tgz_name} '${rel}' 2>/dev/null || true\""
  sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" "$pack_cmd"
  sshpass -p "$pass" scp "${SSH_OPTS[@]}" "${ssh_user}@${ip}:${scp_tgz}" "/tmp/${tgz_name}" 2>/dev/null || {
    echo "    跳过: 无 ${func} 数据"
    return 0
  }
  mkdir -p "$LOCAL_COMM"
  tar xzf "/tmp/${tgz_name}" -C "$ROOT"
  echo "    已合并 $func"
}

fetch_baselines() {
  local ip="$1" pass="$2" win_path="$3" algo="$4"
  local wsl_root out_sub
  wsl_root=$(win_to_wsl_root "$win_path" "")
  if [[ "$algo" == "dpso" ]]; then
    out_sub="MACPO_sourcecode/output_baselines_dpso_5runs"
  else
    out_sub="MACPO_sourcecode/output_baselines_gfpdo_5runs"
  fi
  local tgz_name="macpo_${algo}_${ip}.tgz"
  local scp_tgz
  scp_tgz=$(echo "$win_path" | sed 's|\\|/|g')"/tmp/${tgz_name}"
  local local_out="$ROOT/MACPO_sourcecode/output_baselines_5runs_${algo}"

  echo "==> [$ip] 拉取 ${algo} 基线"
  pack_cmd="wsl.exe bash -lc \"cd '${wsl_root}' && mkdir -p tmp && tar czf tmp/${tgz_name} '${out_sub}' 2>/dev/null || true\""
  sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" "$pack_cmd"
  sshpass -p "$pass" scp "${SSH_OPTS[@]}" "${ssh_user}@${ip}:${scp_tgz}" "/tmp/${tgz_name}" 2>/dev/null || {
    echo "    跳过: 无 ${algo} 数据"
    return 0
  }
  mkdir -p "$local_out"
  tar xzf "/tmp/${tgz_name}" -C "$ROOT" --strip-components=2 2>/dev/null || tar xzf "/tmp/${tgz_name}" -C "$ROOT/MACPO_sourcecode"
  echo "    已保存到 MACPO_sourcecode/output_baselines_5runs_${algo}/"
}

mkdir -p "$LOCAL_COMM"

if [[ "$FETCH_BASELINES" == true ]]; then
  while IFS=$'\t' read -r ip kind payload; do
    [[ -z "${ip:-}" || "$ip" =~ ^# ]] && continue
    [[ "$kind" == baselines_dpso || "$kind" == baselines_gfpdo ]] || continue
    line=$(lookup_host "$ip") || continue
    IFS=$'\t' read -r hip user pass win_path hextra hssh <<< "$line"
    ssh_user="${hssh:-$user}"
    algo="${kind#baselines_}"
    fetch_baselines "$ip" "$pass" "$win_path" "$algo"
  done < <(grep -v '^#' "$PLAN" | grep -v '^$')
  echo "基线拉回完成。"
  exit 0
fi

if [[ "$FETCH_ALL" == true ]]; then
  while IFS=$'\t' read -r ip kind payload; do
    [[ -z "${ip:-}" || "$ip" =~ ^# ]] && continue
    [[ "$kind" == comm ]] || continue
    line=$(lookup_host "$ip") || continue
    IFS=$'\t' read -r hip user pass win_path hextra hssh <<< "$line"
    ssh_user="${hssh:-$user}"
    fetch_comm_func "$ip" "$pass" "$win_path" "$payload"
  done < <(grep -v '^#' "$PLAN" | grep -v '^$')
else
  if [[ -z "$FILTER_HOST" ]]; then
    echo "请指定 --all、--baselines 或 --host IP"
    exit 1
  fi
  line=$(lookup_host "$FILTER_HOST") || { echo "未在 lan_hosts.local.tsv 找到 $FILTER_HOST"; exit 1; }
  IFS=$'\t' read -r hip user pass win_path hextra hssh <<< "$line"
  ssh_user="${hssh:-$user}"
  func=""
  while IFS=$'\t' read -r pip pkind ppayload; do
    [[ "$pip" == "$FILTER_HOST" && "$pkind" == comm ]] && func="$ppayload"
  done < <(grep -v '^#' "$PLAN" | grep -v '^$')
  if [[ -n "$func" ]]; then
    fetch_comm_func "$FILTER_HOST" "$pass" "$win_path" "$func"
  else
    for f in F13 F14 F15 F16 F17 F18; do
      fetch_comm_func "$FILTER_HOST" "$pass" "$win_path" "$f"
    done
  fi
fi

echo "完成。运行: python3 scripts/aggregate_comm_rate_f1_f18.py && python3 scripts/patch_conference_comm_section.py"
