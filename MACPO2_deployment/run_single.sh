#!/bin/bash
# 单次运行脚本
# 用法: ./run_single.sh <METHOD> <FUNC> <EXP_ID>
# 示例: ./run_single.sh CSO F1 1

METHOD=${1:-CSO}
FUNC=${2:-F1}
EXP_ID=${3:-1}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# 格式化实验ID
EXP_ID_FMT="exp$(printf '%02d' $EXP_ID)"

echo "运行: MACPO2_$METHOD $FUNC $EXP_ID_FMT"

mpirun --oversubscribe -n 20 "$BUILD_DIR/MACPO2_$METHOD" "$FUNC" "$EXP_ID_FMT"

