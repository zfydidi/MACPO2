#!/usr/bin/env bash
# Run MACPO (baseline) and RL-MACPO for F1--F6 with the same exID.
# Usage: from MACPO2 repo root:  bash scripts/run_macpo_rl_f1_f6.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXID="${EXID:-paper_r01}"
NPROC="${NPROC:-20}"

MACPO_BIN="${ROOT}/MACPO_sourcecode/build/MACPO_source"
RL_BIN="${ROOT}/RL-MACPO/build/MACPO_simplified"
MACPO_OUT="${ROOT}/MACPO_sourcecode/output_fair"
RL_ROOT="${ROOT}/RL-MACPO"

for b in "$MACPO_BIN" "$RL_BIN"; do
  if [[ ! -x "$b" ]]; then
    echo "Missing executable: $b — build first (cmake/make)." >&2
    exit 1
  fi
done

mkdir -p "$MACPO_OUT"

echo "=== MACPO baseline: F1--F6, exID=$EXID ==="
for F in F1 F2 F3 F4 F5 F6; do
  echo "--- MACPO $F ---"
  (cd "${ROOT}/MACPO_sourcecode" && mpirun --oversubscribe -n "$NPROC" \
    "$MACPO_BIN" "$F" "$EXID" LLSO ./output_fair/)
done

echo "=== RL-MACPO: F1--F6, exID=$EXID, config=Full ==="
for F in F1 F2 F3 F4 F5 F6; do
  echo "--- RL-MACPO $F ---"
  (cd "$RL_ROOT" && mpirun --oversubscribe -n "$NPROC" \
    "$RL_BIN" "$F" "$EXID" Full)
done

echo "Done. Logs:"
echo "  MACPO:  ${MACPO_OUT}/F*_LLSO_${EXID}.txt"
echo "  RL:     ${RL_ROOT}/output/F*_LLSO_final_${EXID}.txt"
echo "Plot: python3 ${ROOT}/scripts/plot_fes_by_function.py --exid ${EXID}"
