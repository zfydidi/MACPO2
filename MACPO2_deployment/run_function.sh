#!/bin/bash
# 运行指定函数的实验
# 用法: ./run_function.sh <METHOD> <FUNC> [NUM_RUNS]
# 示例: ./run_function.sh CSO F1 50
#       ./run_function.sh LLSO F3 25

METHOD=${1:-CSO}
FUNC=${2:-F1}
NUM_RUNS=${3:-50}
NUM_PROCS=20

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OUTPUT_DIR="$SCRIPT_DIR/output"
LOG_DIR="$SCRIPT_DIR/log"

mkdir -p "$OUTPUT_DIR/$METHOD"
mkdir -p "$LOG_DIR"

# 检查编译
if [ ! -f "$BUILD_DIR/MACPO2_$METHOD" ]; then
    echo "错误：请先运行 ./install.sh 编译项目"
    exit 1
fi

echo "========================================="
echo "  MACPO2 实验"
echo "  方法: $METHOD"
echo "  函数: $FUNC"
echo "  运行次数: $NUM_RUNS"
echo "========================================="

START_TIME=$(date +%s)

for RUN in $(seq 1 $NUM_RUNS); do
    EXP_ID="exp$(printf '%02d' $RUN)"
    
    echo -n "[$RUN/$NUM_RUNS] $METHOD $FUNC $EXP_ID ... "
    
    mpirun --oversubscribe -n $NUM_PROCS \
        "$BUILD_DIR/MACPO2_$METHOD" "$FUNC" "$EXP_ID" \
        > "$LOG_DIR/${METHOD}_${FUNC}_${EXP_ID}.log" 2>&1
    
    # 移动输出文件
    if [ -f "$SCRIPT_DIR/../output/${FUNC}_${METHOD}_${EXP_ID}.txt" ]; then
        mv "$SCRIPT_DIR/../output/${FUNC}_${METHOD}_${EXP_ID}.txt" \
           "$OUTPUT_DIR/$METHOD/${FUNC}_${EXP_ID}.txt"
    fi
    
        # 显示结果
        RESULT=$(grep -oP 'final fitness=\K[0-9.e+\-]+' "$LOG_DIR/${METHOD}_${FUNC}_${EXP_ID}.log" 2>/dev/null)
        TIME=$(grep -oP 'total time=\K[0-9]+' "$LOG_DIR/${METHOD}_${FUNC}_${EXP_ID}.log" 2>/dev/null)
        echo "fitness=$RESULT (${TIME}ms)"
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "========================================="
echo "  完成！用时: ${ELAPSED}秒"
echo "========================================="

# 统计结果
echo ""
echo "=== $METHOD $FUNC 统计结果 ==="
python3 - <<EOF
import numpy as np

results = []
for i in range(1, $NUM_RUNS + 1):
    log_file = "$LOG_DIR/${METHOD}_${FUNC}_exp{:02d}.log".format(i)
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if 'final fitness' in line:
                    val = float(line.split('=')[-1].strip().replace(',', ''))
                    results.append(val)
                    break
    except:
        pass

if results:
    arr = np.array(results)
    print(f"样本数: {len(arr)}")
    print(f"平均值: {np.mean(arr):.6e}")
    print(f"标准差: {np.std(arr):.6e}")
    print(f"最小值: {np.min(arr):.6e}")
    print(f"最大值: {np.max(arr):.6e}")
    print(f"中位数: {np.median(arr):.6e}")
else:
    print("无有效结果")
EOF

