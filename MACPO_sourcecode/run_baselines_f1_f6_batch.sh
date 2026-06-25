#!/usr/bin/env bash
# F1–F6 ×（LLSO / CSO）× DPSO1 + GFPDO，默认 25 次（ex01–ex25）。
# 用法: RUNS=5 bash run_baselines_f1_f6_batch.sh
# 环境变量:
#   BUILD   可执行文件目录（默认 ./build）
#   OUT     输出根目录（默认 ./output_baselines）
#   RUNS    重复次数（默认 25）
#   MPIRUN  已废弃；内部使用 mpirun --allow-run-as-root 数组调用
#   NPROCS  F1–F6 填 20（默认 20）；若跑 F7+ 请改 NPROCS
#   ALGO    dpso | gfpdo | both（默认 both，分机跑时设为 dpso 或 gfpdo）

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/../utils/wsl_mpi_env.sh"

BUILD="${BUILD:-$ROOT/build}"
OUT="${OUT:-$ROOT/output_baselines}"
RUNS="${RUNS:-25}"
MPI_ARGS=(mpirun --allow-run-as-root "${WSL_MPIRUN_MCA_ARGS[@]}")
NPROCS="${NPROCS:-20}"
ALGO="${ALGO:-both}"

mkdir -p "$OUT"

BIN_DPSO1="$BUILD/DPSO1"
BIN_GFPDO="$BUILD/GFPDO_overlap"

case "$ALGO" in
  dpso)  need_bins=("$BIN_DPSO1") ;;
  gfpdo) need_bins=("$BIN_GFPDO") ;;
  both)  need_bins=("$BIN_DPSO1" "$BIN_GFPDO") ;;
  *) echo "ALGO 须为 dpso | gfpdo | both"; exit 1 ;;
esac

for b in "${need_bins[@]}"; do
  if [[ ! -x "$b" ]]; then
    echo "找不到可执行文件: $b"
    echo "请先: cd $ROOT && cmake -S . -B build && cmake --build build"
    exit 1
  fi
done

case "$ALGO" in
  dpso)  ALGOS=(dpso) ;;
  gfpdo) ALGOS=(gfpdo) ;;
  both)  ALGOS=(dpso gfpdo) ;;
esac

FUNCS=(F1 F2 F3 F4 F5 F6)
OPTS=(LLSO CSO)
TOTAL_JOBS=$((RUNS * ${#FUNCS[@]} * ${#OPTS[@]} * ${#ALGOS[@]}))
JOB_IDX=0
BATCH_START=$SECONDS

echo "============================================================"
echo "GFPDO/DPSO baseline batch"
echo "  BUILD=$BUILD"
echo "  OUT=$OUT"
echo "  RUNS=$RUNS  NPROCS=$NPROCS  ALGO=$ALGO"
echo "  total jobs=$TOTAL_JOBS  (funcs=${FUNCS[*]}  opts=${OPTS[*]})"
echo "============================================================"

run_one() {
  local exe=$1 name=$2
  local f=$3 opt=$4 ex=$5
  JOB_IDX=$((JOB_IDX + 1))
  local elapsed=$((SECONDS - BATCH_START))
  echo ""
  echo "[$JOB_IDX/$TOTAL_JOBS] +${elapsed}s | $name | $f | $opt | $ex"
  echo "  cmd: ${MPI_ARGS[*]} -n $NPROCS $name $f $ex $opt $OUT/"
  local run_start=$SECONDS
  if "${MPI_ARGS[@]}" -n "$NPROCS" --oversubscribe "$exe" "$f" "$ex" "$opt" "$OUT/" \
    >"$OUT/${name}_${f}_${opt}_${ex}.stdout.log" 2>&1; then
    :
  else
    echo "  !! exit code $? (see $OUT/${name}_${f}_${opt}_${ex}.stdout.log)"
  fi
  local run_s=$((SECONDS - run_start))
  local logf="$OUT/${name}_${f}_${opt}_${ex}.log"
  if [[ -f "$logf" ]]; then
    local summary
    summary=$(grep -Eo 'final fitness=[0-9.eE+-]+' "$logf" | tail -1 || true)
    local wall
    wall=$(grep -Eo 'total[_ ]time=[0-9]+ms' "$logf" | tail -1 || true)
    echo "  done in ${run_s}s | ${summary:-no final fitness} | ${wall:-}"
  else
    echo "  done in ${run_s}s | (missing $logf)"
  fi
}

for ((r=1; r<=RUNS; r++)); do
  ex=$(printf "ex%02d" "$r")
  echo ""
  echo "---- run $r/$RUNS ($ex) ----"
  for f in "${FUNCS[@]}"; do
    for opt in "${OPTS[@]}"; do
      for algo in "${ALGOS[@]}"; do
        if [[ "$algo" == "dpso" ]]; then
          run_one "$BIN_DPSO1" "DPSO1" "$f" "$opt" "$ex"
        else
          run_one "$BIN_GFPDO" "GFPDO" "$f" "$opt" "$ex"
        fi
      done
    done
  done
done

echo ""
echo "============================================================"
echo "完成: $TOTAL_JOBS jobs, wall $((SECONDS - BATCH_START))s"
echo "日志: $OUT/*.log  (Completed [...] final fitness=...)"
echo "============================================================"
