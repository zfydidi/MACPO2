#!/usr/bin/env bash
# 单机跑 1 个 GFPDO job（F1–F6 × LLSO/CSO × ex01），控制台实时输出。
#
# 用法:
#   FUNC=F1 OPT=LLSO EX=ex01 OUT=./output_baselines_gfpdo_1run bash run_gfpdo_single.sh
#
# 环境变量:
#   FUNC   F1..F6（必填）
#   OPT    LLSO | CSO（默认 LLSO）
#   EX     ex01（默认 ex01）
#   OUT    输出目录（默认 ./output_baselines_gfpdo_1run）
#   NPROCS MPI 进程数（默认 20）
#   BUILD  build 目录（默认 ./build）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/../utils/wsl_mpi_env.sh"

FUNC="${FUNC:?请设置 FUNC=F1..F6}"
OPT="${OPT:-LLSO}"
EX="${EX:-ex01}"
OUT="${OUT:-$ROOT/output_baselines_gfpdo_1run}"
BUILD="${BUILD:-$ROOT/build}"
NPROCS="${NPROCS:-20}"
BIN="$BUILD/GFPDO_overlap"

mkdir -p "$OUT"

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: 找不到 $BIN，请先编译 GFPDO_overlap" >&2
  exit 1
fi
if ! file -b "$BIN" | grep -qE 'ELF .*x86-64'; then
  echo "ERROR: $BIN 不是 Linux x86-64 ELF，请 rm -rf build 后在 WSL 重编译" >&2
  file -b "$BIN" >&2 || true
  exit 1
fi

export OMPI_ALLOW_RUN_AS_ROOT="${OMPI_ALLOW_RUN_AS_ROOT:-1}"
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM="${OMPI_ALLOW_RUN_AS_ROOT_CONFIRM:-1}"

iter_log="$OUT/iter_GFPDO_${FUNC}_${OPT}_${EX}.txt"
summary_log="$OUT/GFPDO_${FUNC}_${OPT}_${EX}.log"
mpi_log="$OUT/GFPDO_${FUNC}_${OPT}_${EX}.stdout.log"

echo "============================================================"
echo "GFPDO single job"
echo "  $FUNC | $OPT | $EX | NPROCS=$NPROCS"
echo "  OUT=$OUT"
echo "  控制台: Iteration / Best Fitness（每代一行）"
echo "  备份:   $mpi_log"
echo "============================================================"

echo ""
echo "cmd: mpirun --allow-run-as-root ${WSL_MPIRUN_MCA_ARGS[*]} -n $NPROCS --oversubscribe GFPDO_overlap $FUNC $EX $OPT $OUT/"
echo "started=$(date '+%Y-%m-%d %H:%M:%S')"
echo ""

t0=$(date +%s)
if mpirun --allow-run-as-root "${WSL_MPIRUN_MCA_ARGS[@]}" -n "$NPROCS" --oversubscribe "$BIN" \
  "$FUNC" "$EX" "$OPT" "$OUT/" 2>&1 | tee "$mpi_log"; then
  rc=0
else
  rc=$?
fi

dt=$(($(date +%s) - t0))
echo ""
if [[ -f "$summary_log" ]]; then
  grep -E 'final fitness|total time' "$summary_log" | tail -1 || true
elif [[ -f "$mpi_log" ]]; then
  grep -E 'Completed|final fitness' "$mpi_log" | tail -1 || true
fi
echo "finished=$(date '+%Y-%m-%d %H:%M:%S')  wall=${dt}s  exit=$rc"
echo "iter log: $iter_log"

exit "$rc"
