#!/usr/bin/env bash
# Batch RL-MACPO (LLSO) with 20-column logs (includes rho_avg, gate_comm, etc.).
#
# Usage (from repo root):
#   chmod +x scripts/run_rl_macpo_runs25_rho.sh
#   ./scripts/run_rl_macpo_runs25_rho.sh
#
# Environment:
#   FUNCTIONS   Space-separated benchmark ids (default: "F3 F5")
#   MPI_NPROCS  mpirun -np value (default: 20)
#   OUT_DIR     Output directory (default: <repo>/output/RL-output_runs25_rho)
#   MACPO_DEBUG_MAX_LOOPS  If set (e.g. 3), short runs for smoke test only.
#
# Each run writes: <OUT_DIR>/<F>_LLSO_final_runNN.txt  (NN=01..25)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${OUT_DIR:-${ROOT}/output/RL-output_runs25_rho}"
MACPO_DIR="${ROOT}/RL-MACPO"
EXE="${MACPO_DIR}/build/MACPO_simplified"
NP="${MPI_NPROCS:-20}"
FUNCTIONS="${FUNCTIONS:-F1 F2 F3 F4 F5 F6}" # conflict-highlighted pair; set to "F1 F2 F3 F4 F5 F6" for full 6×25

mkdir -p "${OUT_DIR}"

if [[ ! -x "${EXE}" ]]; then
  echo "Build first: cd ${MACPO_DIR}/build && make -j4"
  exit 1
fi

if [[ ! -f "${MACPO_DIR}/Benchmarks/default_config.json" ]]; then
  echo "Missing ${MACPO_DIR}/Benchmarks/default_config.json"
  exit 1
fi

echo "OUT_DIR=${OUT_DIR}"
echo "FUNCTIONS=${FUNCTIONS}"
echo "MPI_NPROCS=${NP}"
echo "EXE=${EXE}"
if [[ -n "${MACPO_DEBUG_MAX_LOOPS:-}" ]]; then
  echo "WARNING: MACPO_DEBUG_MAX_LOOPS=${MACPO_DEBUG_MAX_LOOPS} (short runs only)"
fi

cd "${MACPO_DIR}"
total=0
for fn in ${FUNCTIONS}; do
  for run in $(seq -f "%02g" 1 25); do
    exid="run${run}"
    echo ""
    echo "========== ${fn} ${exid} =========="
    mpirun --oversubscribe -np "${NP}" \
      "${EXE}" "${fn}" "${exid}" Full "${OUT_DIR}/"
    total=$((total + 1))
  done
done

echo ""
echo "Done. ${total} runs finished. Logs under: ${OUT_DIR}"
