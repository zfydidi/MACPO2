#!/usr/bin/env bash
# ============================================================================
# setup.sh — 搭建 IEEE 14-bus 电力调度仿真实验环境
#
# 1. 从主仓库复制 MACPO / RL-MACPO 算法源码（不动原始代码）
# 2. 打入 patches（Benchmarks 虚函数化）
# 3. 复制电力调度场景文件
# 4. 编译
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC_ROOT="$(cd "$ROOT/.." && pwd)"
ALGO="$ROOT/algorithms"

echo "============================================"
echo " IEEE 14-bus 电力调度仿真实验环境搭建"
echo "============================================"
echo "源仓库: $SRC_ROOT"
echo "目标:   $ALGO"
echo ""

# ---- Step 1: 复制算法源码 ----
mkdir -p "$ALGO"

echo "[1/5] 复制 MACPO baseline 源码..."
rsync -a --delete \
  --exclude 'build/' \
  --exclude 'output/' \
  --exclude 'output_*' \
  --exclude '_build_*' \
  --exclude 'cmake-build-*' \
  --exclude '.DS_Store' \
  "$SRC_ROOT/MACPO_sourcecode/" "$ALGO/MACPO_sourcecode/"

echo "[2/5] 复制 RL-MACPO 源码..."
rsync -a --delete \
  --exclude 'build/' \
  --exclude 'output/' \
  --exclude 'output_*' \
  --exclude '_build_*' \
  --exclude 'cmake-build-*' \
  --exclude '.DS_Store' \
  "$SRC_ROOT/RL-MACPO/" "$ALGO/RL-MACPO/"

# ---- Step 2: 打入 patches（虚函数化 Benchmarks.h） ----
echo "[3/5] 应用 patches..."
PATCH_DIR="$ROOT/patches"

# 从 MATPOWER 生成 IEEE 14/30/57/118 电网数据头文件
echo "  生成 IEEE 电网数据 (14/30/57/118)..."
python3 "$ROOT/../utils/ieee_grid_codegen.py"

# 替换 Benchmarks.h 为虚函数版本（两个算法各自一份）
cp "$PATCH_DIR/Benchmarks_virtual.h" "$ALGO/MACPO_sourcecode/Benchmarks/Benchmarks.h"
cp "$PATCH_DIR/Benchmarks_virtual.h" "$ALGO/RL-MACPO/Benchmarks/Benchmarks.h"

# ---- Step 3: 复制场景文件 ----
echo "[4/5] 部署场景文件..."

deploy_scenarios() {
    local dst="$1"
    local entry="$2"
    mkdir -p "$dst/scenarios"
    rsync -a --delete \
        "$ROOT/scenarios/ndo_common/" "$dst/scenarios/ndo_common/"
    rsync -a --delete \
        "$ROOT/scenarios/power_grid/" "$dst/scenarios/power_grid/"
    rsync -a --delete \
        "$ROOT/scenarios/resource_alloc/" "$dst/scenarios/resource_alloc/"
    rsync -a --delete \
        "$ROOT/scenarios/ev_dispatch/" "$dst/scenarios/ev_dispatch/"
    rsync -a --delete \
        "$ROOT/scenarios/maed/" "$dst/scenarios/maed/"
    cp "$ROOT/scenarios/scenario_factory.h" "$dst/scenarios/"
    if [[ -n "$entry" ]]; then
        cp "$entry" "$dst/"
    fi
}

deploy_scenarios "$ALGO/MACPO_sourcecode" "$ROOT/MACPO_ndo.cpp"
cp "$ROOT/MACPO_power.cpp" "$ALGO/MACPO_sourcecode/"

deploy_scenarios "$ALGO/RL-MACPO" "$ROOT/RL_MACPO_ndo.cpp"
cp "$ROOT/RL_MACPO_power.cpp" "$ALGO/RL-MACPO/"

# ---- Step 4: 追加 CMake 目标（幂等） ----
MARKER="Power Grid Scenario (added by power_dispatch_sim/setup.sh)"
if ! grep -q "$MARKER" "$ALGO/MACPO_sourcecode/CMakeLists.txt" 2>/dev/null; then
    cat >> "$ALGO/MACPO_sourcecode/CMakeLists.txt" <<'EOF'

# === Power Grid Scenario (added by power_dispatch_sim/setup.sh) ===
add_executable(MACPO_power ${MACPO_ROOT}/MACPO_power.cpp ${BENCH_SRC})
target_link_libraries(MACPO_power PRIVATE Eigen3::Eigen MPI::MPI_CXX)
target_include_directories(MACPO_power PRIVATE ${MACPO_ROOT})
EOF
fi

if ! grep -q "$MARKER" "$ALGO/RL-MACPO/CMakeLists.txt" 2>/dev/null; then
    cat >> "$ALGO/RL-MACPO/CMakeLists.txt" <<'EOF'

# === Power Grid Scenario (added by power_dispatch_sim/setup.sh) ===
add_executable(RL_MACPO_power
    Benchmarks/Benchmarks.cpp
    RL_MACPO_power.cpp
    components/evaluator.cpp
)
target_include_directories(RL_MACPO_power PRIVATE ${MACPO2_ROOT})
target_link_libraries(RL_MACPO_power
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)
EOF
fi

MARKER_NDO="NDO Scenarios (added by power_dispatch_sim/setup.sh)"
if ! grep -q "$MARKER_NDO" "$ALGO/MACPO_sourcecode/CMakeLists.txt" 2>/dev/null; then
    cat >> "$ALGO/MACPO_sourcecode/CMakeLists.txt" <<'EOF'

# === NDO Scenarios (added by power_dispatch_sim/setup.sh) ===
add_executable(MACPO_ndo ${MACPO_ROOT}/MACPO_ndo.cpp ${BENCH_SRC})
target_link_libraries(MACPO_ndo PRIVATE Eigen3::Eigen MPI::MPI_CXX)
target_include_directories(MACPO_ndo PRIVATE ${MACPO_ROOT})
EOF
fi

if ! grep -q "$MARKER_NDO" "$ALGO/RL-MACPO/CMakeLists.txt" 2>/dev/null; then
    cat >> "$ALGO/RL-MACPO/CMakeLists.txt" <<'EOF'

# === NDO Scenarios (added by power_dispatch_sim/setup.sh) ===
add_executable(RL_MACPO_ndo
    Benchmarks/Benchmarks.cpp
    RL_MACPO_ndo.cpp
    components/evaluator.cpp
)
target_include_directories(RL_MACPO_ndo PRIVATE ${MACPO2_ROOT})
target_link_libraries(RL_MACPO_ndo
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)
EOF
fi

# ---- Step 5: 编译 ----
echo "[5/5] 编译..."

echo "  编译 MACPO (power + ndo)..."
mkdir -p "$ALGO/MACPO_sourcecode/build"
(cd "$ALGO/MACPO_sourcecode/build" && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4 MACPO_power MACPO_ndo) || {
    echo "ERROR: MACPO 编译失败，请检查依赖 (Eigen3, MPI)"
    exit 1
}

echo "  编译 RL-MACPO (power + ndo)..."
mkdir -p "$ALGO/RL-MACPO/build"
(cd "$ALGO/RL-MACPO/build" && cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4 RL_MACPO_power RL_MACPO_ndo) || {
    echo "ERROR: RL-MACPO 编译失败，请检查依赖 (Eigen3, MPI)"
    exit 1
}

# ---- 检查依赖 ----
echo ""
echo "=== 环境检查 ==="
echo "MPI:"
if command -v mpirun >/dev/null 2>&1; then
    mpirun --version 2>&1 | head -1 || echo "  (found)"
else
    echo "  WARNING: 未检测到 mpirun"
fi

echo "Eigen3:"
if [ -d /usr/local/include/eigen3 ] || [ -d /usr/include/eigen3 ] || \
   [ -d /opt/homebrew/include/eigen3 ] || [ -d "$(brew --prefix eigen 2>/dev/null)/include/eigen3" ]; then
    echo "  (found)"
else
    echo "  WARNING: 未检测到 Eigen3，请 brew install eigen"
fi

echo ""
echo "============================================"
echo " 搭建完成!"
echo ""
echo " 附录 V/VI 多场景实验:"
echo "   bash $ROOT/scripts/run_paper_scenarios.sh 5"
echo ""
echo ""
echo " MAED 阀点经济调度:"
echo "   bash $ROOT/scripts/run_maed.sh 3"
echo "   MAED_LOAD_MW=2520 bash $ROOT/scripts/run_maed.sh 3"
echo ""
echo " IEEE 标准算例 (14/30/57/118):"
echo "   bash $ROOT/scripts/run_power.sh IEEE14 5 paired"
echo "   bash $ROOT/scripts/run_power.sh ALL 5 paired"
echo "============================================"
