#!/bin/bash
# 运行原始 MACPO 25 次，输出到 MACPO_original_output
# 用法: bash scripts/run_macpo_original.sh [LLSO|CSO]

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MACPO_SRC="${PROJECT_ROOT}/MACPO_sourcecode"
OUT_BASE="${PROJECT_ROOT}/MACPO_original_output"
N_RUNS=25
OPTIMIZER="${1:-LLSO}"

FUNCS="F1 F2 F3 F4 F5 F6"
OUT_DIR="${OUT_BASE}/${OPTIMIZER}_25runs"
mkdir -p "$OUT_DIR"
mkdir -p "${MACPO_SRC}/output"

# 查找可执行文件
for exe in "${MACPO_SRC}/MACPO" "${MACPO_SRC}/build/MACPO_source" "${MACPO_SRC}/build/MACPO" "${MACPO_SRC}/cmake-build-debug/MACPO"; do
    if [ -f "$exe" ]; then EXE="$exe"; break; fi
done
if [ -z "$EXE" ]; then
    echo "编译 MACPO..."
    (cd "$MACPO_SRC" && mkdir -p build && cd build && cmake .. && make -j4) 2>/dev/null || true
    EXE="${MACPO_SRC}/build/MACPO_source"
    [ -f "$EXE" ] || EXE="${MACPO_SRC}/build/MACPO"
fi
[ -f "$EXE" ] || { echo "错误: 未找到 MACPO 可执行文件"; exit 1; }

WORK_DIR="$(dirname "$EXE")"
echo "MACPO: $EXE, 优化器: $OPTIMIZER, 运行: $N_RUNS 次"

for F in $FUNCS; do
    OUT_FILE="${OUT_DIR}/${F}_MACPO_${OPTIMIZER}_25runs.txt"
    echo "# Config: 原始MACPO_${OPTIMIZER}, Function: ${F}, Runs: ${N_RUNS}" > "$OUT_FILE"
    success=0
    for r in $(seq 1 $N_RUNS); do
        run_id=$(printf "run%02d" $r)
        tmp_out="${WORK_DIR}/output/${F}_${OPTIMIZER}_${run_id}.txt"
        exe_name=$(basename "$EXE")
        if (cd "$WORK_DIR" && mpirun --oversubscribe -n 20 ./"$exe_name" "$F" "$run_id" "$OPTIMIZER" 2>/dev/null); then
            if [ -f "$tmp_out" ]; then
                final_fit=$(grep "final fitness" "$tmp_out" 2>/dev/null | grep -oE '[0-9.e+-]+' | head -1)
                if [ -z "$final_fit" ]; then
                    final_fit=$(grep -v "^#" "$tmp_out" | tail -1 | awk '{print $3}')
                fi
                if [ -n "$final_fit" ]; then
                    echo "Run_${r}: Completed [${OPTIMIZER}]: final fitness=${final_fit}" >> "$OUT_FILE"
                    success=$((success+1))
                fi
            fi
        fi
    done
    echo "  [$success/$N_RUNS] 原始MACPO $OPTIMIZER $F"
    # 复制到 MACPO_original_output
    for tf in "${WORK_DIR}"/output/${F}_${OPTIMIZER}_*.txt; do
        [ -f "$tf" ] && cp "$tf" "$OUT_DIR/" 2>/dev/null || true
    done
done
echo "输出: $OUT_DIR"
