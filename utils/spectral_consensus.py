"""
谱-自适应共识控制器（Spectral-Adaptive Consensus Controller）
================================================================

统一建模：MACPO / MASO-IE / MA-ES / MASO-CC 都是"探索算子 + 共识算子"的交替，
被同一个共识增益 λ 耦合。共识误差在共识流形附近的线性化动力学为：

    e^{t+1} = (I - λ (I - W)) e^t + η^t,   E||η||^2 = σ_expl^2

误差算子谱半径 ρ(λ) = max(|1 - λ γ_2|, |1 - λ γ_N|)，其中 γ_2 为图拉普拉斯
(I - W) 的谱间隙（代数连通度），γ_N 为最大特征值。三大病理是同一条 ρ(λ) 曲线的越界：

  * 早熟/死锁：λ γ_2 过大 → 探索被吞噬
  * 振荡/拉锯：λ γ_N > 2  → 高频模态发散
  * 孤岛/分裂：γ_2 → 0    → 图代数断裂

本模块提供根本性解法的三个组件（无梯度、仅用邻居差分即可估计）：
  (A) 谱间隙感知的 Chebyshev 最优增益  λ* = 2 / (γ_2 + γ_N)
  (B) 双时间尺度探索方差退火          σ^t ∝ t^{-κ}
  (C) 谱间隙下界护栏（防孤岛）        约束 γ_2 >= γ_min

这是 utils/ 单一真源，供 MACPO/baseline 实验脚本 import 复用，不要在脚本内重写。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


def laplacian_spectrum(W: np.ndarray) -> np.ndarray:
    """返回 (I - W) 的实部特征值升序数组。W 为混合矩阵（行随机或对称双随机）。

    对一般（可能非对称）W，(I-W) 可能有复特征值；线性化收敛由其模控制，
    这里返回按实部排序的特征值，谱量用其实部（对对称双随机 W 精确）。
    """
    n = W.shape[0]
    L = np.eye(n) - W
    ev = np.linalg.eigvals(L)
    return np.sort(ev.real)


def num_connected_components(W: np.ndarray, tol: float = 1e-9) -> int:
    """(I - W) 的零特征值重数 = 图的连通分量数。>1 即已孤岛化/分裂。"""
    ev = laplacian_spectrum(W)
    return int(np.sum(np.abs(ev) <= tol))


def spectral_gap(W: np.ndarray) -> tuple[float, float]:
    """返回 (γ_2, γ_N)：谱间隙（第二小非零特征值）与最大特征值实部。"""
    ev = laplacian_spectrum(W)
    gamma_N = float(ev[-1])
    # γ_2 = Fiedler 值 = 按重数排序的第 2 小特征值。
    # 图不连通(有>=2个零特征值)时 γ_2=0，真实反映代数断裂/孤岛。
    gamma_2 = float(ev[1]) if ev.size >= 2 else 0.0
    gamma_2 = max(gamma_2, 0.0)
    return gamma_2, gamma_N


def chebyshev_optimal_gain(gamma_2: float, gamma_N: float) -> float:
    """component (A): 令两端 |1 - λγ| 相等的最优共识增益。

    λ* = 2 / (γ_2 + γ_N)，对应最小可达谱半径 ρ* = (γ_N - γ_2)/(γ_N + γ_2)。
    """
    denom = gamma_2 + gamma_N
    if denom <= 0:
        return 0.0
    return 2.0 / denom


def spectral_radius(lam: float, gamma_2: float, gamma_N: float) -> float:
    """误差算子谱半径 ρ(λ) = max(|1 - λγ_2|, |1 - λγ_N|)。"""
    return max(abs(1.0 - lam * gamma_2), abs(1.0 - lam * gamma_N))


def stability_interval(gamma_N: float) -> tuple[float, float]:
    """标量增益的稳定区间 (0, 2/γ_N)。超出上界即触发振荡（ρ > 1）。"""
    return (0.0, 2.0 / gamma_N if gamma_N > 0 else np.inf)


def estimate_gamma_poweriter(
    W: np.ndarray, iters: int = 50, seed: int | None = 0
) -> tuple[float, float]:
    """无梯度地用功率迭代估计 (γ_2, γ_N)，仅需矩阵-向量积（等价于一轮邻居交换）。

    - γ_N：对 L = I - W 直接功率迭代。
    - γ_2：在与全 1 向量正交的子空间做功率迭代（对对称 L 得第二小特征值）。
    这模拟"每个 agent 只用邻居差分"即可在线估计谱量，无需中心化特征分解。
    """
    rng = np.random.default_rng(seed)
    n = W.shape[0]
    L = np.eye(n) - W
    Ls = 0.5 * (L + L.T)  # 对称化用于稳健的实谱估计

    # γ_N: 最大特征值
    v = rng.standard_normal(n)
    v /= np.linalg.norm(v)
    for _ in range(iters):
        v = Ls @ v
        v /= np.linalg.norm(v) + 1e-300
    gamma_N = float(v @ (Ls @ v))

    # γ_2: 反向功率迭代在 1⊥ 子空间（用 (cI - L) 的功率迭代取最小非零）
    ones = np.ones(n) / np.sqrt(n)
    shift = gamma_N * 1.05
    u = rng.standard_normal(n)
    u -= (u @ ones) * ones
    u /= np.linalg.norm(u) + 1e-300
    for _ in range(iters):
        u = shift * u - Ls @ u
        u -= (u @ ones) * ones  # 投影掉一致性方向
        u /= np.linalg.norm(u) + 1e-300
    lam_shifted = float(u @ (shift * u - Ls @ u))
    gamma_2 = float(shift - lam_shifted)
    return max(gamma_2, 0.0), gamma_N


@dataclass
class SpectralConsensusController:
    """谱-自适应双时间尺度共识控制器。

    参数
    ----
    gamma_min : 谱间隙下界护栏 (C)，防止孤岛化。<=0 表示关闭护栏。
    sigma0    : 初始探索标准差。
    kappa     : 探索退火指数 σ^t = sigma0 * (1 + t)^{-kappa} (双时间尺度 B)。
    ema       : 谱量在线估计的 EMA 系数（稳健对抗噪声）。
    """

    gamma_min: float = 0.05
    sigma0: float = 1.0
    kappa: float = 0.51  # >0.5 保证随机逼近可和平方可和
    ema: float = 0.3
    _g2: float = field(default=None, repr=False)
    _gN: float = field(default=None, repr=False)

    def guard_mixing(self, W: np.ndarray) -> np.ndarray:
        """(C) 谱间隙护栏：若 γ_2 < gamma_min，注入最小全局混合权，
        从代数上禁止图分裂成不可调和的块。返回修正后的混合矩阵。
        """
        if self.gamma_min <= 0:
            return W
        g2, _ = spectral_gap(W)
        if g2 >= self.gamma_min:
            return W
        n = W.shape[0]
        J = np.ones((n, n)) / n  # 全连接均匀混合（fully-mixing）
        # 凸组合注入最小连通性：W' = (1-ε)W + εJ，选 ε 使 γ_2 达标
        # (I-J) 对 1⊥ 子空间是恒等，故 γ_2(W') ≈ (1-ε)γ_2(W) + ε
        eps = min(1.0, max(0.0, (self.gamma_min - g2) / (1.0 - g2 + 1e-12)))
        return (1.0 - eps) * W + eps * J

    def gain(self, W: np.ndarray, use_powiter: bool = False) -> float:
        """(A) 返回当前谱-自适应增益 λ*，带 EMA 平滑。"""
        if use_powiter:
            g2, gN = estimate_gamma_poweriter(W)
        else:
            g2, gN = spectral_gap(W)
        g2 = max(g2, self.gamma_min if self.gamma_min > 0 else g2)
        # EMA 平滑（在线、抗噪）
        self._g2 = g2 if self._g2 is None else (1 - self.ema) * self._g2 + self.ema * g2
        self._gN = gN if self._gN is None else (1 - self.ema) * self._gN + self.ema * gN
        return chebyshev_optimal_gain(self._g2, self._gN)

    def sigma(self, t: int) -> float:
        """(B) 双时间尺度探索标准差 σ^t = sigma0 (1+t)^{-kappa}。"""
        return self.sigma0 * (1.0 + t) ** (-self.kappa)

    def step(
        self, x: np.ndarray, W: np.ndarray, t: int, rng: np.random.Generator
    ) -> np.ndarray:
        """执行一步"共识算子 + 探索算子"更新。

        x : (N, d) 各 agent 当前解。
        W : (N, N) 混合矩阵。
        返回更新后的 (N, d)。
        """
        W = self.guard_mixing(W)
        lam = self.gain(W)
        # 共识算子：x <- x - λ (I - W) x = (1-λ)x + λ W x
        L = np.eye(W.shape[0]) - W
        consensus = x - lam * (L @ x)
        # 探索算子：退火随机扰动
        expl = self.sigma(t) * rng.standard_normal(x.shape)
        return consensus + expl
