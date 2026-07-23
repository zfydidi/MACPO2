"""
协议无关的冲突门控协商沙盘（Gated Negotiation Sandbox）
======================================================

用途（方向 A / A1）：证明论文的**冲突门控层是与底层协商范式无关的通信调度层**，
而不是只对 MACPO negotiation 有效的补丁。

做法：把论文里的三层门控（Eq. local_gate）抽象成一个 solver 无关的 ``ConflictGate``，
它**只依赖一个黑箱冲突代理 CI 和触发信号 g**（与 utils/ci_bin_trigger.py 里门控只吃
标量 conflict/gate_comm 完全一致），然后把同一个门控接到**结构上不同的协商规则**上：

  * "average"    : Metropolis 双随机平均共识（penalty-based NDO 的主流混合）
  * "gossip"     : 随机成对 gossip（每轮只有一条随机边平均）
  * "nash"       : Nash 双边比较的简化版（只向更优邻居靠拢，非对称）

度量：平均触发率 p_comm（= 门控开的比例）对应的稳态一致性误差 ‖e‖。
若"门控省通信不掉质量"这一结论**在三种协商规则下都成立**（同触发率下稳态误差相近，
且远优于同等预算的周期/随机触发），则门控的有效性与具体协商机制无关。

符号对齐论文（conference_new_ready.tex）：
  - 归一化 gap  e_d^t = |x_d^t - r_d^t| / R_d          （Eq. 一致性缺口）
  - 冲突指数    CI_i^t 由各维 e_d 聚合（这里用 L2/维数）
  - EMA 基线    μ̂_CI^t = γ μ̂^{t-1} + (1-γ) CI^t
  - 三层门控    (1) 最小间隔 Δmin  (2) 相对阈值 CI>λμ̂ 或 fail-safe t-t_last≥K  (3) 相位采样

谱量估计/护栏复用 utils/spectral_consensus.py，不在本模块重写。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from utils.spectral_consensus import spectral_gap


# --------------------------------------------------------------------------- #
# 协商规则族：solver 无关。每个规则把"分散解 x"朝共识拉一步，接口统一。
# 返回 (x_next, r_ref)：x_next 为协商后解，r_ref 为供门控计算 CI 的共识参考。
# --------------------------------------------------------------------------- #
def _metropolis_mixing(n: int, self_weight: float = 0.5) -> np.ndarray:
    """环形拓扑上的 Metropolis 双随机混合矩阵（病态稀疏图）。"""
    W = np.zeros((n, n))
    for i in range(n):
        for j in ((i - 1) % n, (i + 1) % n):
            W[i, j] = (1.0 - self_weight) / 2.0
        W[i, i] = self_weight
    return W


def negotiate(rule: str, x: np.ndarray, W: np.ndarray, lam: float,
              rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """执行一步协商（仅当门控开时调用）。rule 决定协商范式，门控层对此无感知。

    x : (N, d) 各 agent 当前解。W: (N,N) 邻接/混合矩阵。lam: 共识增益。
    """
    n = x.shape[0]
    r = W @ x  # 邻域共识参考（对任意规则都作为门控的 r_d^t）
    if rule == "average":
        x_next = x - lam * ((np.eye(n) - W) @ x)
    elif rule == "gossip":
        # 随机成对 gossip：一次"通信事件"= 随机打乱所有边各激活一次（一整轮 gossip）。
        # 与 average/nash 一样每事件做一整轮，使"每事件混合力度"可比，隔离出时序变量。
        x_next = x.copy()
        idx = np.flatnonzero(np.triu(W, 1).ravel())
        rng.shuffle(idx)
        for e in idx:
            i, j = divmod(int(e), n)
            mid = 0.5 * (x_next[i] + x_next[j])
            x_next[i] = (1 - lam) * x_next[i] + lam * mid
            x_next[j] = (1 - lam) * x_next[j] + lam * mid
    elif rule == "nash":
        # Nash 双边最佳响应（简化版）：非对称、分布式可算、单调改进。
        # 各 agent 以邻域均值 r_i=(Wx)_i 为局部共识参考；仅"偏离超过群体中位数"的
        # 冲突 agent 才向 r_i 移动一步，其余保持不动。区别于对称平均（全员移动），
        # 是只让更差一方让步的最佳响应动态（每步严格降低该 agent 的邻域分歧→稳定）。
        x_next = x.copy()
        dev = np.linalg.norm(x - r, axis=1)
        thr = np.median(dev)
        move = dev > thr
        x_next[move] = (1 - lam) * x[move] + lam * r[move]
    else:
        raise ValueError(f"unknown negotiation rule: {rule!r}")
    return x_next, r


# --------------------------------------------------------------------------- #
# 冲突门控层：solver 无关，只吃 CI 与历史（对齐论文三层门控）
# --------------------------------------------------------------------------- #
@dataclass
class ConflictGate:
    """论文三层冲突门控（Eq. local_gate）的 solver 无关实现。

    lam_thr   : 相对阈值倍数 λ（CI > λ·μ̂ 触发）。
    K         : fail-safe 静默上限（t - t_last ≥ K 强制通信）。
    delta_min : 最小通信间隔 Δmin（Layer 1）。
    gamma     : CI 的 EMA 平滑系数 γ。
    p_phase   : 相位采样概率（Layer 3），1.0 表示关闭该层随机性。
    """

    lam_thr: float = 1.0
    K: int = 20
    delta_min: int = 1
    gamma: float = 0.8
    p_phase: float = 1.0
    _mu: float = field(default=None, repr=False)
    _t_last: int = field(default=-(10**9), repr=False)

    def conflict_index(self, x: np.ndarray, r: np.ndarray, R: float) -> float:
        """CI = 归一化 gap 的 RMS（对齐 e_d = |x_d - r_d|/R 的聚合）。"""
        e = np.abs(x - r) / max(R, 1e-12)
        return float(np.sqrt(np.mean(e ** 2)))

    def decide(self, t: int, ci: float, rng: np.random.Generator) -> bool:
        """返回本轮全局门控 g_global^t ∈ {0,1}。更新 EMA 基线。"""
        self._mu = ci if self._mu is None else self.gamma * self._mu + (1 - self.gamma) * ci
        # Layer 1: 最小间隔
        if t - self._t_last < self.delta_min:
            return False
        # Layer 2: 相对阈值 或 fail-safe
        thr_hit = ci > self.lam_thr * self._mu
        failsafe = (t - self._t_last) >= self.K
        if not (thr_hit or failsafe):
            return False
        # Layer 3: 相位采样（failsafe 时强制，不被相位否决）
        if not failsafe and self.p_phase < 1.0 and rng.random() > self.p_phase:
            return False
        self._t_last = t
        return True


@dataclass
class ConsensusErrorResult:
    """一次沙盘运行的结果。"""

    trigger_rate: float          # 平均触发率 p_comm
    steady_error: float          # 末段稳态一致性误差 ‖e‖（尾窗均值）
    err_curve: np.ndarray        # 全程一致性误差
    gate_curve: np.ndarray       # 每步 g_global


def run_sandbox(
    rule: str,
    *,
    n: int = 12,
    d: int = 4,
    steps: int = 600,
    lam: float = None,
    sigma: float = 0.25,
    gate: ConflictGate | None = None,
    forced_schedule: str | None = None,
    period: int = 1,
    seed: int = 0,
    tail: int = 100,
) -> ConsensusErrorResult:
    """在给定协商规则上跑"局部探索 + 门控协商"，返回触发率与稳态误差。

    forced_schedule: None 用门控; "periodic" 每 period 步触发; "random" 以 1/period 概率触发。
    这样可在**同一协商规则**下比较"门控 vs 周期 vs 随机"是否等触发率下门控更优。
    """
    rng = np.random.default_rng(seed)
    W = _metropolis_mixing(n)
    if lam is None:
        g2, gN = spectral_gap(W)
        lam = 2.0 / (g2 + gN)  # Chebyshev 最优增益（spectral_consensus 组件 A）
    x = rng.standard_normal((n, d)) * 3.0
    R = 6.0  # 搜索范围尺度（用于 e_d 归一化）
    gate = gate or ConflictGate()
    r = W @ x
    errs, gates = [], []
    # 不可预测的突发冲突：以低概率在随机时刻对随机 agent 注入大冲击，其余时刻仅有
    # 微弱基线扰动。这是"事件触发 vs 时间触发"的关键设定——门控能凭实时 CI 精准命中
    # 突发，而固定周期/随机触发无法预知突发时刻，只能盲目撒预算。
    shock_rate = 0.06     # 每步发生突发的概率
    shock_mag = sigma * 8.0
    base_sig = sigma * 0.1
    for t in range(steps):
        # 基线微扰动（平静期）
        x = x + base_sig * rng.standard_normal(x.shape)
        # 随机突发冲击（不可预测时刻/对象）
        if rng.random() < shock_rate:
            k = rng.integers(0, n)
            x[k] = x[k] + shock_mag * rng.standard_normal(d)
        ci = gate.conflict_index(x, r, R)
        if forced_schedule == "periodic":
            g = (t % max(period, 1)) == 0
        elif forced_schedule == "random":
            g = rng.random() < (1.0 / max(period, 1))
        else:
            g = gate.decide(t, ci, rng)
        if g:
            x, r = negotiate(rule, x, W, lam, rng)
        # 否则跳过协商、刷新共识参考（对齐论文 skip 分支）
        e = x - x.mean(axis=0, keepdims=True)
        errs.append(float(np.linalg.norm(e)))
        gates.append(1.0 if g else 0.0)
    errs = np.asarray(errs)
    gates = np.asarray(gates)
    return ConsensusErrorResult(
        trigger_rate=float(gates.mean()),
        steady_error=float(errs[-tail:].mean()),
        err_curve=errs,
        gate_curve=gates,
    )


def sweep_trigger_vs_error(
    rule: str,
    *,
    lam_thr_grid: np.ndarray | None = None,
    n_seeds: int = 8,
    **kw,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """扫 λ 阈值 → (触发率, 稳态误差) 曲线（门控）。返回 (p_comm, mean_err, std_err)。"""
    if lam_thr_grid is None:
        lam_thr_grid = np.array([0.3, 0.6, 0.9, 1.1, 1.4, 1.8, 2.5, 3.5, 5.0])
    ps, ms, ss = [], [], []
    for lt in lam_thr_grid:
        prs, ers = [], []
        for s in range(n_seeds):
            res = run_sandbox(rule, gate=ConflictGate(lam_thr=float(lt), K=30),
                              seed=s, **kw)
            prs.append(res.trigger_rate)
            ers.append(res.steady_error)
        ps.append(np.mean(prs))
        ms.append(np.mean(ers))
        ss.append(np.std(ers))
    order = np.argsort(ps)
    return np.array(ps)[order], np.array(ms)[order], np.array(ss)[order]


def measure_skip_bound(
    rule: str,
    *,
    n: int = 12,
    d: int = 4,
    steps: int = 5000,
    sigma: float = 0.25,
    seed: int = 0,
    aggregate: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """有效性验证 (B1 / Proposition skip)：测量"跳过一轮协商所放弃的惩罚改进"。

    两种度量：
      * aggregate=False（per-agent）：参考取邻域共识 r_d=(Wx)_d（Eq. ci_dim），
        对朝该参考做收缩的 average/nash 天然非扩张（ΔP_i≥0）；不适用随机成对 gossip。
      * aggregate=True（系统级）：参考取全局共识均值 x̄，惩罚为系统级 L1 分歧
        P=Σ_{i,d}|x_{i,d}-x̄_d|/R。由三角不等式 |x_i-x̄|+|x_j-x̄|≥2|m-x̄|，
        average / gossip / best-response 在该度量下均非扩张，可统一验证三规则（含 gossip）。
        x 轴用平均冲突 CĪ=(1/N)Σ_i CI_i。

    命题断言 0 ≤ ΔP ≤ L·(Σδ)，即所有点落在界线之下，且 ΔP→0 当冲突→0。
    通过随机突发扫出宽范围的冲突，再对同一状态施加一轮协商算子 𝒩(rule) 测实际惩罚下降。
    返回 (ci, realized_drop, bound)：per-agent 模式按 (状态×agent) 展平；aggregate 模式按状态。
    """
    rng = np.random.default_rng(seed)
    W = _metropolis_mixing(n)
    g2, gN = spectral_gap(W)
    lam = 2.0 / (g2 + gN)
    R = 6.0
    x = rng.standard_normal((n, d)) * 3.0
    shock_rate, shock_mag, base_sig = 0.06, sigma * 8.0, sigma * 0.1
    ci_all, drop_all, bound_all = [], [], []
    for t in range(steps):
        x = x + base_sig * rng.standard_normal(x.shape)
        if rng.random() < shock_rate:
            k = rng.integers(0, n)
            x[k] = x[k] + shock_mag * rng.standard_normal(d)
        r = x.mean(axis=0, keepdims=True) if aggregate else (W @ x)
        e = np.abs(x - r) / R                        # per-dim normalized gap δ_d (n×d)
        x_next, _ = negotiate(rule, x, W, lam, rng)  # one negotiation round 𝒩
        e_next = np.abs(x_next - r) / R              # gap to the SAME pre-round reference
        if aggregate:
            ci_all.append(e.mean())                  # mean conflict CĪ over all agents/dims
            drop_all.append(e.sum() - e_next.sum())  # system-level ΔP = Σ_{i,d} δ drop
            bound_all.append(e.sum())                # bound = L·Σδ = L·N|D|·CĪ
        else:
            ci_all.append(e.mean(axis=1))            # CI_i per agent
            drop_all.append(e.sum(axis=1) - e_next.sum(axis=1))
            bound_all.append(e.sum(axis=1))          # bound = L|D_i|·CI_i
        x = x_next
    if aggregate:
        return np.asarray(ci_all), np.asarray(drop_all), np.asarray(bound_all)
    return (np.concatenate(ci_all), np.concatenate(drop_all), np.concatenate(bound_all))


def sweep_gate_frontier(
    rule: str,
    *,
    K_grid: np.ndarray | None = None,
    lam_thr: float = 1.2,
    n_seeds: int = 12,
    **kw,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """门控可达前沿：以 fail-safe K 为主控杆平滑扫触发率（配合固定相对阈值 lam_thr）。

    相较 sweep_trigger_vs_error（扫 lam_thr，因 CI 双峰而只在 1/K 地板与高触发两端聚集、
    中段留空导致绘图直线插值假象），本函数用 K 连续调节 fail-safe 地板 1/K，
    在论文真实工作区（通信稀缺，约 1/12）稠密采样，得到公平可比的门控权衡曲线。

    返回按触发率升序的 (p_comm, mean_err, std_err)。
    """
    if K_grid is None:
        K_grid = np.array([2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 40])
    ps, ms, ss = [], [], []
    for K in K_grid:
        prs, ers = [], []
        for s in range(n_seeds):
            res = run_sandbox(rule, gate=ConflictGate(lam_thr=lam_thr, K=int(K)),
                              seed=s, **kw)
            prs.append(res.trigger_rate)
            ers.append(res.steady_error)
        ps.append(np.mean(prs))
        ms.append(np.mean(ers))
        ss.append(np.std(ers))
    order = np.argsort(ps)
    return np.array(ps)[order], np.array(ms)[order], np.array(ss)[order]


def baseline_trigger_vs_error(
    rule: str,
    schedule: str,
    *,
    period_grid: np.ndarray | None = None,
    n_seeds: int = 8,
    **kw,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """周期/随机基线的 (触发率, 稳态误差) 曲线，用于同预算对比。"""
    if period_grid is None:
        period_grid = np.array([1, 2, 3, 5, 8, 12, 20, 40])
    ps, ms, ss = [], [], []
    for pd in period_grid:
        prs, ers = [], []
        for s in range(n_seeds):
            res = run_sandbox(rule, forced_schedule=schedule, period=int(pd),
                              seed=s, **kw)
            prs.append(res.trigger_rate)
            ers.append(res.steady_error)
        ps.append(np.mean(prs))
        ms.append(np.mean(ers))
        ss.append(np.std(ers))
    order = np.argsort(ps)
    return np.array(ps)[order], np.array(ms)[order], np.array(ss)[order]
