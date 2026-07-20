"""
数值验证：统一建模下的三大病理（早熟/振荡/孤岛）及谱-自适应解法。

对比对象：
  - 固定小增益 λ（模拟 MACPO 惩罚过小 / MASO-IE 外部因子过小）: 收敛慢、残留大
  - 固定大增益 λ > 2/γ_N（模拟惩罚过大 / MA-ES 盲目拉锯）    : 振荡/发散
  - 谱-自适应 Chebyshev 增益（本文解法 A+B）                : 最优谱半径、稳定收敛
  - 分裂网络 + 无护栏 vs 有护栏 (C)                          : 孤岛化 vs 全局共识

运行:  python scripts/spectral_consensus_demo.py
输出:  output/spectral_consensus_demo.png
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.spectral_consensus import (  # noqa: E402
    SpectralConsensusController,
    chebyshev_optimal_gain,
    spectral_gap,
    spectral_radius,
    stability_interval,
)
from utils.mpl_sci_ticks import set_yaxis_log_ruler, set_numeric_tick_font_dejavu  # noqa: E402

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402


def ring_mixing(n: int, self_weight: float = 0.5) -> np.ndarray:
    """稀疏环形网络（病态图：γ_N/γ_2 大），Metropolis 双随机混合。"""
    W = np.zeros((n, n))
    for i in range(n):
        nbrs = [(i - 1) % n, (i + 1) % n]
        for j in nbrs:
            W[i, j] = (1 - self_weight) / 2
        W[i, i] = self_weight
    return W


def two_block_mixing(n: int, cross: float) -> np.ndarray:
    """两个团块 + 极弱跨块连接（模拟 MASO-CC 贡献度导致的孤岛化）。cross 越小越易分裂。"""
    W = np.zeros((n, n))
    half = n // 2
    for i in range(n):
        block = range(0, half) if i < half else range(half, n)
        peers = [j for j in block if j != i]
        for j in peers:
            W[i, j] = (1 - 0.4) / len(peers)
        W[i, i] = 0.4
    # 极弱跨块桥
    W[half - 1, half] += cross
    W[half, half - 1] += cross
    W[half - 1, half - 1] -= cross
    W[half, half] -= cross
    return W


def run(W, gain_fn, sigma0, kappa, steps, guard, seed=0):
    """通用一致性误差仿真。gain_fn: (W) -> λ 或 'adaptive'。"""
    n = W.shape[0]
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, 1)) * 3.0  # 初始分散
    L = np.eye(n) - W
    ctrl = SpectralConsensusController(gamma_min=guard, sigma0=sigma0, kappa=kappa)
    errs = []
    for t in range(steps):
        Wt = ctrl.guard_mixing(W) if guard > 0 else W
        Lt = np.eye(n) - Wt
        lam = ctrl.gain(Wt) if gain_fn == "adaptive" else gain_fn
        sig = ctrl.sigma(t) if kappa is not None else sigma0
        x = x - lam * (Lt @ x) + sig * rng.standard_normal(x.shape)
        e = x - x.mean(axis=0, keepdims=True)
        errs.append(float(np.linalg.norm(e)))
    return np.array(errs)


def main():
    os.makedirs("output", exist_ok=True)
    n = 12
    W = ring_mixing(n)
    g2, gN = spectral_gap(W)
    lam_star = chebyshev_optimal_gain(g2, gN)
    lo, hi = stability_interval(gN)
    steps = 400

    print(f"环形网络: N={n}, γ_2={g2:.4f}, γ_N={gN:.4f}, 条件数 γ_N/γ_2={gN/g2:.1f}")
    print(f"稳定区间 λ∈(0,{hi:.3f}), Chebyshev最优 λ*={lam_star:.3f}, ρ*={spectral_radius(lam_star,g2,gN):.4f}")

    e_small = run(W, 0.15 * lam_star, sigma0=0.0, kappa=None, steps=steps, guard=0)
    e_big = run(W, 1.02 * hi, sigma0=0.0, kappa=None, steps=steps, guard=0)
    e_adapt = run(W, "adaptive", sigma0=0.0, kappa=None, steps=steps, guard=0)

    # 孤岛化：两团块几乎断桥（谱间隙塌陷）。加入持续探索噪声，暴露稳态残差差异
    Wb = two_block_mixing(n, cross=0.0)  # 完全分裂：图不连通
    g2b, _ = spectral_gap(Wb)
    print(f"两团块网络: γ_2={g2b:.5f} (谱间隙塌陷/断裂→孤岛)")
    e_island = run(Wb, "adaptive", sigma0=0.3, kappa=0.0, steps=steps, guard=0)
    e_guard = run(Wb, "adaptive", sigma0=0.3, kappa=0.0, steps=steps, guard=0.1)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

    ax = axes[0]
    ax.plot(e_small, label="固定小 λ (惩罚过小/早熟)", color="tab:orange")
    ax.plot(e_big, label="固定大 λ>2/γ_N (振荡/发散)", color="tab:red")
    ax.plot(e_adapt, label="谱-自适应 λ* (本文解法)", color="tab:green", lw=2)
    set_yaxis_log_ruler(ax)
    ax.set_title("(a) 病态稀疏网络：三大失效 vs 谱自适应")
    ax.set_xlabel("迭代步")
    ax.set_ylabel("一致性误差 ‖e‖")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[1]
    lams = np.linspace(1e-3, 1.2 * hi, 400)
    rhos = [spectral_radius(l, g2, gN) for l in lams]
    ax.plot(lams, rhos, color="tab:blue")
    ax.axhline(1.0, ls="--", color="gray", label="ρ=1 (振荡阈值)")
    ax.axvline(lam_star, ls=":", color="tab:green", label=f"λ*={lam_star:.2f}")
    ax.axvline(hi, ls=":", color="tab:red", label=f"2/γ_N={hi:.2f}")
    ax.set_title("(b) 谱半径 ρ(λ)：所有病理是同一曲线的越界")
    ax.set_xlabel("共识增益 λ")
    ax.set_ylabel("误差算子谱半径 ρ")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[2]
    ax.plot(e_island, label="无护栏 (孤岛化/共识分裂)", color="tab:red")
    ax.plot(e_guard, label="谱间隙护栏 (C) 恢复全局共识", color="tab:green", lw=2)
    set_yaxis_log_ruler(ax)
    ax.set_title("(c) 团块网络：谱间隙护栏防孤岛")
    ax.set_xlabel("迭代步")
    ax.set_ylabel("一致性误差 ‖e‖")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    for a in axes:
        set_numeric_tick_font_dejavu(a)
    fig.tight_layout()
    out = "output/spectral_consensus_demo.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"图已保存: {out}")


if __name__ == "__main__":
    main()
