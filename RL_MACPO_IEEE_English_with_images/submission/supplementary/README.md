# Supplementary Material — Conflict-Triggered Communication (MACPO Platform)

This archive supports reproduction and audit of the manuscript **`conference_new_ready.tex`**.

## Contents

```
supplementary/
├── README.md                 (this file)
├── EXPERIMENT_DATA_MAP.md    (paper table → local path index)
├── config/
│   └── headline_gate_defaults.json
├── seeds/
│   └── paired_seed_protocol.md
├── json/                     (table/figure summary statistics)
├── scripts/                  (aggregation & table patch scripts)
├── utils/                    (shared statistics helpers)
└── sample_logs/              (representative raw trajectories)
```

## Headline experimental configuration

| Item | Value |
|------|-------|
| RL-MACPO config name | `Selection_0.9_0.7_0.5` |
| Gate defaults | See `config/headline_gate_defaults.json` (= Table `tab:gate_defaults`) |
| Paired seeds | `MACPO_PAIR_SEED = run_id` (1…25); see `seeds/paired_seed_protocol.md` |
| Optimizer (primary) | LLSO |
| Runs (main tables) | 25 paired independent runs |
| Fail-safe $K$ | 10 (F1–F18 headline); $K=2$ (IEEE 30/57/118 pilots) |

## Regenerating paper tables

From repository root (`MACPO2/`):

```bash
# F1–F6 main table JSON
python3 scripts/patch_conference_table_f1_f6.py

# F7–F18 extension
python3 scripts/patch_conference_table_f7_f18.py

# Communication trigger rates F1–F18
bash scripts/run_comm_rate_f1_f18.sh   # or python3 scripts/aggregate_comm_rate_f1_f18.py

# Penalty controller F3/F5
bash scripts/run_penalty_controller_f3_f5.sh

# Appendix A drift stats
python3 -m utils.per_loop_drift_stats

# Appendix C application run stats
python3 -m utils.application_appendix_stats

# λ sensitivity (already run; JSON in json/)
# python3 scripts/run_lambda_sensitivity_f3_f5.py
```

Outputs land in `RL_MACPO_IEEE_English_with_images/media/*.json` (copied into `json/` here).

## Raw log locations (full archive)

Full 25-run logs are **not** duplicated in this zip when large; paths are indexed in `EXPERIMENT_DATA_MAP.md`. Key directories:

| Experiment | Path (under repo root) |
|------------|------------------------|
| F1–F6 MACPO LLSO | `MACPO_original_output/LLSO_25runs/` |
| F1–F6 RL-MACPO LLSO | `ablation_experiments/Exp4_Variable_Selection/MACPO2_WithSelection_0.9_0.7_0.5/output/` |
| F7–F18 RL-MACPO | `MACPO2_deployment/output/LLSO/F*/` |
| Comm rate F1–F18 | `ablation_experiments/results/comm_rate_f1_f18/` |
| IEEE pilots | `power_dispatch_sim/output/power_IEEE30_20260630_114805/` etc. |

## Contact

Corresponding author: Xiao-Min Hu (xmhu@gdut.edu.cn)
