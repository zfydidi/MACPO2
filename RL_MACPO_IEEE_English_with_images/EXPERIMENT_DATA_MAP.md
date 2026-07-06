# 论文实验条目 → 本地数据文件夹对照表

根目录：`/Users/zhangyingjie/Project/MACPO2/`

> **最后更新**：2026-06-30（IEEE 表已对齐 K=2 重跑批次 `114805` / `114810`）

---

## 一、NDO 主实验（F1–F18，25 runs）

| 论文位置 | 内容 | 原始日志目录 | 汇总/脚本 | 备注 |
|---|---|---|---|---|
| Table `tab:macpo_style_all` | F1–F6 MACPO vs RL-MACPO（LLSO/CSO） | **MACPO LLSO**：`MACPO_original_output/LLSO_25runs/`（`F*_LLSO_run*.txt`）<br>**RL LLSO**：`ablation_experiments/Exp4_Variable_Selection/MACPO2_WithSelection_0.9_0.7_0.5/output/`（`F*_LLSO_run*.txt`）<br>**MACPO CSO**：`ablation_experiments/results/CSO_25runs/MACPO_baseline/`<br>**RL CSO**：`ablation_experiments/results/CSO_25runs/Full/` | `scripts/patch_conference_table_f1_f6.py`<br>→ `RL_MACPO_IEEE_English_with_images/media/table_f1_f6_recomputed.json` | RL Only 行来自 `ablation_experiments/results/Full_System_and_RLonly_LLSO_CSO_25runs/` |
| 同上（外部列） | GFPDO† / DPSO† | **GFPDO（25-run）**：`MACPO_sourcecode/output_baselines_gfpdo_25runs/`<br>**DPSO（25-run）**：`MACPO_sourcecode/output_baselines_dpso_25runs/` | `utils/external_baselines.py` | 缺日志时用文献 fallback |
| Table `tab:f1f6_comm_eva` | F1–F6 通信率 + eva | 与主表同一批 RL 日志；`# COST_STATS` 在轨迹末尾 | `RL_MACPO_IEEE_English_with_images/media/f1f6_comm_eva.json`<br>原始：`ablation_experiments/results/comm_rate_f1_f18/F1_F6/` | 25-run **Full**（Selection_0.9_0.7_0.5） |
| Table `tab:macpo_rl_mean_f1_f18` | F7–F18 fitness | **MACPO**：`MACPO_original_output/LLSO/F*/`、`MACPO_original_output/CSO/F*/`<br>**RL-MACPO**：`MACPO2_deployment/output/LLSO/F*/`、`MACPO2_deployment/output/CSO/F*/` | `scripts/patch_conference_table_f7_f18.py`<br>→ `media/table_f7_f18_recomputed.json` | MACPO 报 penalized endpoint；RL 报末行 `f_pure` |
| Table `tab:wall_time_f1_f18` | F1–F18 墙钟时间 | **论文表内数值为开发机 indicative 测量，硬编码在 tex**； fitness 归档日志大多**未**写入统一 timing 字段 | 部分 F1–F6 pilot：`output/RL-output_runs25/timing_from_logs_s.csv`（**≠ 论文 Table III 数值**） | 见第六节.4 |
| Table `tab:comm_rate_f1_f18` | F1–F18 通信触发率 | `ablation_experiments/results/comm_rate_f1_f18/F1_F6/`<br>`ablation_experiments/results/comm_rate_f1_f18/F7_F18/` | `scripts/run_comm_rate_f1_f18.sh`<br>→ `media/comm_rate_f1_f18.json` | F1–F6：Selection_0.9_0.7_0.5；F7–F18：Full |

---

## 二、曲线与诊断图

| 论文位置 | 内容 | 原始日志目录 | 出图脚本 / PDF |
|---|---|---|---|
| Fig `fig:fes_f1_f6_panel` | F1–F6 FES 收敛（单 run 面板） | 脚本默认：`MACPO_sourcecode/output_runs25/` + `RL-MACPO/output_runs25/`（Mac 上可能不存在）<br>实际可用：`MACPO_original_output/LLSO_25runs/` + `output/RL-output_runs25/` | `scripts/plot_fes_f1_f6_panel.py`<br>→ `RL_MACPO_IEEE_English_with_images/media/F1_F6_panel.pdf` |
| Fig `fig:rl_traj_*` | α / ρ / conflict / reward 轨迹 | `output/RL-output_runs25_rho/`（`F*_LLSO_final_run*.txt`） | `scripts/plot_rl_metrics_runs25_by_metric.py`<br>→ `media/rl_metrics_mean25_rho_*.pdf` |
| Fig `fig:conflict_alpha_bins` | conflict–α 分箱 | 同上 `output/RL-output_runs25_rho/` | `scripts/plot_conflict_alpha_bins.py`<br>→ `media/conflict_alpha_bins_F1_F6.pdf` |
| Fig `fig:f3_f5_micro` | F3/F5 微观诊断 | 单 run 轨迹（通常来自 `output/RL-output_runs25_rho/` 某一 run） | `scripts/plot_f3_f5_conflict_penalty_micro.py`<br>→ `media/f3_f5_conflict_alpha_micro.pdf` |

---

## 三、消融与机制实验

| 论文位置 | 内容 | 原始日志目录 | 汇总 |
|---|---|---|---|
| **Table `tab:penalty_controller_f3_f5`** | F3/F5 penalty controller (MACPO / Fixed / EMA / RL) | **EMA**: `ablation_experiments/results/penalty_controller_f3_f5/EMA_Penalty/`<br>**Fixed**: `.../FixedSchedule/`<br>**RL**: headline `Exp4_.../output/` or `.../Selection_0.9_0.7_0.5/`<br>**MACPO**: `MACPO_original_output/LLSO_25runs/` | `scripts/run_penalty_controller_f3_f5.sh`<br>`utils/penalty_controller_stats.py`<br>`scripts/patch_penalty_controller_table.py` |
| Fig `fig:gating_ablation` | 门控层消融 F1–F6 | `ablation_experiments/results/补做实验_25runs/` | `ablation_experiments/results/汇总对比表.csv` → `media/fig_gating_ablation.pdf` |
| Table `tab:phase_eta` | Phase / η 消融 | 同上 `补做实验_25runs/` | `汇总对比表.csv` |
| Table `tab:deeprl` | 深度 RL 架构对比 | `ablation_experiments/Exp6_DeepRL_WithGating/`、`Exp6_DeepRL_NoGating/` | `汇总对比表.csv` |
| Table `tab:gate_cost_stats` | 门控代价统计（V0–V3） | `ablation_experiments/results/gate_mechanism_minimal/raw/` | `gate_mechanism_minimal_10runs_summary.csv` |
| Table `tab:periodic_baseline` | Periodic-K 基线 | `ablation_experiments/results/periodic_baseline/raw/` | `media/periodic_baseline_f125.json` |
| Table `tab:threshold_baseline` | 阈值触发基线 | `ablation_experiments/results/comm_baselines/raw/` | `media/comm_baselines_f1_f6.json` |
| Table `tab:scalability_chain` | F1/F7/F13 + F1S50/F1S100 | `RL-MACPO/output1/output/` + `ablation_experiments/results/scalability/` | **5-run pilot**，≠ 25-run 主表 |

---

## 四、工程应用实验（`power_dispatch_sim/`）

| 论文位置 | 内容 | **论文当前使用的**输出目录 | 运行脚本 | 索引文件 |
|---|---|---|---|---|
| Table `tab:application_cases` | MAED-13 | `power_dispatch_sim/output/maed_20260622_114525/MAED13/` | `scripts/run_maed.sh` | `patent_supplement/paired_experiment_data.json` |
| 同上 | Resource scheduling | `power_dispatch_sim/output/paper_20260622_114518/RESOURCE/` | `scripts/run_paper_scenarios.sh` | 同上 |
| 同上 | EV dispatch | `power_dispatch_sim/output/paper_20260622_114518/EVDISPATCH/` | 同上 | 同上 |
| Table `tab:ieee_power_cases` | IEEE 30/57/118（**25-run，best-so-far + K=2 fail-safe**） | **`power_dispatch_sim/output/power_IEEE30_20260630_114805/`**<br>**`power_dispatch_sim/output/power_IEEE57_20260630_114810/`**<br>`power_dispatch_sim/output/power_IEEE118_20260630_113148/` | `scripts/run_power.sh IEEE30\|57\|118 25 paired` | 各目录 `summary.json` |

**IEEE 批次说明**

| 目录 | 状态 | 关键指标（RL） |
|---|---|---|
| `114805`（IEEE30） | ✅ **论文采用**（K=2） | comm ≈ 58.6%，mean ≈ 915，drop ≈ −41.4%，**success 23/25**（runs 1/25 离群，comm 同为 58.6%） |
| `114810`（IEEE57） | ✅ **论文采用**（K=2） | comm ≈ 58.8%，median Δ ≈ 0% |
| `113148`（IEEE118） | ✅ **论文采用**（K=3，未重跑） | comm = 40.0%，drop ≈ −60% |
| `113138` / `113144` | ⚠️ 已 superseded | 旧 K=3 批次（best-so-far 修复后、K=2 重跑前）；IEEE30 RL comm ≈ 42.8% |
| `111653` / `111710` / `111720` | ⚠️ 更旧 | 初版 25-run（RL 报告口径 bug 未修） |

---

## 五、论文侧汇总入口

| 用途 | 路径 |
|---|---|
| 论文 LaTeX | `RL_MACPO_IEEE_English_with_images/conference_en_ready.tex` |
| 表格/图 JSON 缓存 | `RL_MACPO_IEEE_English_with_images/media/` |
| 应用实验索引 | `patent_supplement/paired_experiment_data.json` |
| IEEE 实验代码 | `power_dispatch_sim/algorithms/MACPO_sourcecode/`、`power_dispatch_sim/algorithms/RL-MACPO/` |

---

## 六、核对时容易混的几处

1. **F1–F6 RL 主表**在 `Exp4_Variable_Selection/.../output/`，**不是** `MACPO2_deployment/output/`。
2. **F7–F18 RL**在 `MACPO2_deployment/output/`，**不是** Exp4。
3. **Scalability / Periodic / Threshold** 是 5-run 或 10-run pilot，与 25-run 主表不可混读。
4. **IEEE 表**请以 **`114805` / `114810` / `113148`** 为准；**不要**再用 `113138` / `113144`（旧 K=3 批次）。
5. **`output/RL-output_runs25/`** 与 **`output/RL-output_runs25_rho/`** 分别对应 FES 曲线和 RL 轨迹图。

### 6.4 Wall-time（Table III）可复现性

- 论文 Table `tab:wall_time_f1_f18` 的数值**直接写入 tex**，表示开发机上的 **indicative wall-clock**，用于定性说明 RL 推理/门控开销，**不是**从 fitness 归档日志自动重算。
- 主表 fitness 用的 MACPO/RL 轨迹（`MACPO_original_output/`、`Exp4/.../output/`、`MACPO2_deployment/output/`）**大多不含**可解析的 `total time=` / `total_time_ms=` 字段。
- 仓库内有一份 **F1–F6 部分** timing 归档：`output/RL-output_runs25/timing_from_logs_s.csv`（由 `scripts/extract_timing_from_run_logs.py` 从 `F*_LLSO_final_run*.txt` 提取）。该 CSV **与 Table III 数值不一致**（不同跑批/硬件/日志粒度），仅供内部交叉核对，**不能**当作论文表的复现源。
- 若审稿人要求 raw timing：需在新跑批中统一打开 wall-clock 日志，或接受 caption 中的 indicative 措辞。
