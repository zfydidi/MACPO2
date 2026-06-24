#!/bin/bash
# MACPO2 安装脚本
# 在 WSL 原生目录编译，但支持在 Windows 目录运行

echo "========================================="
echo "  MACPO2 安装脚本"
echo "========================================="

CURRENT_DIR="$(pwd)"
WSL_BUILD_DIR="$HOME/MACPO2_build"

# 检查是否在 /mnt/ 目录（Windows分区）
if [[ "$CURRENT_DIR" == /mnt/* ]]; then
    echo ""
    echo "检测到项目在 Windows 分区: $CURRENT_DIR"
    echo "将在 WSL 原生目录编译，但保留项目在原位置运行"
    echo ""
    
    # 复制到 WSL 原生目录用于编译
    echo ">>> 复制源码到 $WSL_BUILD_DIR 进行编译..."
    rm -rf "$WSL_BUILD_DIR"
    mkdir -p "$WSL_BUILD_DIR"
    cp -r "$CURRENT_DIR"/* "$WSL_BUILD_DIR/"
    
    # 在 WSL 目录编译
    cd "$WSL_BUILD_DIR"
fi

# 检查并安装依赖
echo "[1/3] 检查依赖..."

if ! command -v mpicxx &> /dev/null; then
    echo "安装 OpenMPI..."
    sudo apt-get update
    sudo apt-get install -y libopenmpi-dev openmpi-bin
fi

if ! dpkg -s libeigen3-dev &> /dev/null 2>&1; then
    echo "安装 Eigen3..."
    sudo apt-get install -y libeigen3-dev
fi

if ! command -v cmake &> /dev/null; then
    echo "安装 CMake..."
    sudo apt-get install -y cmake build-essential
fi

pip3 install numpy --quiet 2>/dev/null || true

echo "依赖检查完成！"

# 编译
echo "[2/3] 编译项目..."
rm -rf build
mkdir -p build
cd build
cmake ..
make -j$(nproc)
BUILD_STATUS=$?
cd ..

if [ $BUILD_STATUS -eq 0 ]; then
    echo ""
    echo "[3/3] 编译成功！"
    
    # 如果是从 Windows 目录启动，复制编译结果回去
    if [[ "$CURRENT_DIR" == /mnt/* ]]; then
        echo ""
        echo ">>> 复制编译结果回 Windows 目录..."
        cp -r build "$CURRENT_DIR/"
        
        echo ""
        echo "========================================="
        echo "  编译完成！"
        echo "  项目位置: $CURRENT_DIR"
        echo "  可执行文件: $CURRENT_DIR/build/"
        echo ""
        echo "  现在可以在原目录运行："
        echo "  cd $CURRENT_DIR"
        echo "  ./run_group.sh CSO GROUP1 50"
        echo "========================================="
    else
        echo ""
        echo "使用方法："
        echo "  ./run_group.sh CSO GROUP1 50"
        echo "  ./run_function.sh CSO F1 50"
    fi
else
    echo "编译失败！"
    exit 1
fi
