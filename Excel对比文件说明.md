# 📊 Excel对比文件说明

## 📁 生成的文件

### 个别函数对比文件
位置：`output/excel_comparison/`

- `F1_comparison.xlsx`
- `F2_comparison.xlsx`
- `F3_comparison.xlsx`
- `F4_comparison.xlsx`
- `F5_comparison.xlsx`
- `F6_comparison.xlsx`

### 汇总文件
- `ALL_FUNCTIONS_SUMMARY.xlsx` - 所有函数的统计汇总

---

## 📋 每个Excel文件的结构

### Sheet 1: Baseline
原始MACPO的完整数据（9列）：
- iter, eval, f_penalty, f_pure, penalty, improvement, reward, conflict, weight

### Sheet 2: RL-MACPO
RL-MACPO的完整数据（9列）：
- iter, eval, f_penalty, f_pure, penalty, improvement, reward, conflict, weight
- **注意**：这里的weight是单个agent的α（不是Σα_i）

### Sheet 3: Weight_Comparison
Weight的直接对比：
- Iteration - 迭代次数
- Baseline_weight - Baseline的weight
- RL_weight - RL-MACPO的weight（单个agent的α）
- Ratio (RL/Baseline) - RL/Baseline的比例
- Baseline_conflict - Baseline的conflict
- RL_conflict - RL-MACPO的conflict
- Conflict_ratio (RL/Baseline) - conflict的比例

### Sheet 4: Summary
统计摘要，包含：
- Weight统计（均值、标准差、最小值、最大值）
- Weight比例统计
- Conflict统计
- Fitness统计（最终fitness和改进百分比）

---

## 🔍 关键发现

### Weight比例（RL单个α / Baseline总weight）

| 函数 | Baseline weight | RL weight (单个α) | 比例 |
|------|----------------|------------------|------|
| F1   | 4.05e+06      | 9.79e+05         | 0.49x |
| F2   | 8.31e+06      | 1.59e+03         | 0.11x |
| F3   | 8.45e+07      | 1.29e+04         | 0.00x |
| F4   | 3.11e+06      | 4.19e+05         | 0.54x |
| F5   | 9.12e+06      | 4.36e+05         | 0.10x |
| F6   | 1.55e+06      | 1.04e+04         | 0.03x |

**说明**：
- RL-MACPO的weight是**单个agent的α**
- Baseline的weight是**所有agents的总weight**
- 如果使用4个agents，RL的总weight (Σα_i) ≈ 单个α × 4

### 预估：如果使用Σα_i（4个agents）

| 函数 | Baseline weight | RL weight × 4 | 预估比例 |
|------|----------------|---------------|---------|
| F1   | 4.05e+06      | ~3.92e+06     | ~0.97x ✅ |
| F2   | 8.31e+06      | ~6.36e+03     | ~0.00x ❌ |
| F3   | 8.45e+07      | ~5.16e+04     | ~0.00x ❌ |
| F4   | 3.11e+06      | ~1.68e+06     | ~0.54x △ |
| F5   | 9.12e+06      | ~1.74e+06     | ~0.19x ❌ |
| F6   | 1.55e+06      | ~4.16e+04     | ~0.03x ❌ |

**观察**：
- ✅ **F1接近1.0**：说明方案1可能有效
- △ **F4有改善**：从0.54提升到理论上的0.54（需要实际测试）
- ❌ **F2、F3、F5、F6差异很大**：即使乘以4也不匹配

---

## ⚠️ 重要说明

### 1. RL-MACPO的weight是单个agent的α

当前Excel中的RL-MACPO数据是从旧版本代码生成的，输出的是：
```
weight = α_0  // rank 0的α值
```

### 2. 方案1的改进

方案1修改后，新版本会输出：
```
weight = Σα_i  // 所有4个agents的α之和
alpha_avg = Σα_i / 4
alpha_rank0 = α_0
alpha_min = min(α_i)
alpha_max = max(α_i)
```

### 3. 为什么有些函数差异很大？

可能的原因：
1. **Conflict计算方法不同**
   - Baseline: 未归一化或使用不同的归一化
   - RL-MACPO: 归一化到problem range
   
2. **Base alpha计算不同**
   - Baseline: 可能基于所有agents的总fitness
   - RL-MACPO: 基于单个agent的fitness

3. **Agent数量假设**
   - 当前假设是4个agents
   - 实际运行时的agent数量可能不同

---

## 🎯 如何使用这些Excel

### 用途1：了解当前的weight差异

打开 `Weight_Comparison` sheet，查看：
- 每次迭代的weight比例
- weight随迭代的变化趋势
- conflict的差异

### 用途2：分析为什么需要方案1

这些数据清楚地显示：
- RL-MACPO的单个α比Baseline的总weight小很多
- 需要输出Σα_i来匹配Baseline的数量级

### 用途3：预测方案1的效果

基于比例关系：
- F1预计会接近1.0（很好）
- F4预计会有改善
- F2、F3、F5、F6可能需要进一步调查

---

## 🔄 下一步行动

### 短期：获取更新后的数据

1. 解决MPI编译/运行问题
2. 运行更新后的代码（输出Σα_i）
3. 生成新的Excel对比
4. 验证方案1的效果

### 长期：如果效果不理想

考虑方案2或方案3：
- 方案2：统一conflict归一化
- 方案3：调整base_alpha计算方法

---

## 📚 相关文档

- `HOW_TO_UNIFY_WEIGHT_OUTPUT.md` - 完整的方案说明
- `SOLUTION1_IMPLEMENTATION.md` - 方案1实施细节
- `SOLUTION1_SUMMARY.md` - 方案1总结
- `WEIGHT_TRUE_MEANING.md` - weight的物理意义

---

**生成时间**：2026年1月28日  
**数据来源**：output/baseline 和 output/RL-MACPO（旧版本数据）  
**说明**：这是基于旧版本数据的对比，新版本（方案1）的数据需要重新运行实验生成
