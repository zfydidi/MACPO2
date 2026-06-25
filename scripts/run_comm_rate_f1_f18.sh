#!/usr/bin/env bash
# Re-run RL-MACPO with COST_STATS logging for comm_rate (F1-F18, LLSO).
#
# 环境变量:
#   RUNS          每个函数重复次数（默认 25）
#   FUNCS         逗号分隔，如 F13 或 F13,F14
#   SKIP_EXISTING 1=跳过已有非空结果文件（默认 1，续跑）
#   FORCE         1=忽略已有结果，全部重跑
#   START_RUN     从第几次开始（默认 1）
#   LIVE_TAIL     1=实时把结果文件迭代表刷到控制台（默认 1，类似 output/ablation/*.txt）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=../utils/wsl_mpi_env.sh
source "$ROOT/utils/wsl_mpi_env.sh"
RLMACPO="$ROOT/RL-MACPO"
BIN="$RLMACPO/build/MACPO_simplified"
OUT="$ROOT/ablation_experiments/results/comm_rate_f1_f18"
MPI_LOG_DIR="$ROOT/logs/comm_rate_mpi"
RUNS="${RUNS:-25}"
FUNCS="${FUNCS:-F1,F2,F3,F4,F5,F6,F7,F8,F9,F10,F11,F12,F13,F14,F15,F16,F17,F18}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
START_RUN="${START_RUN:-1}"
FORCE="${FORCE:-0}"
LIVE_TAIL="${LIVE_TAIL:-1}"

if [[ "$FORCE" == "1" ]]; then
  SKIP_EXISTING=0
fi

np_for_func() {
  python3 -c "import json; from pathlib import Path; cfg=json.loads(Path('${RLMACPO}/Benchmarks/default_config.json').read_text()); print(int(cfg['benchmarks']['${1}']['group_num']))"
}

verify_linux_elf() {
  local bin="$1"
  if [[ ! -x "$bin" ]]; then
    echo "ERROR: 找不到可执行文件: $bin" >&2
    echo "  请先: cmake -S RL-MACPO -B RL-MACPO/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx" >&2
    echo "        cmake --build RL-MACPO/build -j\$(nproc)" >&2
    exit 1
  fi
  if ! file -b "$bin" | grep -qE 'ELF .*x86-64'; then
    echo "ERROR: $bin 不是 Linux x86-64 ELF（常见原因: 从 Mac 拷入了 build/）" >&2
    file -b "$bin" >&2 || true
    echo "  请: rm -rf RL-MACPO/build 后在 WSL 内重新 cmake --build" >&2
    exit 1
  fi
}

verify_linux_elf "$BIN"
mkdir -p "$MPI_LOG_DIR"

run_mpi_with_live_output() {
  local func="$1" exid="$2" cfg="$3" outdir="$4" np="$5" mpi_log="$6" outfile="$7"
  local mpi_pid tail_pid="" waited=0 rc=0

  echo "========================================"
  echo "  实时输出: 迭代表 -> 控制台（同 ${outfile##*/}）"
  echo "  MPI 日志备份: $mpi_log"
  echo "========================================"

  (
    cd "$RLMACPO" && mpirun --allow-run-as-root "${WSL_MPIRUN_MCA_ARGS[@]}" -np "$np" --oversubscribe ./build/MACPO_simplified \
      "$func" "$exid" "$cfg" "$outdir"
  ) > >(tee "$mpi_log") 2>&1 &
  mpi_pid=$!

  if [[ "$LIVE_TAIL" == "1" ]]; then
    while [[ ! -f "$outfile" ]] && (( waited < 180 )); do
      sleep 1
      waited=$((waited + 1))
      if ! kill -0 "$mpi_pid" 2>/dev/null; then
        break
      fi
    done
    if [[ -f "$outfile" ]]; then
      tail -n 0 -f "$outfile" &
      tail_pid=$!
    fi
  fi

  wait "$mpi_pid" || rc=$?
  if [[ -n "$tail_pid" ]]; then
    kill "$tail_pid" 2>/dev/null || true
    wait "$tail_pid" 2>/dev/null || true
  fi
  return "$rc"
}

IFS=',' read -ra FUNC_ARR <<< "$FUNCS"
total=$((${#FUNC_ARR[@]} * RUNS))
k=0

for func in "${FUNC_ARR[@]}"; do
  if [[ "$func" =~ ^F[1-6]$ ]]; then
    sub="F1_F6"
    cfg="Selection_0.9_0.7_0.5"
    outdir="$OUT/$sub/$func/"
  else
    sub="F7_F18"
    cfg="Full"
    outdir="$OUT/$sub/$func/"
  fi
  mkdir -p "$outdir"
  NP="$(np_for_func "$func")"
  for ((i=1; i<=RUNS; i++)); do
    k=$((k + 1))
    if [[ "$i" -lt "$START_RUN" ]]; then
      continue
    fi
    exid="comm_$(printf '%02d' "$i")"
    outfile="$outdir/${func}_LLSO_final_${exid}.txt"
    mpi_log="$MPI_LOG_DIR/${func}_${exid}.log"

    if [[ "$SKIP_EXISTING" == "1" && -s "$outfile" ]]; then
      rate=$(grep -o 'comm_rate=[0-9.eE+-]*' "$outfile" | tail -1 | cut -d= -f2 || echo "?")
      echo "[$k/$total] $func $cfg run $i/$RUNS SKIP (exists comm_rate=$rate)"
      continue
    fi

    t0=$(date +%s)
    echo ""
    echo "[$k/$total] $func $cfg run $i/$RUNS  started=$(date '+%H:%M:%S')"
    if ! run_mpi_with_live_output "$func" "$exid" "$cfg" "$outdir" "$NP" "$mpi_log" "$outfile"; then
      echo "FAILED $func run $i (see $mpi_log)" >&2
      tail -20 "$mpi_log" >&2 || true
      continue
    fi
    if [[ ! -s "$outfile" ]]; then
      echo "FAILED $func run $i (mpirun ok but missing $outfile)" >&2
      tail -10 "$mpi_log" >&2 || true
      continue
    fi
    dt=$(($(date +%s) - t0))
    rate=$(grep -o 'comm_rate=[0-9.eE+-]*' "$outfile" | tail -1 | cut -d= -f2 || echo "?")
    echo ""
    echo "  >>> done ${dt}s comm_rate=$rate finished=$(date '+%H:%M:%S')"
  done
done

python3 "$ROOT/scripts/aggregate_comm_rate_f1_f18.py" --runs "$RUNS"
echo "Comm-rate batch complete."
