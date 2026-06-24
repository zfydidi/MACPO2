# MACPO 论文附录 V/VI 配对实验

> 独立项目。专注附录 **V（资源分配）**、**VI（EV 电力调度）**；MACPO 与 RL-MACPO 使用**同一配对协议**对比。

## 统一配对协议（`paired_protocol()`）

| 参数 | 值 | 说明 |
|------|-----|------|
| MPI 进程数 | 10 | 链式 10 节点 |
| 优化器 | LLSO | 两侧一致 |
| `swarm_size` | 100 | 种群规模 |
| `gen_per_d` | 3.0 | 每轮局部进化代数 |
| `eva_per_d` | 20000 | 评估预算系数 × max(区域维度) |
| 惩罚 λ | 1/512 | MACPO 动态 `w=\|f\|/512` |
| 随机种子 | `MACPO_PAIR_SEED` | 同 run 两侧相同 |
| RL 门控 | `MACPO_PAIRED=1` | fail-safe 每 5 轮强制协商 |

## 场景

| 场景 ID | 论文章节 | 目标函数 |
|---------|----------|----------|
| `RESOURCE` | 附录 V 式 (S1) | Σ(Uᵢ−供给)² |
| `EVDISPATCH` | 附录 VI 式 (S2)+Alg.S1 | 发电+交易−EV收益 |

## 快速开始

```bash
cd power_dispatch_sim
bash setup.sh
bash scripts/run_paper_scenarios.sh 5
```

结果：`output/paper_<timestamp>/overview.json`

## 单场景调试

```bash
export MACPO_PAIRED=1 MACPO_PAIR_SEED=42
mpirun -n 10 ./algorithms/MACPO_sourcecode/build/MACPO_ndo RESOURCE LLSO ./output/
mpirun -n 10 ./algorithms/RL-MACPO/build/RL_MACPO_ndo EVDISPATCH Full ./output/
```

## 对比指标

| 指标 | 含义 |
|------|------|
| `f_pure` | 纯目标（`global_fitness`，不计入评估预算） |
| `comm_rate` | 触发协商的外层迭代占比 |
| `eva_count` | 黑盒评估次数（两侧预算一致） |
| `outer_iters` | 外层循环次数 |

---

## IEEE 标准算例（可选，非附录 V/VI）

连续**经济调度 ED**（非博客常见的机组组合 UC）。数据来自 MATPOWER `case14/30/57/118.m`。

| 算例 | MPI 进程 | 发电机 | 决策维 |
|------|----------|--------|--------|
| IEEE14 | 4 | 5 | 9 |
| IEEE30 | 4 | 6 | 9 |
| IEEE57 | 4 | 7 | 11 |
| IEEE118 | 8 | 54 | 65 |

```bash
# 单算例
bash scripts/run_power.sh IEEE30 5 paired

# 四个算例依次跑
bash scripts/run_power.sh ALL 5 paired

# 手动
mpirun -n 4 ./algorithms/MACPO_sourcecode/build/MACPO_power IEEE57 LLSO ./output/
```

重新生成电网数据头文件：`python3 utils/ieee_grid_codegen.py`

| 物理概念 | MACPO 框架映射 |
|----------|---------------|
| 电力控制区域 | MPI Rank (0-3) |
| 区域内发电机出力 | 私有变量 |
| 区域间联络线功率 | 共享（重叠）变量 |
| 发电成本最小化 | 全局目标函数 |
| 联络线功率一致性 | 惩罚项约束 |
| 功率平衡约束 | 评估器内置二次惩罚 |

## IEEE 14-bus 区域划分

```
Region 0 (North):  Buses {1,2,5}        → G1(bus1), G2(bus2)   R0: [P_G1, P_G2, P_tie_01, P_tie_02]
Region 1 (Central): Buses {3,4}         → G3(bus3)              R1: [P_tie_01, P_G3, P_tie_13]
Region 2 (East):   Buses {6,11,12,13}   → G4(bus6)              R2: [P_tie_02, P_G4, P_tie_23]
Region 3 (South):  Buses {7,8,9,10,14}  → G5(bus8)              R3: [P_tie_13, P_tie_23, P_G5]

共享变量（联络线）:
  dim 2: P_tie_01  (R0 ↔ R1)
  dim 3: P_tie_02  (R0 ↔ R2)
  dim 5: P_tie_13  (R1 ↔ R3)
  dim 7: P_tie_23  (R2 ↔ R3)

总维度: 9 (5 发电机 + 4 联络线)
```

## 目标函数

```
min  Σ cost_g(P_Gg) + w_bal · (P_G_local - P_D_local - P_export)²

cost_g(P) = a·P² + b·P + c    [quadratic, $/h]
w_bal     = 1000              [power balance penalty, $/MW²]
```

联络线功率一致性由 MACPO 框架的交叉惩罚自动保证。

## 快速开始

```bash
cd power_dispatch_sim

# 1. 编译（复制源码 + 打入 patches + 构建）
bash setup.sh

# 2. 单次调试
cd algorithms/MACPO_sourcecode
mpirun -n 4 --oversubscribe ./build/MACPO_power IEEE14 LLSO ./output/

# 3. 配对对比实验
bash scripts/run_power.sh IEEE14 5 paired
bash scripts/run_power.sh ALL 5 paired
```

## 依赖

- C++11 编译器 (g++/clang++)
- CMake ≥ 3.10
- Eigen3 (`brew install eigen`)
- MPI (`brew install open-mpi`)

## 目录结构

```
power_dispatch_sim/
├── README.md
├── setup.sh                          # 环境搭建脚本
├── MACPO_power.cpp                   # MACPO 电力调度入口
├── RL_MACPO_power.cpp                # RL-MACPO 电力调度入口
├── algorithms/                       # setup.sh 生成（算法复制 + 场景文件）
│   ├── MACPO_sourcecode/
│   │   ├── MACPO_power.cpp
│   │   ├── scenarios/power_grid/
│   │   │   ├── PowerGridBenchmarks.h
│   │   │   └── ieee14bus_data.h
│   │   └── ...
│   └── RL-MACPO/
│       ├── RL_MACPO_power.cpp
│       ├── scenarios/power_grid/
│       └── ...
├── patches/
│   └── Benchmarks_virtual.h          # 虚函数化 Benchmarks 基类
├── scenarios/power_grid/
│   ├── PowerGridBenchmarks.h         # 分区经济调度评估器（IEEE 14-bus）
│   └── ieee14bus_data.h              # IEEE 14-bus 静态数据
├── scripts/
│   └── run_power.sh                  # 实验运行脚本
└── output/                           # 实验结果
```

## 对比指标

| 指标 | 含义 | 工程解释 |
|------|------|---------|
| f_penalty | 含惩罚的总成本 | 全网发电总成本 + 约束违背惩罚 |
| f_pure | 纯发电成本 | 各区域发电成本之和 |
| penalty | 一致性惩罚 | 联络线功率不一致的惩罚量 |
| conflict | 冲突指数 | 共享变量分歧程度（归一化） |
| comm_rate | 通信率 | 触发协商的迭代占比 |
| eva_count | 评估次数 | 黑盒函数调用总次数 |

## 与传统 Benchmark 实验的关键区别

1. **物理意义**: 发电机 MW 出力、$ 成本 → 可直接理解
2. **问题结构**: 低维 (9 维)、凸 → 快速收敛
3. **通信拓扑**: 非全连接，与实际电网分区一致
4. **目标函数**: 二次发电成本，非人工 benchmark 函数

</details>
