# f_pure、f_penalty与h函数的对应关系

## 🎯 核心结论

在**两个算法**中：
- **`f_penalty`** = `h_i(x)` （带惩罚的目标函数）
- **`f_pure`** = `f_i(x)` （纯目标函数，不含惩罚）

---

## 📊 输出数据说明

### Source MACPO输出

查看 `output/baseline/F1_LLSO_ex01.txt`：

| 列名 | 数学符号 | 计算方式 | 说明 |
|------|---------|---------|------|
| `f_penalty` | `h(x)` | `Evaluator->evaluate(globalBest)` | **带惩罚**的目标函数 ✅ |
| `f_pure` | `f(x)` | `pFunc->local_eva(globalBest, myrank)` | **纯**目标函数，无惩罚 ✅ |
| `penalty` | `penalty` | `f_penalty - f_pure` | 惩罚项的值 |

**代码位置**（MACPO.cpp 第292-301行）：
```cpp
// f_penalty: 带惩罚的fitness
double local_fit = Optimizer->Evaluator->evaluate(globalBest);
double global_fit = global_average(local_fit, commu_object) * nprocs;

// f_pure: 纯fitness（不含惩罚）
double local_fit_pure = pFunc->local_eva(globalBest, myrank);
double global_fit_pure = global_sum_pure / nprocs;

// 输出
outfile << global_fit << "\t"         // f_penalty = h(x)
        << global_fit_pure << "\t"    // f_pure = f(x)
        << (global_fit - global_fit_pure) << "\t"  // penalty
```

---

### RL-MACPO输出

查看 `output/RL-MACPO/F1_LLSO_ex01.txt`：

| 列名 | 数学符号 | 计算方式 | 说明 |
|------|---------|---------|------|
| `f_penalty` | `h(x)` | `Evaluator->evaluate(globalBest)` | **带惩罚**的目标函数 ✅ |
| `f_pure` | `f(x)` | `p_func->local_eva(globalBest, myrank)` | **纯**目标函数，无惩罚 ✅ |
| `penalty` | `penalty` | `f_penalty - f_pure` | 惩罚项的值 |

**代码位置**（MACPO_simplified.cpp 第384-393行）：
```cpp
// f_penalty: 带惩罚的fitness
double local_fit_with_penalty = Evaluator->evaluate(globalBest);
double global_fit_with_penalty = global_average(local_fit_with_penalty, commu_object) * nprocs;

// f_pure: 纯fitness（不含惩罚）
double local_fit_pure = pFunc->local_eva(globalBest, myrank);
double global_fit_pure = global_sum_pure / nprocs;

// 输出（第485-487行）
outfile << global_fit_with_penalty << "\t"    // f_penalty = h(x)
        << global_fit_pure << "\t"            // f_pure = f(x)
        << (global_fit_with_penalty - global_fit_pure) << "\t"  // penalty
```

---

## 🔍 详细分析

### 1. f_penalty = h(x) （带惩罚）

**定义**：
```
h_i(x) = Evaluator->evaluate(x)
```

**Source MACPO**：
```cpp
double evaluate(double* X) {
    res = pFunc->local_eva(X, groupIndex);  // f_i(x)
    for (int i = 0; i < overlapSize; ++i) {
        res += alpha * fabs(X[index] - globalBest[index]) * variable_switch[index];
        //     惩罚项
    }
    return res;  // h_i(x) = f_i(x) + penalty
}
```

**RL-MACPO**：
```cpp
double evaluate(double* x) {
    double obj_value = p_func->local_eva(x, group_index);  // f_i(x)
    double conflict_penalty = calculate_conflict(x);
    return obj_value + alpha * conflict_penalty;  // h_i(x) = f_i(x) + penalty
}
```

**数学公式**：

**Source**：
```latex
h_i(x) = f_i(x) + \frac{|f_i(x)|}{512} \cdot \sum_{j \in \mathcal{N}_i} \sum_{d \in \mathcal{I}_{i,j}} (t_{j,d} |x^d - x_{i,\text{con}}^d|)
```

**RL-MACPO**：
```latex
h_i(x) = f_i(x) + \frac{|f_i(x)|}{512} \cdot \text{ratio}_i \cdot \sum_{j \in \mathcal{N}_i} \sum_{d \in \mathcal{I}_{i,j}} \frac{|x^d - x_{i,\text{con}}^d|}{x_{\max} - x_{\min}}
```

---

### 2. f_pure = f(x) （纯目标函数）

**定义**：
```
f_i(x) = pFunc->local_eva(x, agent_id)
```

**完全相同**（两个算法）：
```cpp
double local_fit_pure = pFunc->local_eva(globalBest, myrank);
```

**数学公式**：
```latex
f_i(x) = \text{local\_eva}(x, i)
```

**说明**：
- 这是原始的目标函数值
- 不包含任何惩罚项
- 两个算法计算方式完全相同

---

### 3. penalty （惩罚项）

**定义**：
```
penalty = h(x) - f(x) = f_penalty - f_pure
```

**Source MACPO**：
```
penalty = α · ∑_{j,d} (t_{j,d} |x^d - x_{con}^d|)
```

**RL-MACPO**：
```
penalty = α · ∑_{j,d} (|x^d - x_{con}^d| / (x_max - x_min))
```

---

## 📋 输出列对照表

### Baseline (Source MACPO)

| 列名 | 对应函数 | 数学符号 |
|------|---------|---------|
| `f_penalty` | `h(x)` | 带惩罚目标函数 ✅ |
| `f_pure` | `f(x)` | 纯目标函数 ✅ |
| `penalty` | `penalty` | 惩罚项 = h(x) - f(x) |
| `weight` | `α` | 惩罚系数 = \|f\|/512 |

### RL-MACPO

| 列名 | 对应函数 | 数学符号 |
|------|---------|---------|
| `f_penalty` | `h(x)` | 带惩罚目标函数 ✅ |
| `f_pure` | `f(x)` | 纯目标函数 ✅ |
| `penalty` | `penalty` | 惩罚项 = h(x) - f(x) |
| `weight` | `Σα_i` | 所有agents的α之和 |

---

## ✅ 回答您的问题

### Q: f_pure和f_penalty哪个对应h函数？

**A: `f_penalty` 对应 `h(x)` 函数！**

### 详细说明

**`f_penalty`**：
- ✅ 对应数学公式中的 `h_i(x)`
- ✅ 包含惩罚项
- ✅ 算法实际优化的目标
- 代码：`Evaluator->evaluate(globalBest)`

**`f_pure`**：
- ✅ 对应数学公式中的 `f_i(x)`
- ✅ 不含惩罚项
- ✅ 原始benchmark函数值
- 代码：`pFunc->local_eva(globalBest, myrank)`

**`penalty`**：
- ✅ 就是惩罚项本身
- ✅ 等于 `f_penalty - f_pure`
- ✅ 等于 `h(x) - f(x)`

---

## 📊 数值验证

### Source MACPO (iter 1)

```
f_penalty = 1.07E+10  // h(x)
f_pure    = 6.30E+08  // f(x)
penalty   = 1.01E+10  // h(x) - f(x)

验证：6.30E+08 + 1.01E+10 = 1.07E+10 ✅
```

### RL-MACPO (iter 1)

```
f_penalty = 3.91E+09  // h(x)
f_pure    = 1.67E+08  // f(x)
penalty   = 3.75E+09  // h(x) - f(x)

验证：1.67E+08 + 3.75E+09 = 3.92E+09 ≈ 3.91E+09 ✅
```

---

## 🎯 总结

### 函数对应关系

| 输出列名 | 数学符号 | 说明 | 包含惩罚？ |
|---------|---------|------|----------|
| **f_penalty** | **h(x)** | 带惩罚的目标函数 | ✅ 是 |
| **f_pure** | **f(x)** | 纯目标函数 | ❌ 否 |
| **penalty** | **penalty** | 惩罚项 | - |

### 数学公式

**Source MACPO**：
```latex
\text{f\_penalty} = h_i(x) = f_i(x) + \frac{|f_i(x)|}{512} \cdot \sum_{j,d} (t_{j,d} |x^d - x_{con}^d|)
\text{f\_pure} = f_i(x)
\text{penalty} = h_i(x) - f_i(x)
```

**RL-MACPO**：
```latex
\text{f\_penalty} = h_i(x) = f_i(x) + \frac{|f_i(x)|}{512} \cdot r_i \cdot \sum_{j,d} \frac{|x^d - x_{con}^d|}{x_{\max}-x_{\min}}
\text{f\_pure} = f_i(x)
\text{penalty} = h_i(x) - f_i(x)
```

---

**结论**：
- ✅ **f_penalty就是h(x)函数**
- ✅ **f_pure就是f(x)函数**
- ✅ 两个算法的定义完全一致
