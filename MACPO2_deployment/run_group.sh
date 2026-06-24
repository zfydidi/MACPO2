#!/bin/bash
# 按组运行实验
# 用法: ./run_group.sh <METHOD> <GROUP> [NUM_RUNS]

METHOD=${1:-CSO}
GROUP=${2:-GROUP1}
NUM_RUNS=${3:-50}

# 根据组设置函数和进程数
case $GROUP in
    GROUP1|group1|1)
        FUNCTIONS="F1 F2 F3 F4 F5 F6"
        NUM_PROCS=20
        GROUP_NAME="GROUP1 (F1-F6)"
        ;;
    GROUP2|group2|2)
        FUNCTIONS="F7 F8 F9 F10 F11 F12"
        NUM_PROCS=100
        GROUP_NAME="GROUP2 (F7-F12)"
        ;;
    GROUP3|group3|3)
        FUNCTIONS="F13 F14 F15 F16 F17 F18"
        NUM_PROCS=200
        GROUP_NAME="GROUP3 (F13-F18)"
        ;;
    *)
        echo "未知组: $GROUP"
        echo "可用组: GROUP1 (F1-F6), GROUP2 (F7-F12), GROUP3 (F13-F18)"
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
OUTPUT_DIR="$SCRIPT_DIR/output"
LOG_DIR="$SCRIPT_DIR/log"

# 创建目录
mkdir -p "$OUTPUT_DIR/$METHOD"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# 检查编译
if [ ! -f "$BUILD_DIR/MACPO2_$METHOD" ]; then
    echo "错误：未找到 $BUILD_DIR/MACPO2_$METHOD"
    echo "请先运行 ./install.sh 编译项目"
    exit 1
fi

echo "========================================="
echo "  MACPO2 组实验"
echo "  方法: $METHOD"
echo "  组: $GROUP_NAME"
echo "  函数: $FUNCTIONS"
echo "  每函数运行次数: $NUM_RUNS"
echo "  MPI进程数: $NUM_PROCS"
echo "  工作目录: $SCRIPT_DIR"
echo "========================================="

START_TIME=$(date +%s)

# 切换到项目根目录运行（重要！）
cd "$SCRIPT_DIR"

# 遍历组内函数
for FUNC in $FUNCTIONS; do
    echo ""
    echo ">>> $FUNC <<<"
    
    for RUN in $(seq 1 $NUM_RUNS); do
        EXP_ID="exp$(printf '%02d' $RUN)"
        LOG_FILE="$LOG_DIR/${METHOD}_${FUNC}_${EXP_ID}.log"
        
        echo -n "  [$RUN/$NUM_RUNS] $FUNC $EXP_ID ... "
        
        # 从项目根目录运行，输出到 output/ 目录
        mpirun --oversubscribe -n $NUM_PROCS \
            "./build/MACPO2_$METHOD" "$FUNC" "$EXP_ID" \
            > "$LOG_FILE" 2>&1
        
        EXIT_CODE=$?
        
        # 移动输出文件到方法子目录
        SRC_FILE="$OUTPUT_DIR/${FUNC}_${METHOD}_${EXP_ID}.txt"
        DST_FILE="$OUTPUT_DIR/$METHOD/${FUNC}_${EXP_ID}.txt"
        if [ -f "$SRC_FILE" ]; then
            mv "$SRC_FILE" "$DST_FILE"
        fi
        
        # 显示结果
        if [ $EXIT_CODE -eq 0 ]; then
            # 正确提取 "final fitness=xxx" 中的数值
            RESULT=$(grep -oP 'final fitness=\K[0-9.e+\-]+' "$LOG_FILE" 2>/dev/null)
            TIME=$(grep -oP 'total time=\K[0-9]+' "$LOG_FILE" 2>/dev/null)
            if [ -n "$RESULT" ]; then
                echo "fitness=$RESULT (${TIME}ms)"
            else
                echo "完成"
            fi
        else
            echo "失败 (exit=$EXIT_CODE)"
            tail -3 "$LOG_FILE" 2>/dev/null
        fi
    done
    
    # 该函数统计
    echo ""
    echo "  --- $FUNC 统计 ---"
    python3 - <<EOF 2>/dev/null || echo "  (跳过统计，需要 numpy)"
import numpy as np
results = []
for i in range(1, $NUM_RUNS + 1):
    try:
        with open(f"$LOG_DIR/${METHOD}_${FUNC}_exp{i:02d}.log", 'r') as f:
            for line in f:
                if 'final fitness' in line:
                    val = float(line.split('=')[-1].strip().replace(',', ''))
                    results.append(val)
                    break
    except: pass
if results:
    arr = np.array(results)
    print(f"    样本: {len(arr)}, Mean: {np.mean(arr):.4e}, Std: {np.std(arr):.4e}")
    print(f"    Min: {np.min(arr):.4e}, Max: {np.max(arr):.4e}")
else:
    print("    无有效结果")
EOF
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINS=$((ELAPSED / 60))
SECS=$((ELAPSED % 60))

echo ""
echo "========================================="
echo "  $GROUP_NAME 完成！"
echo "  方法: $METHOD"
echo "  总用时: ${MINS}分${SECS}秒"
echo "  结果目录: $OUTPUT_DIR/$METHOD/"
echo "  日志目录: $LOG_DIR/"
echo "========================================="

# 生成组汇总
echo ""
echo "=== $METHOD $GROUP_NAME 汇总 ==="
python3 - <<EOF 2>/dev/null || echo "(跳过汇总)"
import numpy as np

functions = "$FUNCTIONS".split()
print(f"{'函数':<6} {'Mean':<14} {'Std':<14} {'Min':<14} {'Max':<14}")
print("-" * 62)

for func in functions:
    results = []
    for i in range(1, $NUM_RUNS + 1):
        try:
            with open(f"$LOG_DIR/${METHOD}_{func}_exp{i:02d}.log", 'r') as f:
                for line in f:
                    if 'final fitness' in line:
                        val = float(line.split('=')[-1].strip().replace(',', ''))
                        results.append(val)
                        break
        except: pass
    
    if results:
        arr = np.array(results)
        print(f"{func:<6} {np.mean(arr):<14.6e} {np.std(arr):<14.6e} {np.min(arr):<14.6e} {np.max(arr):<14.6e}")
    else:
        print(f"{func:<6} {'N/A':<14} {'N/A':<14} {'N/A':<14} {'N/A':<14}")

# 保存汇总到文件
with open("$OUTPUT_DIR/${METHOD}_${GROUP}_summary.txt", 'w') as f:
    f.write(f"MACPO2 $METHOD $GROUP_NAME 实验结果\n")
    f.write(f"每函数运行次数: $NUM_RUNS\n")
    f.write("=" * 62 + "\n")
    f.write(f"{'函数':<6} {'Mean':<14} {'Std':<14} {'Min':<14} {'Max':<14}\n")
    for func in functions:
        results = []
        for i in range(1, $NUM_RUNS + 1):
            try:
                with open(f"$LOG_DIR/${METHOD}_{func}_exp{i:02d}.log", 'r') as fi:
                    for line in fi:
                        if 'final fitness' in line:
                            val = float(line.split('=')[-1].strip().replace(',', ''))
                            results.append(val)
                            break
            except: pass
        if results:
            arr = np.array(results)
            f.write(f"{func:<6} {np.mean(arr):<14.6e} {np.std(arr):<14.6e} {np.min(arr):<14.6e} {np.max(arr):<14.6e}\n")
print(f"\n汇总已保存: $OUTPUT_DIR/${METHOD}_${GROUP}_summary.txt")
EOF
