# RL-MACPO 实验数据和图表说明文档

## 📊 生成的文件位置

### 1. Excel数据文件
位置：`output/excel_data/`

包含文件：
- `F1_all_data.xlsx` ~ `F6_all_data.xlsx` - 每个函数的完整数据（3个sheet）
  - Sheet 1: Baseline（MACPO_sourcecode）
  - Sheet 2: RL-MACPO
  - Sheet 3: IMPROVED_with_FES（含FES计算代价）
  
- `Summary_All_Functions.xlsx` - 所有函数的最终结果汇总表

- `FES_Cost_Data.xlsx` - FES计算代价专项数据（6个sheet，每个函数一个）

### 2. 图表文件

#### 原始图表（无公式标注）
位置：`output/figures/`
- `F1~F6_baseline_penalty_vs_pure.png` - Baseline方法的带惩罚vs纯适应度
- `F1~F6_rlmacpo_penalty_vs_pure.png` - RL-MACPO方法的带惩罚vs纯适应度
- `F1~F6_penalty_vs_pure_by_method.png` - 两方法并排对比
- `F1~F6_comparison_3plots.png` - 三合一对比图
- `FES_cost_comparison_F1_F6.png` - FES耗时曲线对比
- `FES_cost_bar_chart_F1_F6.png` - FES耗时柱状图
- `FES_efficiency_F1_F6.png` - FES效率分析

#### 改进图表（带统一公式标注）⭐ 推荐使用
位置：`output/figures_with_formulas/`
- `F1~F6_penalty_vs_pure_comparison.png` - 带惩罚vs纯适应度对比（带公式）
- `FES_cost_comparison_F1_F6.png` - FES耗时曲线对比（带公式）
- `FES_cost_bar_chart_F1_F6.png` - FES耗时柱状图（带公式）

---

## 📐 核心数学公式

### 1. 基本关系式
```
f_penalty = f_pure + penalty
```
- **说明**：带惩罚的适应度 = 纯适应度 + 惩罚项
- **用途**：优化器实际使用的目标函数

### 2. 惩罚项计算
```
penalty = α × conflict
```
- **说明**：惩罚项 = 惩罚系数 × 冲突度量
- **符号**：
  - `α` (alpha): 惩罚权重系数（在代码中对应`weight`列）
  - `conflict`: 冲突度量（梯度冲突或变量不一致性）

### 3. RL惩罚系数调整（两层更新）

#### 第一层：基准惩罚系数
```
α_base = |f| / 512
```
- **说明**：基准惩罚系数根据目标函数值的数量级自适应设置
- **数值示例**：
  - 若 `|f| = 1e8`，则 `α_base ≈ 195312.5`
  - 若 `|f| = 1e6`，则 `α_base ≈ 1953.125`

#### 第二层：RL比例调整
```
ratio ← clip(ratio + 0.1·a, 0.1, 2.0)
α = α_base × ratio
```
- **说明**：
  1. RL策略网络输出动作 `a` ∈ [-1, +1]
  2. 用 `a` 调整比例参数 `ratio`（步长0.1）
  3. `ratio` 被限制在 [0.1, 2.0] 范围内
  4. 最终惩罚系数 = 基准值 × 比例
  
- **效果**：允许 `α` 在 [0.1×α_base, 2.0×α_base] 范围内动态调整

### 4. 动态α初始化（仅首次迭代）
```
if iter == 0 && measured_conflict > 1.0:
    scaling_factor = 1.0 / measured_conflict
    α ← α_base × scaling_factor
```
- **说明**：首次迭代时，如果冲突过大，动态缩放一次基准惩罚系数
- **后续迭代**：由RL在这个初始值基础上微调

### 5. FES计算代价
```
T_FES = Σ(i=1 to n) t_i    （累计总耗时）
t̄ = T_FES / n              （单次平均耗时）
```
- **符号**：
  - `T_FES`: 累计FES总耗时（毫秒转秒）
  - `t_i`: 第i次FES的耗时
  - `n`: 总FES次数（实验中为150,300）
  - `t̄`: 单次FES平均耗时（毫秒）

---

## 📋 Excel数据列说明

### Baseline和RL-MACPO表格（.txt来源）
| 列名 | 说明 | 单位 | 公式关系 |
|-----|------|-----|---------|
| `iter` | 迭代次数 | - | - |
| `eval` | 累计函数评估次数 | - | FES |
| `f_penalty` | 带惩罚的适应度 | - | = `f_pure` + `penalty` |
| `f_pure` | 纯适应度 | - | 原始目标函数值 |
| `penalty` | 惩罚项 | - | = `weight` × `conflict` |
| `improvement` | 适应度改善率 | - | 相对上次迭代的改善 |
| `reward` | RL奖励值 | - | 用于训练RL策略网络 |
| `conflict` | 冲突度量 | - | 梯度冲突或变量不一致性 |
| `weight` | 惩罚权重（α） | - | = `α_base` × `ratio` |

### IMPROVED表格（.tsv来源，含FES代价）
在上述列基础上，额外包含：
| 列名 | 说明 | 单位 | 公式关系 |
|-----|------|-----|---------|
| `gen` | 代数 | - | - |
| `fes_ms_tot` | 累计FES总耗时 | 毫秒 | T_FES |
| `fes_ms_per` | 单次FES平均耗时 | 毫秒 | t̄ = T_FES / n |
| `fes_time_sec` | 累计FES总耗时 | 秒 | = `fes_ms_tot` / 1000 |

---

## 📈 图表类型说明

### 1. 带惩罚vs纯适应度对比图
- **文件名格式**：`F*_penalty_vs_pure_comparison.png`
- **内容**：
  - 左图：Baseline方法
  - 右图：RL-MACPO方法
  - 实线：f_penalty（带惩罚）
  - 虚线：f_pure（纯适应度）
- **公式标注**：
  - Baseline: `f_penalty = f_pure + penalty`, `penalty = α × conflict`
  - RL-MACPO: `f_penalty = f_pure + penalty`, `α = α_base × ratio`

### 2. FES计算代价曲线对比
- **文件名**：`FES_cost_comparison_F1_F6.png`
- **内容**：
  - 上图：累计FES总耗时（秒）vs FES次数
  - 下图：单次FES平均耗时（毫秒）vs FES次数
- **公式标注**：`T_FES = Σt_i`, `t̄ = T_FES/n`

### 3. FES计算代价柱状图
- **文件名**：`FES_cost_bar_chart_F1_F6.png`
- **内容**：
  - 左图：6个函数的最终累计总耗时
  - 右图：6个函数的最终单次平均耗时
- **数值标注**：每个柱子顶部显示具体数值

---

## 🔢 实验结果汇总（最终值）

| 函数 | Baseline<br>f_penalty | RL-MACPO<br>f_penalty | 改善率 | FES总耗时(s) | 单次平均(ms) |
|-----|----------------------|----------------------|--------|-------------|-------------|
| F1  | 2.65e+08            | 1.32e+08            | 50.2%  | 3.45        | 0.023       |
| F2  | 1.05e+06            | 6.53e+04            | 93.8%  | 3.61        | 0.024       |
| F3  | 2.54e+10            | 1.19e+04            | >99.9% | 2.96        | 0.020       |
| F4  | 6.05e+07            | 5.47e+07            | 9.6%   | 4.39        | 0.029       |
| F5  | 4.51e+08            | 5.96e+07            | 86.8%  | 3.31        | 0.022       |
| F6  | 1.42e+06            | 3.39e+04            | 97.6%  | 3.39        | 0.023       |

**关键发现**：
- ✅ **F3计算效率最高**：单次FES仅需0.020ms
- ⚠️ **F4计算代价最高**：单次FES需要0.029ms，比F3慢47%
- 🎯 **RL-MACPO在所有函数上都优于Baseline**

---

## 📝 数据使用建议

### 论文写作
1. **图表选择**：推荐使用 `output/figures_with_formulas/` 中的图表，公式标注清晰统一
2. **数据引用**：直接从Excel文件中复制数据到论文表格
3. **公式引用**：参考本文档中的LaTeX格式公式

### 进一步分析
1. **Excel数据**：可用于深度统计分析、绘制自定义图表
2. **原始txt/tsv文件**：位于 `output/baseline/`、`output/RL-MACPO/`、`output/IMPROVED/LLSO/`

### LaTeX公式（可直接复制）

```latex
% 基本关系式
f_{\mathrm{penalty}} = f_{\mathrm{pure}} + \mathrm{penalty}

% 惩罚项计算
\mathrm{penalty} = \alpha \times \mathrm{conflict}

% RL两层更新
\alpha = \alpha_{\mathrm{base}} \times \mathrm{ratio}

\alpha_{\mathrm{base}} = \frac{|f|}{512}

\mathrm{ratio} \leftarrow \mathrm{clip}(\mathrm{ratio} + 0.1 \cdot a, 0.1, 2.0)

% FES计算代价
T_{\mathrm{FES}} = \sum_{i=1}^{n} t_i

\bar{t} = \frac{T_{\mathrm{FES}}}{n}
```

---

## 🛠️ 脚本说明

生成这些数据和图表的脚本：

1. **export_data_to_excel.py** - 导出所有数据到Excel
2. **plot_with_formulas.py** - 生成带公式标注的图表
3. **plot_penalty_vs_pure.py** - 生成原始penalty vs pure对比图
4. **plot_comparison.py** - 生成原始三合一对比图
5. **plot_fes_cost.py** - 生成原始FES代价图

