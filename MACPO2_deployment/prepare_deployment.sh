#!/bin/bash
# 准备 MACPO2 部署包

SRC_DIR="/Users/zhangyingjie/CLionProjects/MACPO2"
DEST_DIR="$SRC_DIR/MACPO2_deployment"

echo "准备 MACPO2 部署包..."

# 复制 Benchmarks 目录
echo "复制 Benchmarks..."
cp -r "$SRC_DIR/Benchmarks" "$DEST_DIR/"

# 复制 components 目录
echo "复制 components..."
cp -r "$SRC_DIR/components" "$DEST_DIR/"

# 复制 util 目录
echo "复制 util..."
cp -r "$SRC_DIR/util" "$DEST_DIR/"

# 创建 output 目录
mkdir -p "$DEST_DIR/output"

# 设置脚本可执行权限
chmod +x "$DEST_DIR"/*.sh

echo ""
echo "部署包准备完成！"
echo "位置: $DEST_DIR"
echo ""
echo "目录结构:"
find "$DEST_DIR" -maxdepth 2 -type f -name "*.cpp" -o -name "*.sh" -o -name "*.txt" -o -name "*.h" 2>/dev/null | head -30
echo ""
echo "下一步:"
echo "1. 将 MACPO2_deployment 目录复制到目标机器"
echo "2. 在WSL中运行: ./install.sh"
echo "3. 运行实验: ./run_experiments.sh"

