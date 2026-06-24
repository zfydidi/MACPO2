#!/usr/bin/env bash
# 将 RL-MACPO 最新源码同步到本部署目录（macOS/Linux）。
# 在 MACPO2 仓库根目录执行: bash MACPO2_deployment/sync_from_RL-MACPO.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/RL-MACPO"
DST="$ROOT/MACPO2_deployment"

if [[ ! -d "$SRC" ]]; then
  echo "Missing: $SRC"
  exit 1
fi

cp -f "$SRC/MACPO_simplified.cpp" "$DST/MACPO_LLSO.cpp"
cp -f "$SRC/MACPO_CSO_properly_fixed.cpp" "$DST/MACPO_CSO.cpp"
cp -f "$SRC/Benchmarks/Benchmarks.cpp" "$SRC/Benchmarks/Benchmarks.h" "$SRC/Benchmarks/BaseFunction.h" "$DST/Benchmarks/"
mkdir -p "$DST/Benchmarks/util"
[[ -f "$SRC/Benchmarks/util/json.hpp" ]] && cp -f "$SRC/Benchmarks/util/json.hpp" "$DST/Benchmarks/util/"
cp -f "$SRC/components/"*.cpp "$SRC/components/"*.h "$DST/components/"

# 部署工程使用 "Benchmarks/..." 而非 "./Benchmarks/..."
sed -i '' 's|"./Benchmarks/|"Benchmarks/|g; s|"./components/|"components/|g' "$DST/MACPO_LLSO.cpp" "$DST/MACPO_CSO.cpp" 2>/dev/null \
  || sed -i 's|"./Benchmarks/|"Benchmarks/|g; s|"./components/|"components/|g' "$DST/MACPO_LLSO.cpp" "$DST/MACPO_CSO.cpp"

echo "OK: synced $SRC -> $DST (remember to rebuild on Windows/Linux)."
