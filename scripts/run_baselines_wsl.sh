#!/usr/bin/env bash
# 在 WSL 项目根目录跑 DPSO / GFPDO 基线（F1–F6 × LLSO/CSO × 25 runs）。
#
# 用法（WSL 内）:
#   tmux new -s dpso
#   cd /mnt/d/zyj/MACPO2 && bash scripts/run_baselines_wsl.sh dpso
#
#   tmux new -s gfpdo
#   cd /mnt/c/zyj/MACPO2 && bash scripts/run_baselines_wsl.sh gfpdo
#
# 环境变量:
#   RUNS=25          重复次数（默认 25）
#   SKIP_EXISTING=1  续跑（默认 1）
#   START_RUN=1      从第几次开始
#   NPROCS=20        MPI 进程数（F1–F6 固定 20）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALGO="${1:-${ALGO:-both}}"

case "$ALGO" in
  dpso|gfpdo|both) ;;
  *)
    echo "用法: bash scripts/run_baselines_wsl.sh {dpso|gfpdo|both}" >&2
    exit 1
    ;;
esac

# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/utils/wsl_mpi_env.sh"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

SRC="$ROOT/MACPO_sourcecode"
BUILD="$SRC/build"

if [[ ! -x "$BUILD/DPSO1" && "$ALGO" != gfpdo ]] || [[ ! -x "$BUILD/GFPDO_overlap" && "$ALGO" != dpso ]]; then
  echo "==> 编译 MACPO_sourcecode 基线 ..."
  cmake -S "$SRC" -B "$BUILD" -DCMAKE_BUILD_TYPE=Release
  case "$ALGO" in
    dpso)  cmake --build "$BUILD" -j"$(nproc)" --target DPSO1 ;;
    gfpdo) cmake --build "$BUILD" -j"$(nproc)" --target GFPDO_overlap ;;
    both)  cmake --build "$BUILD" -j"$(nproc)" ;;
  esac
fi

RUNS="${RUNS:-25}"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/baselines_${ALGO}_$(date +%Y%m%d_%H%M%S).log"

echo "============================================================"
echo "WSL baselines: ALGO=$ALGO RUNS=$RUNS"
echo "  log: $LOG"
echo "============================================================"

(
  cd "$SRC"
  ALGO="$ALGO" RUNS="$RUNS" NPROCS="${NPROCS:-20}" \
    SKIP_EXISTING="${SKIP_EXISTING:-1}" START_RUN="${START_RUN:-1}" \
    bash run_baselines_f1_f6_batch.sh
) 2>&1 | tee "$LOG"

echo ""
echo "完成。Mac 拉回: bash scripts/lan_fetch_results.sh --baselines"
echo "本地汇总:     python3 scripts/aggregate_baselines_f1_f6.py"
