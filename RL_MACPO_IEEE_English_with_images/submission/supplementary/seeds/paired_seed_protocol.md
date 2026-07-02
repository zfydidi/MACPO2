# Paired-Seed Protocol

## NDO benchmark (F1–F18)

- **25 independent runs** per method/function pair.
- **MACPO vs RL-MACPO** use the **same** random seed per run index `run_id ∈ {1,…,25}`.
- Environment variable: `MACPO_PAIR_SEED=<run_id>` (or equivalent init in MACPO launcher scripts).
- Ensures paired Wilcoxon signed-rank tests compare like-for-like initial conditions.

## Application / IEEE pilots

- Script: `power_dispatch_sim/scripts/run_power.sh`, `run_paper_scenarios.sh`, `run_maed.sh`
- Set `MACPO_PAIRED=1` and `MACPO_PAIR_SEED=<seed>` so MACPO and RL-MACPO share initialization per run.
- Documented in `power_dispatch_sim/README.md` and `scripts/run_patent_paired_experiment.py`.

## λ sensitivity (Appendix / Table tab:lambda_sensitivity)

- 10 runs per λ setting on F3/F5.
- Uses `MACPO_PAIR_SEED` matched across λ values for the same run index where applicable.
- Config: `Selection_0.9_0.7_0.5`, fail-safe `K=10`.

## What we do *not* claim

- Seeds are **not** a hyperparameter sweep; they are independent replication draws.
- External baselines (GFPDO†, DPSO†, MASOIE) use their own run protocols as noted in table captions.
