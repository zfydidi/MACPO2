# 高优 + 中优实验补跑 Runbook

## 一键入口

```bash
cd /Users/zhangyingjie/Project/MACPO2
bash scripts/run_priority_experiments.sh {ci|comm25|dpso25|masoie25|ieee118|apps25|scale25|timing|aggregate|all}
```

日志目录：`logs/priority_experiments/*.log`

## 任务清单

| 优先级 | 任务 | 命令 | 输出 |
|--------|------|------|------|
| 高 | CI 条件触发统计 | `bash scripts/run_priority_experiments.sh ci` | `media/ci_bin_trigger_F1_F6.{pdf,json,txt}` |
| 高 | IEEE118 K=2 重跑 | `MACPO_FAILSAFE_K=2 bash ... ieee118` | `power_dispatch_sim/output/power_IEEE118_*` |
| 高 | MASOIE 外部基线 F1–F6×25 | `bash ... masoie25` | `media/masoie_maes_f1f6.json` |
| 高 | DPSO 外部基线 F1–F6×25 | `bash ... dpso25` | `ablation_experiments/results/external_baselines_25runs_unified/` |
| 中 | 通信基线 10→25 | `bash ... comm25` | `media/comm_baselines_f1_f6.json` |
| 中 | 应用案例 10→25 | `bash ... apps25` | `power_dispatch_sim/output/maed_*`, `paper_*` |
| 中 | 可扩展性 F1S50/F1S100→25 | `bash ... scale25` | `media/scalability_chain.json` |
| 中 | Wall-time 可复现 | `bash ... timing` | `media/wall_time_f1_f6_summary.json` |

## MAES-CCSA 说明

公开仓库目前仅提供 **MASOIE** 参考实现（`external_baselines/iamrice_cdo/`）。**MAES-CCSA** 尚无官方开源包；论文中可并列报告 MASOIE + DPSO，并在 limitation 中说明 MAES 待作者发布代码后补跑。

## 汇总

全部跑完后：

```bash
bash scripts/run_priority_experiments.sh aggregate
```

## 当前后台任务监控

```bash
tail -f logs/priority_experiments/comm25.log
tail -f logs/priority_experiments/masoie25.log
tail -f logs/priority_experiments/dpso25.log
tail -f logs/priority_experiments/ieee118_k2.log
```
