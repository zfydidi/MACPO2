#!/usr/bin/env bash
# One pair of curves (MACPO vs RL-MACPO) with identical LLSO initial populations.
# 1) Run MACPO with MACPO_PAIR_INIT_DUMP -> writes rank_0.bin ... rank_{N-1}.bin
# 2) Run RL-MACPO with MACPO_PAIR_INIT_LOAD pointing at the same directory.
#
# Usage from repo root:
#   bash scripts/pair_init_pair_run.sh F1 paper_pair01
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FUNC="${1:-F1}"
EXID="${2:-paper_pair01}"
NPROC="${NPROC:-20}"
# 必须随 FUNC/EXID 变化；不要用环境里残留的 PAIR_DIR 指向旧目录
PAIR_DIR="${ROOT}/pair_init_states/${FUNC}_${EXID}"
# 同一值：保证 DUMP 与 LOAD 两次运行中 LLSO 的 rand() 序列一致（与初值文件配套）
export MACPO_PAIR_SEED="${MACPO_PAIR_SEED:-90001}"

# Prefer freshly built MACPO; fall back to MACPO_source if your tree uses that name.
MACPO_BIN="${MACPO_BIN:-${ROOT}/MACPO_sourcecode/build/MACPO}"
[[ -x "$MACPO_BIN" ]] || MACPO_BIN="${ROOT}/MACPO_sourcecode/build/MACPO_source"
RL_BIN="${RL_BIN:-${ROOT}/RL-MACPO/build/MACPO_simplified}"

for b in "$MACPO_BIN" "$RL_BIN"; do
  if [[ ! -x "$b" ]]; then
    echo "Build missing: $b" >&2
    exit 1
  fi
done

mkdir -p "$PAIR_DIR"

echo "=== Dump initial swarm (MACPO baseline) -> ${PAIR_DIR} (MACPO_PAIR_SEED=${MACPO_PAIR_SEED}) ==="
rm -f "${PAIR_DIR}"/rank_*.bin "${PAIR_DIR}"/global_best_iter0.bin "${PAIR_DIR}"/f_pure_iter0.txt
export MACPO_PAIR_INIT_DUMP="$PAIR_DIR"
unset MACPO_PAIR_INIT_LOAD
(cd "${ROOT}/MACPO_sourcecode" && mpirun --oversubscribe -n "$NPROC" \
  "$MACPO_BIN" "$FUNC" "$EXID" LLSO ./output_fair/)
unset MACPO_PAIR_INIT_DUMP

echo "=== RL-MACPO with same init -> output/F${FUNC}_... ==="
export MACPO_PAIR_INIT_LOAD="$PAIR_DIR"
unset MACPO_PAIR_INIT_DUMP
(cd "${ROOT}/RL-MACPO" && mpirun --oversubscribe -n "$NPROC" \
  "$RL_BIN" "$FUNC" "$EXID" Full)
unset MACPO_PAIR_INIT_LOAD

echo "Done. Traces:"
echo "  MACPO:    ${ROOT}/MACPO_sourcecode/output_fair/${FUNC}_LLSO_${EXID}.txt"
echo "  RL-MACPO: ${ROOT}/RL-MACPO/output/${FUNC}_LLSO_final_${EXID}.txt"
echo "Plot: python3 ${ROOT}/scripts/plot_f1_fes_fair.py --macpo ... --rl ..."
