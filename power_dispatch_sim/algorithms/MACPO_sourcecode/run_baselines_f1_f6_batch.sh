#!/usr/bin/env bash
# F1–F6 ×（LLSO / CSO）× 各 25 次（ex01–ex25），与 MACPO 相同使用 mpirun -n 20。
# 用法: bash run_baselines_f1_f6_batch.sh
# 环境变量:
#   BUILD   可执行文件目录（默认 ./build）
#   OUT     输出根目录（默认 ./output_baselines）
#   RUNS    重复次数（默认 25）
#   MPIRUN  mpirun 命令（默认 mpirun）
#   NPROCS  F1–F6 填 20（默认 20）；若跑 F7+ 请改 NPROCS

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

BUILD="${BUILD:-$ROOT/build}"
OUT="${OUT:-$ROOT/output_baselines}"
RUNS="${RUNS:-25}"
MPIRUN="${MPIRUN:-mpirun}"
NPROCS="${NPROCS:-20}"

mkdir -p "$OUT"

BIN_DPSO1="$BUILD/DPSO1"
BIN_GFPDO="$BUILD/GFPDO_overlap"

for b in "$BIN_DPSO1" "$BIN_GFPDO"; do
  if [[ ! -x "$b" ]]; then
    echo "找不到可执行文件: $b"
    echo "请先: cd $ROOT && cmake -S . -B build && cmake --build build"
    exit 1
  fi
done

FUNCS=(F1 F2 F3 F4 F5 F6)
OPTS=(LLSO CSO)

run_one() {
  local exe=$1 name=$2
  local f=$3 opt=$4 ex=$5
  echo "----------------------------------------"
  echo "$MPIRUN -n $NPROCS $name | $f | $opt | $ex"
  "$MPIRUN" -n "$NPROCS" --oversubscribe "$exe" "$f" "$ex" "$opt" "$OUT/" \
    2>&1 | tee "$OUT/${name}_${f}_${opt}_${ex}.stdout.log"
}

echo "BUILD=$BUILD OUT=$OUT RUNS=$RUNS NPROCS=$NPROCS"

for ((r=1; r<=RUNS; r++)); do
  ex=$(printf "ex%02d" "$r")
  for f in "${FUNCS[@]}"; do
    for opt in "${OPTS[@]}"; do
      run_one "$BIN_DPSO1" "DPSO1" "$f" "$opt" "$ex"
      run_one "$BIN_GFPDO" "GFPDO" "$f" "$opt" "$ex"
    done
  done
done

echo ""
echo "完成。每个 *.log 一行: Completed [...] final fitness=... total_time=...ms"
