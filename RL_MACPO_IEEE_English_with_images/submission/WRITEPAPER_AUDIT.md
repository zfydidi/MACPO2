# WRITEPAPER 对照审计 — `conference_new_ready.tex` vs `conference_en_ready.tex`

对照李小平老师《离散调度类论文写作基本格式》（WRITEPAPER_xpli.pdf）及你列出的四条要求。  
**结论先行：** 投稿应使用 **`conference_new_ready.tex`**；`conference_en_ready.tex` 在叙事、结构、篇幅上与期刊版严重不一致，不宜并行投稿。

---

## 一、核心叙事（communication timing 是否为“论+证”）

| 维度 | `conference_new_ready.tex` | `conference_en_ready.tex` |
|------|---------------------------|---------------------------|
| 标题 | Conflict-Gated **Communication** … When to Negotiate | **RL-MACPO** … Learned Penalty Control |
| 摘要主线 | timing → gate → MACPO 平台 → penalty 次要 | RL-MACPO 架构 + RL penalty |
| when / how 解耦 | Discussion 第一段明确写出 | 有提及，但架构图顺序仍 penalty→gating |
| RL 定位 | default plug-in，Q3 统计 tied | 正文含 deeprl 表、RL 子图、phase_eta |
| 附录结构 | A drift / B RL 诊断 / C 应用分布 | RL 轨迹、deeprl 仍在 **正文 Q3** |
| Complexity 诚实表述 | expected execution cost ✓ | 需核对是否已同步 |
| 可读/可实现 | gate 有 Algorithm + Fig gate_policy + 默认参数表 | 模块多、RL 环路易喧宾夺主 |

**判断：** `new_ready` 已按「期刊优化阶段」叙事；`en_ready` 仍是「RL-MACPO 论文」旧版，**未**跟上当前逻辑。

---

## 二、问题 1 — 分号 / 冒号 / “AI 腔”

WRITEPAPER 要求：短句、段首中心句、逻辑清楚；你补充：**少用分号、少用冒号**。

### `conference_new_ready.tex`

| 类型 | 数量 | 典型位置 |
|------|------|----------|
| 正文分号（非 TikZ/表格行） | ~12 处 | L226, L589, L696, L763, L772, L804, L887, L890；部分 **caption** 内 |
| 冒号 | 贡献列表 `\item`、定理环境、必要定义 | 结构性的难完全去掉 |
| 一段多信息堆叠 | Limitations 段（L772） | 5 个分号串联，最像 AI 清单 |

**已处理（本次 patch）：** 正文关键分号改句号或拆句；Limitations 拆成多句。

**仍保留的冒号：** Discussion 中 *whether to communicate* : *how to negotiate* — 这是全文核心论点，建议保留一处。

### `conference_en_ready.tex`

| 类型 | 数量 |
|------|------|
| 正文分号 | ~27 处 |
| RL/架构长句 | Intro L78–80、Method L133 等 |

**建议：** 不要在这份旧稿上逐句修；若必须保留 `en_ready`，应以 `new_ready` 为母本重写。

### 「英文左右空格」

两篇为 **全英文稿**，不涉及中文混排空格问题。需注意的反而是 LaTeX 规范：`Table~\\ref{}`、`Eq.~\\eqref{}` 的 tie 空格是正确用法，不是“AI 多空格”。

---

## 三、问题 2 — 变量斜体、数字/标点正体

| 检查项 | `new_ready` | `en_ready` |
|--------|-------------|------------|
| 全局目标 | `$F(\mathbf{X})$`，Eq.~\eqref{eq:global_objective} | 混用 `$X$` 与 `$\mathbf{X}$`（L104–111） |
| 纯目标 | `$f_{\mathrm{pure}}$`（`\mathrm` 正体下标）✓ | 同 ✓ |
| 通信率 | `$\bar p_{\mathrm{comm}}$` ✓ | 同 ✓ |
| 运算符/数字 | `$K{=}10$`、`$D{=}905$` 在数学模式中 ✓ | 基本 ✓ |
| `\texttt{}` 日志字段 | Appendix drift 字段名 — 代码体，合理 |

**问题：** `en_ready` 式 (104) 用 `$X$` 而非 `$\mathbf{X}$`，与后文不一致。  
**`new_ready`：** 符号体系基本一致，无系统性“数字斜体”问题。

---

## 四、问题 3 — 图表引用与位置

WRITEPAPER：(iii) 引用所有重要图表；图表格一目了然；**正文要写到去掉图表仍能读懂结论**。

### 引用完整性

| 文件 | 未单独 `\ref` 的标签 | 说明 |
|------|----------------------|------|
| `new_ready` | `fig:rl_traj_alpha/rho/conflict/reward` | 子图，经 `fig:rl_traj_metrics` + (a)–(d) 间接引用；**已在 Appendix B.1 补显式引用** |
| `new_ready` | 其余 fig/tab/alg | **均已引用** |
| `en_ready` | `fig:rl_macpo_main`, `fig:rl_macpo_rl` | 子图 label 未单独引用（仅引 parent） |
| `en_ready` | `fig:f3_f5_micro` | **源码中 float 出现在首次引用之前**（L753 vs L760） |

### 浮动体位置（LaTeX 源码顺序）

多数图表在 **首次 `\ref` 之后的段落下方** 定义 ✓（如 Q1 先文字后 Table）。

**IEEE `[!t]` 限制：** 编译后图仍可能跑到页顶，这是 IEEEtran 常态。若期刊/导师强制“图必须在段下”，最后格式日改用 `[H]`（已加载 `float` 宏包）或 `stfloats`，**现在不宜全局改**，以免 float 连锁错乱。

### 正文是否“无图可读”

| 区块 | `new_ready` | `en_ready` |
|------|-------------|------------|
| Q1 结论 | `\paragraph{Q1 analysis}` 有数字 ✓ | 有 ✓ |
| Q2 结论 | `\paragraph{Q2 analysis}` ✓ | 较弱 |
| Q3 | synthesis 段 ✓；deeprl 在附录 | 正文图+表多，RL 味重 |
| Q4 | `\paragraph{Q4 analysis}` ✓ | 需核对 |

**`new_ready` 仍可加强：** Q2 的 `tab:lambda_sensitivity`、`tab:external_masoie` 前可增加一句“为何做此实验”的动机（论），目前略偏“报数”。

---

## 五、问题 4 — 能否让人学会、能实现

WRITEPAPER：六个问题（研究什么、为什么、什么方法、为什么此法、什么结果、为什么如此）。

| WRITEPAPER 要求 | `new_ready` | `en_ready` |
|-----------------|-------------|------------|
| (1)(2) 问题与动机 | Intro 第 2–3 段清楚 ✓ | 偏长背景 |
| (3)(4) 方法与理由 | Gate 三层 + Algorithm + 默认参数表 ✓ | RL 算法占 Method 大量篇幅 |
| (5)(6) 结果与解释 | Q1–Q4 analysis + Discussion ✓ | 有，但 RL 消融抢主线 |
| 小孩子能读懂 | 语言仍偏 dense，但结构清晰 | 更长、模块编号 1)–9) 增加认知负担 |
| 能实现 | gate_policy 流程图 + tab:gate_defaults ✓ | 需读 RL 子图 + 多算法 |

---

## 六、两文件差异总结（投稿决策）

```
                    new_ready          en_ready
叙事主线            communication      RL-MACPO
正文 RL 图/表       仅 conflict-α      轨迹+deeprl+phase_eta
附录                A/B/C              无同等结构
Discussion 定稿句   ✓ 已补全           未同步
页数                ~18                ~更长
投稿建议            ✅ 用此稿           ❌ 归档/勿投
```

---

## 七、建议修改优先级

### 仅 `conference_new_ready.tex`（投稿稿）

1. **P0** — 分号改句号 / 拆句（Limitations、Appendix、Q2 长段）→ **本次已改一部分**
2. **P1** — Appendix 子图显式 `\ref`
3. **P2** — Q2 外部 baseline / λ 表各加 1 句“为何做、说明什么”
4. **P3（格式日）** — `[H]` 浮动、期刊模板、参考文献

### `conference_en_ready.tex`

- **不建议再维护。** 若必须同步，应以 `new_ready` 覆盖 Intro/Method/Q3/Discussion/Appendices，而不是反向合并。

---

## 八、与 WRITEPAPER PDF 的其他对齐

| PDF 要求 | 状态 |
|----------|------|
| 每段首句中心句 | 大体符合；Limitations 原段需拆句 ✓ |
| 表格/图高分辨率 | PDF 矢量图 ✓ |
| 避免长句 | `en_ready` 更差；`new_ready` 中等 |
| 被动语态（主语为人称时） | 两篇均以被动/无主句为主 ✓ |
| 不自我剽窃堆旧文 | 需确认与旧 conference 稿差异说明 |

---

*审计日期：2026-06-15。修复 patch 见 `conference_new_ready.tex` 同期 git diff。*
