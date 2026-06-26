#!/usr/bin/env bash
# 在 WSL 项目根目录跑 DPSO / GFPDO 基线（F1–F6 × LLSO/CSO × 25 runs）。
#
# 用法（必须在项目根目录，不要在 MACPO_sourcecode/ 里）:
#   cd /mnt/d/zyj/MACPO2
#
#   # 全量串行（慢，不推荐 GFPDO）
#   bash scripts/run_baselines_wsl.sh gfpdo
#
#   # 按函数拆（6 个窗口）
#   bash scripts/run_baselines_wsl.sh gfpdo F1
#
#   # 按函数 + 优化器拆（12 个窗口，最吃满 CPU）
#   bash scripts/run_baselines_wsl.sh gfpdo F1 LLSO
#   bash scripts/run_baselines_wsl.sh gfpdo F1 CSO
#
#   # 环境变量等价写法
#   FUNCS="F1 F2" OPTS=LLSO bash scripts/run_baselines_wsl.sh gfpdo
#
# 环境变量:
#   RUNS=25          重复次数（默认 25）
#   SKIP_EXISTING=1  续跑（默认 1）
#   START_RUN=1      从第几次开始
#   NPROCS=20        MPI 进程数（F1–F6 固定 20）
#   FUNCS            如 F1 或 "F1 F3"（默认 F1..F6）
#   OPTS             LLSO / CSO / "LLSO CSO"（默认两者）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALGO="${1:-${ALGO:-both}}"
FUNC_ARG="${2:-}"
OPT_ARG="${3:-}"

case "$ALGO" in
  dpso|gfpdo|both) ;;
  *)
    echo "用法: bash scripts/run_baselines_wsl.sh {dpso|gfpdo|both} [F1..F6] [LLSO|CSO]" >&2
    exit 1
    ;;
esac

if [[ -n "$FUNC_ARG" ]]; then
  export FUNCS="$FUNC_ARG"
fi

if [[ -n "$OPT_ARG" ]]; then
  case "$OPT_ARG" in
    LLSO|CSO) export OPTS="$OPT_ARG" ;;
    *)
      echo "第 3 个参数须为 LLSO 或 CSO，收到: $OPT_ARG" >&2
      exit 1
      ;;
  esac
fi

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
FUNCS_TAG="${FUNCS:-ALL}"
FUNCS_TAG="${FUNCS_TAG// /_}"
OPTS_TAG="${OPTS:-LLSO_CSO}"
OPTS_TAG="${OPTS_TAG// /_}"
LOG="$LOG_DIR/baselines_${ALGO}_${FUNCS_TAG}_${OPTS_TAG}_$(date +%Y%m%d_%H%M%S).log"
echo "$LOG" >"$LOG_DIR/.last_baselines_${ALGO}_${FUNCS_TAG}_${OPTS_TAG}.logpath"

echo "============================================================"
echo "WSL baselines: ALGO=$ALGO FUNCS=${FUNCS:-F1..F6} OPTS=${OPTS:-LLSO CSO} RUNS=$RUNS"
echo "  OUT: MACPO_sourcecode/output_baselines_${ALGO}_25runs"
echo "  log: $LOG"
echo "  tail: tail -f \"\$(cat logs/.last_baselines_${ALGO}_${FUNCS_TAG}_${OPTS_TAG}.logpath)\""
echo "============================================================"

(
  cd "$SRC"
  ALGO="$ALGO" RUNS="$RUNS" NPROCS="${NPROCS:-20}" \
    FUNCS="${FUNCS:-}" OPTS="${OPTS:-}" \
    SKIP_EXISTING="${SKIP_EXISTING:-1}" START_RUN="${START_RUN:-1}" \
    bash run_baselines_f1_f6_batch.sh
) 2>&1 | tee "$LOG"

echo ""
echo "完成。Mac 拉回: bash scripts/lan_fetch_results.sh --baselines"
echo "本地汇总:     python3 scripts/aggregate_baselines_f1_f6.py"
