#!/usr/bin/env bash
# 高优 + 中优实验批量补跑（Mac / WSL 通用）
#
# 用法:
#   bash scripts/run_priority_experiments.sh ci          # 仅 CI 后处理
#   bash scripts/run_priority_experiments.sh comm25      # 通信基线 11-25
#   bash scripts/run_priority_experiments.sh dpso25      # DPSO 外部基线
#   bash scripts/run_priority_experiments.sh masoie25    # MASOIE F1-F6
#   bash scripts/run_priority_experiments.sh ieee118     # IEEE118 K=2 重跑
#   bash scripts/run_priority_experiments.sh apps25      # 应用案例补到 25
#   bash scripts/run_priority_experiments.sh scale25      # F1S50/F1S100 补到 25
#   bash scripts/run_priority_experiments.sh timing       # wall-time 提取
#   bash scripts/run_priority_experiments.sh aggregate   # 汇总 JSON + patch tex
#   bash scripts/run_priority_experiments.sh all          # 顺序跑全部（极耗时）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs/priority_experiments"
mkdir -p "$LOG_DIR"

run_ci() {
  python3 scripts/plot_ci_bin_trigger.py \
    --runs-dir experiments/patent_paired_comparison/raw/RL-MACPO \
    --functions F1 F2 F3 F4 F5 F6 --exclude-iter0 \
    --out RL_MACPO_IEEE_English_with_images/media/ci_bin_trigger_F1_F6.pdf
  python3 scripts/export_ci_bin_trigger_json.py --exclude-iter0
}

run_comm25() {
  python3 scripts/run_comm_baselines.py \
    --runs 25 --skip-existing \
    --output-dir "$ROOT/RL-MACPO/output" \
    --funcs F1,F2,F3,F4,F5,F6 \
    --methods Full,PeriodicK2,PeriodicK3,PeriodicK5,FixedThreshold,FixedThresholdNoFailSafe,RelativeThresholdFailSafe
  python3 scripts/merge_comm_baselines_json.py
}

run_dpso25() {
  python3 ablation_experiments/scripts/run_external_baselines_f1f6.py \
    --runs 25 --methods DPSO --resume
}

run_masoie25() {
  python3 scripts/run_masoie_maes_baselines.py --runs 25 --resume
}

run_ieee118() {
  export MACPO_FAILSAFE_K=2
  cmake --build power_dispatch_sim/algorithms/RL-MACPO/build -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)" 2>/dev/null || \
    cmake --build power_dispatch_sim/algorithms/RL-MACPO/build -j4
  bash power_dispatch_sim/scripts/run_power.sh IEEE118 25 paired
}

run_apps25() {
  export MACPO_FAILSAFE_K=2
  cmake --build power_dispatch_sim/algorithms/RL-MACPO/build -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)" 2>/dev/null || true
  bash power_dispatch_sim/scripts/run_maed.sh 25
  bash power_dispatch_sim/scripts/run_paper_scenarios.sh 25
}

run_scale25() {
  python3 -c "from utils.chain_benchmark_codegen import ensure_scalability_benchmarks; print(ensure_scalability_benchmarks())"
  python3 scripts/run_scalability_experiments.py \
    --runs 25 --skip-existing \
    --benchmarks F1S50,F1S100 \
    --output-dir "$ROOT/RL-MACPO/output1/output"
}

run_timing() {
  python3 scripts/extract_timing_from_run_logs.py \
    --macpo_dir MACPO_original_output/LLSO_25runs \
    --rl_dir ablation_experiments/Exp4_Variable_Selection/MACPO2_WithSelection_0.9_0.7_0.5/output \
    --out RL_MACPO_IEEE_English_with_images/media/wall_time_f1_f6_from_logs.csv
  python3 scripts/patch_conference_timing_table.py || true
}

run_aggregate() {
  python3 scripts/merge_comm_baselines_json.py
  python3 scripts/run_periodic_baseline.py --aggregate-only --runs 25 2>/dev/null || true
  python3 scripts/run_scalability_experiments.py --aggregate-only --runs 25 \
    --benchmarks F1,F7,F13,F1S50,F1S100 \
    --output-dir "$ROOT/RL-MACPO/output1/output"
  python3 scripts/run_masoie_maes_baselines.py --aggregate-only --runs 25
  python3 scripts/patch_conference_comm_policy.py 2>/dev/null || true
  python3 scripts/patch_conference_application_section.py 2>/dev/null || true
  echo "Aggregate complete. Check RL_MACPO_IEEE_English_with_images/media/*.json"
}

TASK="${1:-help}"
case "$TASK" in
  ci) run_ci ;;
  comm25) run_comm25 ;;
  dpso25) run_dpso25 ;;
  masoie25) run_masoie25 ;;
  ieee118) run_ieee118 ;;
  apps25) run_apps25 ;;
  scale25) run_scale25 ;;
  timing) run_timing ;;
  aggregate) run_aggregate ;;
  all)
    run_ci
    run_comm25
    run_dpso25
    run_masoie25
    run_ieee118
    run_apps25
    run_scale25
    run_timing
    run_aggregate
    ;;
  *)
    echo "Usage: bash scripts/run_priority_experiments.sh {ci|comm25|dpso25|masoie25|ieee118|apps25|scale25|timing|aggregate|all}"
    exit 1
    ;;
esac
