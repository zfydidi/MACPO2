#!/usr/bin/env bash
# MACPO + RL-MACPO: F1–F6, 25 independent runs each (run01..run25), same protocol.
# Outputs:
#   MACPO_sourcecode/output_runs25/F{1-6}_LLSO_run{01-25}.txt
#   RL-MACPO/output_runs25/F{1-6}_LLSO_final_run{01-25}.txt
# Then: python3 scripts/plot_fes_by_function.py --n_runs 25 \
#         --macpo_dir MACPO_sourcecode/output_runs25 --rl_dir RL-MACPO/output_runs25
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NPROC="${NPROC:-20}"

MACPO_BIN="${ROOT}/MACPO_sourcecode/build/MACPO_source"
RL_BIN="${ROOT}/RL-MACPO/build/MACPO_simplified"
MACPO_OUT="${ROOT}/MACPO_sourcecode/output_runs25"
RL_OUT="${ROOT}/RL-MACPO/output_runs25"

for b in "$MACPO_BIN" "$RL_BIN"; do
  if [[ ! -x "$b" ]]; then
    echo "Build missing: $b" >&2
    exit 1
  fi
done

mkdir -p "$MACPO_OUT" "$RL_OUT"

TIMING_CSV="${MACPO_OUT}/timing_wallclock_s.csv"
echo "func,run_id,algorithm,seconds_wall" > "$TIMING_CSV"

echo "Total jobs: 6 functions × 25 runs × 2 algorithms = 300 MPI runs"
echo "MACPO -> $MACPO_OUT"
echo "RL    -> $RL_OUT"
echo "Wall-clock log -> $TIMING_CSV"

for F in F1 F2 F3 F4 F5 F6; do
  for i in $(seq 1 25); do
    printf -v RID 'run%02d' "$i"
    echo "======== MACPO ${F} ${RID} ========"
    t0=$(date +%s)
    (cd "${ROOT}/MACPO_sourcecode" && mpirun --oversubscribe -n "$NPROC" \
      "$MACPO_BIN" "$F" "$RID" LLSO "${MACPO_OUT}/")
    t1=$(date +%s)
    echo "${F},${RID},MACPO,$((t1 - t0))" >> "$TIMING_CSV"
    echo "======== RL-MACPO ${F} ${RID} ========"
    t0=$(date +%s)
    (cd "${ROOT}/RL-MACPO" && mpirun --oversubscribe -n "$NPROC" \
      "$RL_BIN" "$F" "$RID" Full "${RL_OUT}/")
    t1=$(date +%s)
    echo "${F},${RID},RL-MACPO,$((t1 - t0))" >> "$TIMING_CSV"
  done
done

cp "$TIMING_CSV" "${RL_OUT}/timing_wallclock_s.csv"

echo "Done 300 runs."
echo "Plot: python3 ${ROOT}/scripts/plot_fes_by_function.py --n_runs 25 \\"
echo "        --macpo_dir ${MACPO_OUT} --rl_dir ${RL_OUT}"
