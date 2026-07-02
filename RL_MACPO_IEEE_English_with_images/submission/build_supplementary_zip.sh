#!/usr/bin/env bash
# Build Supplementary.zip for journal submission.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PAPER_ROOT="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$PAPER_ROOT/.." && pwd)"
SUB="$HERE/supplementary"
OUT="$HERE/Supplementary.zip"
STAGING="$HERE/_supplementary_staging"

rm -rf "$STAGING" "$OUT"
mkdir -p "$STAGING"

copy_tree() {
  local src="$1" dst="$2"
  if [[ -d "$src" ]]; then
    mkdir -p "$dst"
    cp -R "$src"/. "$dst"/
  fi
}

cp "$SUB/README.md" "$STAGING/"
cp "$PAPER_ROOT/EXPERIMENT_DATA_MAP.md" "$STAGING/"
cp -R "$SUB/config" "$STAGING/"
cp -R "$SUB/seeds" "$STAGING/"

mkdir -p "$STAGING/json"
cp "$PAPER_ROOT/media/"*.json "$STAGING/json/" 2>/dev/null || true
cp "$PAPER_ROOT/media/wall_time_f1_f6_from_logs.csv" "$STAGING/json/" 2>/dev/null || true

mkdir -p "$STAGING/scripts"
SCRIPTS=(
  patch_conference_table_f1_f6.py
  patch_conference_table_f7_f18.py
  aggregate_comm_rate_f1_f18.py
  run_comm_rate_f1_f18.sh
  run_penalty_controller_f3_f5.sh
  patch_penalty_controller_table.py
  run_lambda_sensitivity_f3_f5.py
  run_masoie_maes_baselines.py
  patch_conference_new_ready_q4.py
  export_ci_bin_trigger_json.py
  plot_ci_bin_trigger.py
  plot_rl_metrics_runs25_by_metric.py
  plot_conflict_alpha_bins.py
)
for f in "${SCRIPTS[@]}"; do
  [[ -f "$REPO_ROOT/scripts/$f" ]] && cp "$REPO_ROOT/scripts/$f" "$STAGING/scripts/"
done

copy_tree "$REPO_ROOT/utils" "$STAGING/utils"

mkdir -p "$STAGING/sample_logs/f1_f6_rl"
LOG_SRC="$REPO_ROOT/ablation_experiments/Exp4_Variable_Selection/MACPO2_WithSelection_0.9_0.7_0.5/output"
if [[ -d "$LOG_SRC" ]]; then
  for fn in F1 F2 F3; do
    sample="$LOG_SRC/${fn}_LLSO_run01.txt"
    [[ -f "$sample" ]] && cp "$sample" "$STAGING/sample_logs/f1_f6_rl/"
  done
fi

IEEE_SRC="$REPO_ROOT/power_dispatch_sim/output/power_IEEE30_20260630_114805/summary.json"
if [[ -f "$IEEE_SRC" ]]; then
  mkdir -p "$STAGING/sample_logs/ieee"
  cp "$IEEE_SRC" "$STAGING/sample_logs/ieee/IEEE30_summary.json"
fi

(cd "$STAGING" && zip -r "$OUT" .)
rm -rf "$STAGING"

echo "Created $OUT ($(du -h "$OUT" | cut -f1))"
