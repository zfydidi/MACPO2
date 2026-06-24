# MAED — 多区域经济调度（连续 + 阀点效应）

## 场景 ID

| ID | MPI 进程 | 说明 |
|----|----------|------|
| `MAED13` | 1 | 经典 13 机组 VPE-ED（单区，验证非凸搜索） |
| `MAED2` | 2 | 13 机组拆为 2 区 + 联络线（验证多智能体） |

## 成本函数

\[
C(P) = aP^2 + bP + c + \big| e\sin(f(P_{\min}-P)) \big|
\]

实现：`maed_vpe_cost.h`

## 约束（路线 A + MACPO 协商）

- 箱约束：进化中 clamp + 软罚
- 功率平衡：slack 机组修复 + `maed_balance_penalty`
- 联络线容量：\(\lambda[\max(0,|T|-T^{\max})]^2\)（仅 `MAED2`）
- 联络线一致性 \(T_{01}=-T_{10}\)：MACPO 共享维协商 + 惩罚评估器

## 环境变量

- `MAED_LOAD_MW`：总负荷，默认 `1800`（可设 `2520`）

## 实现要点

- 可行初值：`maed_init_dispatch.h`（按容量比例分摊 + slack 修复）
- 多区评估：`maed_area_redispatch.h`（按 `D + net_tie` 再分配，避免仅调 slack 导致巨额平衡罚）
- 联络线：评估时裁剪到 `±T_max`

## 运行

```bash
cd power_dispatch_sim
bash setup.sh

# 单场景调试
export MACPO_PAIR_SEED=42 MAED_LOAD_MW=1800
mpirun -n 1 ./algorithms/MACPO_sourcecode/build/MACPO_ndo MAED13 LLSO ./output/
mpirun -n 2 ./algorithms/MACPO_sourcecode/build/MACPO_ndo MAED2 LLSO ./output/

# 配对实验
bash scripts/run_maed.sh 3
```

## 文件

```
scenarios/maed/
  maed_vpe_cost.h           # 阀点成本
  maed_balance_repair.h     # 平衡修复
  maed_13gen_data.h         # 13 机组参数表
  maed_2area_data.h         # 2 区划分 + 联络线
  MaedSingleAreaBenchmarks.h
  MaedMultiAreaBenchmarks.h
```
