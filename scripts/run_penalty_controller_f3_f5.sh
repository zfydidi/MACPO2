#!/usr/bin/env bash
# Penalty-controller comparison on F3/F5 (25 runs each).
# Same Full gating/selection stack; differs only in penalty update:
#   Selection_0.9_0.7_0.5  -> RL (paper Full)
#   EMA_Penalty              -> AdaptivePenaltyController heuristic
#   FixedSchedule            -> fixed phase ratios (no RL)
#
# MACPO baseline is read from MACPO_original_output/LLSO_25runs (existing 25-run batch).
#
# Usage:
#   NPROC=20 bash scripts/run_penalty_controller_f3_f5.sh
#   python3 utils/penalty_controller_stats.py
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NPROC="${NPROC:-20}"
RUNS="${RUNS:-25}"
BIN="${ROOT}/RL-MACPO/build/MACPO_simplified"
OUT="${ROOT}/ablation_experiments/results/penalty_controller_f3_f5"

if [[ ! -x "$BIN" ]]; then
  echo "Build first: cd RL-MACPO/build && cmake .. && make MACPO_simplified" >&2
  exit 1
fi

mkdir -p "$OUT"/{EMA_Penalty,FixedSchedule,Selection_0.9_0.7_0.5}

echo "Penalty-controller study: F3/F5 × ${RUNS} runs × 3 controllers"
echo "Output -> $OUT"

FORCE="${FORCE:-0}"

for F in F3 F5; do
  for i in $(seq 1 "$RUNS"); do
    printf -v RID 'run%02d' "$i"
    export MACPO_PAIR_SEED="$i"
    for CFG in EMA_Penalty FixedSchedule Selection_0.9_0.7_0.5; do
      dest="${OUT}/${CFG}/${F}_LLSO_final_${RID}.txt"
      if [[ "$FORCE" != "1" && -f "$dest" ]]; then
        echo "[skip] $CFG $F $RID"
        continue
      fi
      echo "======== $CFG $F $RID (MACPO_PAIR_SEED=$i) ========"
      (cd "${ROOT}/RL-MACPO" && mpirun --oversubscribe -n "$NPROC" \
        -x MACPO_PAIR_SEED \
        "$BIN" "$F" "$RID" "$CFG" "${OUT}/${CFG}/")
    done
  done
done

python3 "${ROOT}/utils/penalty_controller_stats.py" --root "$OUT" --runs "$RUNS"
echo "Done. JSON -> RL_MACPO_IEEE_English_with_images/media/penalty_controller_f3_f5.json"
