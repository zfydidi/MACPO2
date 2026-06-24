#!/usr/bin/env bash
# 按「一机一函数 + GFPDO/DPSO 分机」一键分发并启动全部远程实验。
#
# 分工见 scripts/lan_dispatch_plan.tsv（9 台中 8 台干活，.27 备用）
#
# 用法:
#   bash scripts/lan_dispatch_all.sh
#   bash scripts/lan_dispatch_all.sh --distribute-only
#   bash scripts/lan_dispatch_all.sh --run-only
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLAN="$ROOT/scripts/lan_dispatch_plan.tsv"

DISTRIBUTE=true
RUN=true
for arg in "$@"; do
  case "$arg" in
    --distribute-only) RUN=false ;;
    --run-only) DISTRIBUTE=false ;;
  esac
done

echo "======== 局域网实验分工 ========"
grep -v '^#' "$PLAN" | grep -v '^$' | awk -F'\t' '{printf "%-16s %-18s %s\n", $1, $2, $3}'
echo "备用机: 10.21.51.27"
echo "================================"

if [[ "$DISTRIBUTE" == true ]]; then
  echo ""
  echo ">>> 向全部可达主机分发源码..."
  bash "$ROOT/scripts/lan_distribute.sh"
fi

if [[ "$RUN" == true ]]; then
  echo ""
  echo ">>> 按分工启动远程任务..."
  while IFS=$'\t' read -r ip kind payload; do
    [[ -z "${ip:-}" || "$ip" =~ ^# ]] && continue
    case "$kind" in
      comm)
        FUNCS="$payload" TASK=comm_f13_f18 STOP_OLD=1 \
          bash "$ROOT/scripts/lan_run_remote.sh" --host "$ip" || echo "!! $ip 启动失败"
        ;;
      baselines_dpso)
        TASK=baselines_dpso STOP_OLD=1 \
          bash "$ROOT/scripts/lan_run_remote.sh" --host "$ip" || echo "!! $ip 启动失败"
        ;;
      baselines_gfpdo)
        TASK=baselines_gfpdo STOP_OLD=1 \
          bash "$ROOT/scripts/lan_run_remote.sh" --host "$ip" || echo "!! $ip 启动失败"
        ;;
    esac
  done < <(grep -v '^#' "$PLAN" | grep -v '^$')
fi

echo ""
echo "全部调度完成。完成后: bash scripts/lan_fetch_results.sh --all"
