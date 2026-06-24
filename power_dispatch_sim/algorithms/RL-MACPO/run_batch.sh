#!/bin/bash
# MACPO2批量运行脚本 - 在一台机器上运行100次实验

set -e

# 检查参数
if [ $# -lt 3 ]; then
    echo "用法: $0 <算法类型> <功能编号> <进程数> [运行次数]"
    echo "示例: $0 LLSO F1 20 100"
    echo "      $0 CSO F1 20 100"
    echo ""
    echo "算法类型:"
    echo "  LLSO - 使用LLSO优化器"
    echo "  CSO  - 使用CSO优化器"
    echo ""
    echo "可用的测试函数:"
    echo "  F1-F6:   50维问题"
    echo "  F7-F12:  100维问题"
    echo "  F13-F18: 200维问题"
    echo ""
    echo "进程数建议:"
    echo "  - 根据问题规模和机器配置选择,例如: 20"
    exit 1
fi

ALGORITHM=$1
FUNC_ID=$2
NUM_PROCS=$3
NUM_RUNS=${4:-100}  # 默认100次

# 根据算法类型选择可执行文件
if [ "${ALGORITHM}" == "LLSO" ]; then
    EXECUTABLE="MACPO_simplified"
elif [ "${ALGORITHM}" == "CSO" ]; then
    EXECUTABLE="MACPO_CSO_properly_fixed"
else
    echo "错误: 未知的算法类型 '${ALGORITHM}'"
    echo "请使用 'LLSO' 或 'CSO'"
    exit 1
fi

# 检查可执行文件
if [ ! -f "/workspace/build/${EXECUTABLE}" ]; then
    echo "错误: 找不到可执行文件 ${EXECUTABLE}"
    echo "请先运行 ./build.sh 构建项目"
    exit 1
fi

# 创建输出目录
OUTPUT_DIR="/workspace/output"
mkdir -p ${OUTPUT_DIR}

# 总结文件
TOTAL_FILE="${OUTPUT_DIR}/${FUNC_ID}_${ALGORITHM}_total.txt"

# 初始化总结文件 - 写入表头
echo "# Algorithm: ${ALGORITHM}" > ${TOTAL_FILE}
echo "# Function: ${FUNC_ID}" >> ${TOTAL_FILE}
echo "" >> ${TOTAL_FILE}

# 表头: run generation evaluation f f(pure) time (Tab分隔)
echo -e "run\tgeneration\tevaluation\tf\tf(pure)\ttime" >> ${TOTAL_FILE}

echo ""
echo "========================================"
echo "批量运行 MACPO2"
echo "========================================"
echo "算法类型: ${ALGORITHM}"
echo "功能编号: ${FUNC_ID}"
echo "进程数: ${NUM_PROCS}"
echo "运行次数: ${NUM_RUNS}"
echo "可执行文件: ${EXECUTABLE}"
echo "输出目录: ${OUTPUT_DIR}"
echo "总结文件: ${TOTAL_FILE}"
echo ""

# 初始化统计变量
declare -a f_pure_array
declare -a f_penalty_array
declare -a time_array

# 循环运行
for i in $(seq 1 ${NUM_RUNS}); do
    EX_ID=$(printf "ex%02d" $i)
    
    echo "----------------------------------------"
    echo "[${i}/${NUM_RUNS}] 运行实验: ${EX_ID}"
    echo "----------------------------------------"
    
    # 记录开始时间(秒)
    START_TIME=$(date +%s)
    
    # 运行实验
    cd /workspace/build
    
    # 运行MPI程序,传入funcID和exID
    mpirun --allow-run-as-root \
           --mca btl_vader_single_copy_mechanism none \
           --oversubscribe \
           -n ${NUM_PROCS} \
           ./${EXECUTABLE} ${FUNC_ID} ${EX_ID} > /dev/null 2>&1
    
    # 记录结束时间
    END_TIME=$(date +%s)
    ELAPSED_TIME=$((END_TIME - START_TIME))
    
    # 从生成的输出文件中提取数据
    RESULT_FILE="${OUTPUT_DIR}/${FUNC_ID}_${ALGORITHM}_${EX_ID}.txt"
    
    if [ -f "${RESULT_FILE}" ]; then
        # 读取最后一行数据（跳过注释行和表头）
        LAST_DATA=$(grep -v "^#" ${RESULT_FILE} | grep -v "^iter" | tail -n 1)
        
        # 检查是否是数据行（包含Tab分隔的数字）
        if [[ "${LAST_DATA}" == *$'\t'* ]]; then
            # 使用awk提取Tab分隔的字段
            # 格式: iter eval f_penalty f_pure penalty improvement reward conflict weight
            EVALUATION=$(echo "${LAST_DATA}" | awk -F'\t' '{print $2}')
            F_PENALTY=$(echo "${LAST_DATA}" | awk -F'\t' '{print $3}')
            F_PURE=$(echo "${LAST_DATA}" | awk -F'\t' '{print $4}')
            
            # 计算generation (evaluation / swarm_size)
            if [ -n "${EVALUATION}" ] && [ "${EVALUATION}" != "eval" ]; then
                GENERATION=$((EVALUATION / 300))
            else
                GENERATION="N/A"
            fi
        else
            # 如果不是Tab分隔格式，设为N/A
            F_PURE="N/A"
            F_PENALTY="N/A"
            EVALUATION="N/A"
            GENERATION="N/A"
        fi
    else
        echo "  警告: 找不到结果文件 ${RESULT_FILE}"
        F_PURE="N/A"
        F_PENALTY="N/A"
        EVALUATION="N/A"
        GENERATION="N/A"
    fi
    
    # 输出到终端
    echo "  Generation: ${GENERATION}"
    echo "  Evaluation: ${EVALUATION}"
    echo "  F(pure):    ${F_PURE}"
    echo "  F(penalty): ${F_PENALTY}"
    echo "  Time:       ${ELAPSED_TIME}s"
    
    # 写入总结文件 (Tab分隔)
    echo -e "${EX_ID}\t${GENERATION}\t${EVALUATION}\t${F_PENALTY}\t${F_PURE}\t${ELAPSED_TIME}" >> ${TOTAL_FILE}
    
    # 保存到数组用于统计
    if [ "${F_PURE}" != "N/A" ] && [ "${F_PENALTY}" != "N/A" ]; then
        f_pure_array+=("${F_PURE}")
        f_penalty_array+=("${F_PENALTY}")
        time_array+=("${ELAPSED_TIME}")
    fi
    
    echo ""
done

echo "========================================"
echo "所有实验完成,正在计算统计数据..."
echo "========================================"

# 计算统计数据
if [ ${#f_pure_array[@]} -gt 0 ]; then
    # 将数组转换为换行分隔的字符串
    f_pure_str=$(printf "%s\n" "${f_pure_array[@]}")
    f_penalty_str=$(printf "%s\n" "${f_penalty_array[@]}")
    time_str=$(printf "%s\n" "${time_array[@]}")
    
    # 使用Python计算均值和标准差
    STATS=$(python3 <<EOF
import sys
import math

f_pure = [float(x.replace('E','e').replace('+','')) for x in '''${f_pure_str}'''.strip().split('\n') if x]
f_penalty = [float(x.replace('E','e').replace('+','')) for x in '''${f_penalty_str}'''.strip().split('\n') if x]
times = [float(x) for x in '''${time_str}'''.strip().split('\n') if x]

def calc_stats(data):
    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / n
    std = math.sqrt(variance)
    return mean, std

f_penalty_mean, f_penalty_std = calc_stats(f_penalty)
f_pure_mean, f_pure_std = calc_stats(f_pure)
time_mean, time_std = calc_stats(times)

print(f'{f_penalty_mean:.6e} {f_penalty_std:.6e} {f_pure_mean:.6e} {f_pure_std:.6e} {time_mean:.2f}')
EOF
)
    
    read F_PENALTY_MEAN F_PENALTY_STD F_PURE_MEAN F_PURE_STD TIME_MEAN <<< ${STATS}
    
    # 写入总结文件 - 按照要求的格式 (Tab分隔)
    echo "" >> ${TOTAL_FILE}
    echo -e "avg\t-\t-\t${F_PENALTY_MEAN}\t${F_PURE_MEAN}\t${TIME_MEAN}" >> ${TOTAL_FILE}
    echo -e "std\t-\t-\t${F_PENALTY_STD}\t${F_PURE_STD}\t-" >> ${TOTAL_FILE}
    
    # 输出到终端
    echo ""
    echo "统计结果:"
    echo "  F(带惩罚)均值:    ${F_PENALTY_MEAN}"
    echo "  F(带惩罚)标准差:  ${F_PENALTY_STD}"
    echo "  F(纯净)均值:      ${F_PURE_MEAN}"
    echo "  F(纯净)标准差:    ${F_PURE_STD}"
    echo "  平均时间:         ${TIME_MEAN}s"
    echo ""
else
    echo "" >> ${TOTAL_FILE}
    echo "警告: 没有有效的结果数据" >> ${TOTAL_FILE}
fi

echo "========================================"
echo "批量实验完成!"
echo "========================================"
echo "总结文件: ${TOTAL_FILE}"
echo ""
echo "查看结果:"
echo "  cat ${TOTAL_FILE}"
echo ""

