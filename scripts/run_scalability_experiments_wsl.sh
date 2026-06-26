#!/usr/bin/env bash
# WSL 跑 scalability（F1/F7/F13/F1S50/F1S100）。自动建 logs/、MPI 环境、检查编译。
#
# 用法（单机多窗口，每窗口一个 benchmark）:
#   cd /mnt/d/zyj/MACPO2
#   bash scripts/run_scalability_experiments_wsl.sh F1
#   RUNS=5 SLEEP_SEC=60 bash scripts/run_scalability_experiments_wsl.sh F7
#   nohup bash scripts/run_scalability_experiments_wsl.sh F1S100 > logs/scale_F1S100_wrapper.log 2>&1 &
#
# 环境变量: RUNS SLEEP_SEC
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BENCH="${1:-F1}"
RUNS="${RUNS:-5}"
SLEEP_SEC="${SLEEP_SEC:-60}"

# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/utils/wsl_mpi_env.sh"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"

BIN="$ROOT/RL-MACPO/build/MACPO_simplified"
mkdir -p "$ROOT/logs" "$ROOT/ablation_experiments/results/scalability"

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

# F1S50/F1S100 需要先生成 Benchmarks/data/*.txt
python3 -c "from utils.chain_benchmark_codegen import ensure_scalability_benchmarks as e; w=e(); print('codegen:', w or 'ok')"

case "$BENCH" in
  F1|F7|F13) ;;
  F1S50) SLEEP_SEC="${SLEEP_SEC:-90}" ;;
  F1S100) SLEEP_SEC="${SLEEP_SEC:-120}" ;;
  *)
    echo "未知 benchmark: $BENCH（可选 F1 F7 F13 F1S50 F1S100）" >&2
    exit 1
    ;;
esac

LOG="$ROOT/logs/scale_${BENCH}_$(date +%Y%m%d_%H%M%S).log"
echo "$LOG" > "$ROOT/logs/.last_scale_${BENCH}.logpath"
echo "日志: $LOG"
echo "benchmark: $BENCH runs=$RUNS sleep=${SLEEP_SEC}s"
echo "推荐: tail -f \"$LOG\""

nice -n 19 ionice -c 3 python3 -u "$ROOT/scripts/run_scalability_experiments.py" \
  --benchmarks "$BENCH" --runs "$RUNS" --sleep-sec "$SLEEP_SEC" \
  2>&1 | tee "$LOG"
