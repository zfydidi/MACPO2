#!/usr/bin/env bash
# F1–F6 ×（LLSO / CSO）× DPSO1 + GFPDO，默认 25 次（ex01–ex25）。
#
# 用法:
#   ALGO=dpso  RUNS=25 bash run_baselines_f1_f6_batch.sh
#   ALGO=gfpdo RUNS=25 OUT=./output_baselines_gfpdo_25runs bash run_baselines_f1_f6_batch.sh
#
# 环境变量:
#   BUILD          可执行文件目录（默认 ./build）
#   OUT            输出根目录（默认见下方 ALGO 分支）
#   RUNS           重复次数（默认 25）
#   NPROCS         F1–F6 填 20（默认 20）
#   ALGO           dpso | gfpdo | both（默认 both）
#   FUNCS          空格/逗号分隔，如 "F1" 或 "F1 F3 F5"（默认 F1–F6 全部）
#   OPTS           LLSO / CSO / "LLSO CSO"（默认两者）
#   SKIP_EXISTING  1=已有 final fitness 的 .log 则跳过（默认 1，续跑）
#   FORCE          1=忽略 SKIP_EXISTING，全部重跑
#   START_RUN      从第几次开始（默认 1，如 START_RUN=6 从 ex06 起）
#
# 多窗口并行（GFPDO 很慢，建议每函数开一个 WSL/CMD）:
#   FUNCS=F1 ALGO=gfpdo bash run_baselines_f1_f6_batch.sh
#   FUNCS=F2 ALGO=gfpdo bash run_baselines_f1_f6_batch.sh
#   … 六个窗口可同时跑，输出目录相同、SKIP_EXISTING=1 自动续跑不冲突

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/../utils/wsl_mpi_env.sh"

BUILD="${BUILD:-$ROOT/build}"
RUNS="${RUNS:-25}"
NPROCS="${NPROCS:-20}"
ALGO="${ALGO:-both}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
START_RUN="${START_RUN:-1}"
FORCE="${FORCE:-0}"

if [[ "$FORCE" == "1" ]]; then
  SKIP_EXISTING=0
fi

case "$ALGO" in
  dpso)  OUT="${OUT:-$ROOT/output_baselines_dpso_25runs}" ;;
  gfpdo) OUT="${OUT:-$ROOT/output_baselines_gfpdo_25runs}" ;;
  both)  OUT="${OUT:-$ROOT/output_baselines_25runs}" ;;
  *) echo "ALGO 须为 dpso | gfpdo | both"; exit 1 ;;
esac

MPI_ARGS=(mpirun --allow-run-as-root "${WSL_MPIRUN_MCA_ARGS[@]}")
mkdir -p "$OUT"

BIN_DPSO1="$BUILD/DPSO1"
BIN_GFPDO="$BUILD/GFPDO_overlap"

verify_linux_elf() {
  local bin="$1"
  if [[ ! -x "$bin" ]]; then
    echo "ERROR: 找不到可执行文件: $bin" >&2
    echo "  请先: cd $ROOT && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j\$(nproc)" >&2
    exit 1
  fi
  if ! file -b "$bin" | grep -qE 'ELF .*x86-64'; then
    echo "ERROR: $bin 不是 Linux x86-64 ELF（常见: 从 Mac 拷了 build/）" >&2
    file -b "$bin" >&2 || true
    echo "  请: rm -rf build && 在 WSL 内重新 cmake --build" >&2
    exit 1
  fi
}

case "$ALGO" in
  dpso)  need_bins=("$BIN_DPSO1") ;;
  gfpdo) need_bins=("$BIN_GFPDO") ;;
  both)  need_bins=("$BIN_DPSO1" "$BIN_GFPDO") ;;
esac
for b in "${need_bins[@]}"; do
  verify_linux_elf "$b"
done

case "$ALGO" in
  dpso)  ALGOS=(dpso) ;;
  gfpdo) ALGOS=(gfpdo) ;;
  both)  ALGOS=(dpso gfpdo) ;;
esac

_parse_list() {
  # "F1,F2 F3" -> F1 F2 F3
  echo "$1" | tr ',\t' '  ' | tr -s ' ' | sed 's/^ //;s/ $//'
}

FUNCS_RAW="${FUNCS:-F1 F2 F3 F4 F5 F6}"
OPTS_RAW="${OPTS:-LLSO CSO}"
read -r -a FUNCS <<< "$(_parse_list "$FUNCS_RAW")"
read -r -a OPTS <<< "$(_parse_list "$OPTS_RAW")"
TOTAL_JOBS=$(( (RUNS - START_RUN + 1) * ${#FUNCS[@]} * ${#OPTS[@]} * ${#ALGOS[@]} ))
JOB_IDX=0
BATCH_START=$SECONDS

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OMPI_ALLOW_RUN_AS_ROOT="${OMPI_ALLOW_RUN_AS_ROOT:-1}"
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM="${OMPI_ALLOW_RUN_AS_ROOT_CONFIRM:-1}"

echo "============================================================"
echo "GFPDO/DPSO baseline batch"
echo "  BUILD=$BUILD"
echo "  OUT=$OUT"
echo "  RUNS=$RUNS  START_RUN=$START_RUN  NPROCS=$NPROCS  ALGO=$ALGO"
echo "  SKIP_EXISTING=$SKIP_EXISTING  FORCE=$FORCE"
echo "  total jobs=$TOTAL_JOBS  (funcs=${FUNCS[*]}  opts=${OPTS[*]})"
echo "============================================================"

run_has_final() {
  local logf="$1"
  [[ -s "$logf" ]] && grep -qE 'final fitness=' "$logf" 2>/dev/null
}

run_one() {
  local exe=$1 name=$2
  local f=$3 opt=$4 ex=$5
  local logf="$OUT/${name}_${f}_${opt}_${ex}.log"
  local stdlog="$OUT/${name}_${f}_${opt}_${ex}.stdout.log"

  if [[ "$SKIP_EXISTING" == "1" ]] && run_has_final "$logf"; then
    JOB_IDX=$((JOB_IDX + 1))
    local summary
    summary=$(grep -Eo 'final fitness=[0-9.eE+-]+' "$logf" | tail -1 || true)
    echo "[$JOB_IDX/$TOTAL_JOBS] SKIP $name | $f | $opt | $ex | ${summary:-ok}"
    return 0
  fi

  JOB_IDX=$((JOB_IDX + 1))
  local elapsed=$((SECONDS - BATCH_START))
  echo ""
  echo "[$JOB_IDX/$TOTAL_JOBS] +${elapsed}s | $name | $f | $opt | $ex"
  echo "  cmd: ${MPI_ARGS[*]} -n $NPROCS $name $f $ex $opt $OUT/"
  local run_start=$SECONDS
  if "${MPI_ARGS[@]}" -n "$NPROCS" --oversubscribe "$exe" "$f" "$ex" "$opt" "$OUT/" \
    >"$stdlog" 2>&1; then
    :
  else
    echo "  !! exit code $? (see $stdlog)"
  fi
  local run_s=$((SECONDS - run_start))
  if run_has_final "$logf"; then
    local summary wall
    summary=$(grep -Eo 'final fitness=[0-9.eE+-]+' "$logf" | tail -1 || true)
    wall=$(grep -Eo 'total[_ ]time=[0-9]+ms' "$logf" | tail -1 || true)
    echo "  done in ${run_s}s | ${summary:-no final fitness} | ${wall:-}"
  else
    echo "  done in ${run_s}s | (missing or incomplete $logf)"
  fi
}

for ((r=START_RUN; r<=RUNS; r++)); do
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
echo "完成: $TOTAL_JOBS jobs (attempted), wall $((SECONDS - BATCH_START))s"
echo "日志: $OUT/*.log  (Completed [...] final fitness=...)"
echo "汇总: python3 scripts/aggregate_baselines_f1_f6.py"
echo "============================================================"
