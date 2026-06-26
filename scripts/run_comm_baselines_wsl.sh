#!/usr/bin/env bash
# WSL 跑通信基线（F1–F6）。自动建 logs/、MPI 环境、检查 Linux ELF 编译。
#
# 用法:
#   cd /mnt/d/zyj/MACPO2
#   bash scripts/run_comm_baselines_wsl.sh F1
#   SMOKE=1 bash scripts/run_comm_baselines_wsl.sh F1   # 只跑 Full×1，验证环境
#   RUNS=10 SLEEP_SEC=30 bash scripts/run_comm_baselines_wsl.sh F2
#   nohup bash scripts/run_comm_baselines_wsl.sh F3 > logs/comm_F3_wrapper.log 2>&1 &
#   tail -f "$(cat logs/.last_comm_F3.logpath)"
#
# 环境变量: RUNS SKIP_EXISTING SLEEP_SEC NP METHODS SMOKE
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FUNC="${1:-F1}"
RUNS="${RUNS:-10}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
SLEEP_SEC="${SLEEP_SEC:-30}"
NP="${NP:-20}"
METHODS="${METHODS:-}"
SMOKE="${SMOKE:-0}"

# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/utils/wsl_mpi_env.sh"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"

BIN="$ROOT/RL-MACPO/build/MACPO_simplified"
mkdir -p "$ROOT/logs" "$ROOT/ablation_experiments/results/comm_baselines/raw"

verify_linux_elf() {
  if [[ ! -x "$BIN" ]]; then
    echo "ERROR: 未找到 $BIN，正在编译 ..."
    cmake -S "$ROOT/RL-MACPO" -B "$ROOT/RL-MACPO/build" \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx
    cmake --build "$ROOT/RL-MACPO/build" -j1
  fi
  if ! file -b "$BIN" | grep -qE 'ELF .*x86-64'; then
    echo "ERROR: $BIN 不是 Linux ELF（请 rm -rf RL-MACPO/build 后在 WSL 重编译）" >&2
    file -b "$BIN" >&2 || true
    exit 1
  fi
}

verify_linux_elf

LOG="$ROOT/logs/comm_${FUNC}_$(date +%Y%m%d_%H%M%S).log"
echo "$LOG" > "$ROOT/logs/.last_comm_${FUNC}.logpath"
echo "日志: $LOG"
echo "函数: $FUNC runs=$RUNS np=$NP sleep=${SLEEP_SEC}s smoke=$SMOKE"
echo "说明: 单次 MPI 约 20–60 分钟；日志会实时写入。勿用 tail -f logs/comm_${FUNC}_*.log（会匹配旧空文件）"
echo "推荐: tail -f \"$LOG\""

ARGS=(python3 -u "$ROOT/scripts/run_comm_baselines.py" --funcs "$FUNC" --runs "$RUNS" --np "$NP" --sleep-sec "$SLEEP_SEC")
[[ "$SKIP_EXISTING" == "1" ]] && ARGS+=(--skip-existing)
if [[ "$SMOKE" == "1" ]]; then
  ARGS=(python3 -u "$ROOT/scripts/run_comm_baselines.py" --funcs "$FUNC" --runs 1 --np "$NP" --methods Full --sleep-sec 0)
fi
[[ -n "$METHODS" ]] && ARGS+=(--methods "$METHODS")

nice -n 19 ionice -c 3 "${ARGS[@]}" 2>&1 | tee "$LOG"
