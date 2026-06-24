#!/usr/bin/env bash
# Re-run RL-MACPO with COST_STATS logging for comm_rate (F1-F18, LLSO).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RLMACPO="$ROOT/RL-MACPO"
BIN="$RLMACPO/build/MACPO_simplified"
OUT="$ROOT/ablation_experiments/results/comm_rate_f1_f18"
RUNS="${RUNS:-25}"
FUNCS="${FUNCS:-F1,F2,F3,F4,F5,F6,F7,F8,F9,F10,F11,F12,F13,F14,F15,F16,F17,F18}"

np_for_func() {
  python3 -c "import json; from pathlib import Path; cfg=json.loads(Path('${RLMACPO}/Benchmarks/default_config.json').read_text()); print(int(cfg['benchmarks']['${1}']['group_num']))"
}

if [[ ! -x "$BIN" ]]; then
  echo "Build first: (cd $RLMACPO/build && make -j4)"
  exit 1
fi

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
    exid="comm_$(printf '%02d' "$i")"
    t0=$(date +%s)
    echo "[$k/$total] $func $cfg run $i/$RUNS"
    (cd "$RLMACPO" && mpirun --allow-run-as-root -np "$NP" --oversubscribe ./build/MACPO_simplified \
      "$func" "$exid" "$cfg" "$outdir") >/dev/null 2>&1 || {
        echo "FAILED $func run $i" >&2
        continue
      }
    dt=$(($(date +%s) - t0))
    rate=$(grep -o 'comm_rate=[0-9.eE+-]*' "$outdir/${func}_LLSO_final_${exid}.txt" | tail -1 | cut -d= -f2 || echo "?")
    echo "  done ${dt}s comm_rate=$rate"
  done
done

python3 "$ROOT/scripts/aggregate_comm_rate_f1_f18.py" --runs "$RUNS"
echo "Comm-rate batch complete."
