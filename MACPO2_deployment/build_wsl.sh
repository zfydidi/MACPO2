#!/usr/bin/env bash
# WSL / Linux 下一键配置并编译 MACPO2_LLSO、MACPO2_CSO
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

: "${CXX:=mpicxx}"
BUILD_DIR="${BUILD_DIR:-build}"

echo "Using CXX=$CXX"
cmake -S "$ROOT" -B "$BUILD_DIR" -DCMAKE_CXX_COMPILER="$CXX"
cmake --build "$BUILD_DIR" -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

echo ""
echo "OK: $BUILD_DIR/MACPO2_LLSO  $BUILD_DIR/MACPO2_CSO"
echo "Run e.g.: cd $BUILD_DIR && mpirun -n 20 ./MACPO2_LLSO F1 ex01 Full ../output/"
