# MACPO对比实验总结

## 实验概述

本次实验对比了两个MACPO版本：
- **Baseline**: MACPO_sourcecode (原始版本)
- **RL-MACPO**: 改进版本（带有强化学习增强的惩罚机制）

## 实验配置

- **优化器**: LLSO (Learning Level Swarm Optimizer)
- **测试函数**: F1-F6
- **进程数**: 20 (使用--oversubscribe模式)
- **实验编号**: ex01

## 运行信息

### 运行命令

```bash
# 运行完整对比实验
bash run_comparison.sh

# 监控进度
bash monitor_progress.sh

# 绘制对比图
python3 plot_comparison.py
```

### 实验数据位置

```
output/
├── baseline/          # MACPO_sourcecode结果
│   ├── F1_LLSO_ex01.txt
│   ├── F2_LLSO_ex01.txt
│   ├── F3_LLSO_ex01.txt
│   ├── F4_LLSO_ex01.txt
│   ├── F5_LLSO_ex01.txt
│   └── F6_LLSO_ex01.txt
├── RL-MACPO/          # RL-MACPO结果
│   ├── F1_LLSO_ex01.txt
│   ├── F2_LLSO_ex01.txt
│   ├── F3_LLSO_ex01.txt
│   ├── F4_LLSO_ex01.txt
│   ├── F5_LLSO_ex01.txt
│   └── F6_LLSO_ex01.txt
└── figures/           # 生成的对比图
    ├── F1_comparison_3plots.png          (三合一对比图)
    ├── F1_fes_penalty_fitness.png        (带惩罚适应度)
    ├── F1_fes_pure_fitness.png           (纯适应度)
    ├── F1_fes_penalty_comparison.png     (惩罚值与权重对比)
    └── ... (F2-F6的相同图表)
```

## 生成的图表类型

对于每个测试函数（F1-F6），生成了以下4种图表：

### 1. 三合一对比图 (`{F}_comparison_3plots.png`)

包含三个子图的综合对比：
- 左图：带惩罚的适应度曲线对比
- 中图：纯适应度曲线对比（无惩罚项）
- 右图：惩罚值和惩罚权重对比（实线表示惩罚值，虚线表示权重）

### 2. 带惩罚适应度对比 (`{F}_fes_penalty_fitness.png`)

显示两个版本的带惩罚适应度（f_penalty）随评估次数（FES）的变化。

### 3. 纯适应度对比 (`{F}_fes_pure_fitness.png`)

显示两个版本的纯适应度（f_pure，不含惩罚项）随评估次数的变化。
这是评估算法实际优化性能的关键指标。

### 4. 惩罚机制对比 (`{F}_fes_penalty_comparison.png`)

对比两个版本的：
- **惩罚值** (penalty，实线): 实际施加的惩罚大小
- **惩罚权重** (weight，虚线): 动态调整的惩罚权重参数α

## 数据格式说明

每个输出文件包含以下列：

| 列名 | 说明 |
|------|------|
| iter | 迭代次数 |
| eval | 累计评估次数（FES） |
| f_penalty | 带惩罚的适应度值 |
| f_pure | 纯适应度值（无惩罚项） |
| penalty | 惩罚项大小 (f_penalty - f_pure) |
| improvement | 改进率 |
| reward | 强化学习奖励值 |
| conflict | 冲突度 |
| weight | 惩罚权重参数α |

## 关键观察点

### Baseline (MACPO_sourcecode)
- 使用固定的惩罚权重动态调整策略
- 惩罚权重 = |f| / 512

### RL-MACPO
- 在第一次迭代后动态测量实际冲突规模
- 根据测量的conflict自适应调整α
- 如果conflict > 1.0，则使用缩放因子: α_adjusted = base_α / conflict
- 目标是保持 penalty/f ≈ 0.195% (1/512)

## 预期分析方向

1. **收敛速度**: 比较两个版本达到相同f_pure值所需的FES
2. **最终性能**: 比较在相同FES下的最优f_pure值
3. **惩罚效果**: 分析penalty曲线，评估惩罚机制的有效性
4. **权重动态**: 观察weight参数的调整过程和稳定性

## 注意事项

- 所有图表使用对数坐标(log scale)以更清晰地显示收敛过程
- X轴为评估次数（FES），可以公平比较不同算法的效率
- 纯适应度（f_pure）是评估算法实际优化能力的核心指标
- 惩罚项主要用于协调多子问题间的冲突，不应主导目标函数

---

生成时间: 2026-01-23
实验平台: macOS (Apple Silicon)
MPI版本: Open MPI 5.0.7
