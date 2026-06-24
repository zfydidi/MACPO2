#!/usr/bin/env bash
# Run MACPO (dump) + RL-MACPO (load) for F1–F6 with the same protocol as pair_init_pair_run.sh.
# Usage: bash scripts/pair_init_f1_f6.sh [EXID]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXID="${1:-panel_fair_r01}"
for F in F1 F2 F3 F4 F5 F6; do
  echo "========== ${F} ${EXID} =========="
  bash "${ROOT}/scripts/pair_init_pair_run.sh" "$F" "$EXID"
done
echo "All six functions done. EXID=${EXID}"
