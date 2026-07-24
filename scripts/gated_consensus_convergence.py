"""B2: numerical validation of the intermittent gated-consensus convergence rate.

Proposition (intermittent gated negotiation): gating at trigger rate p turns the
consensus recursion e^{t+1}=(I-lambda L)e^t into an effective-gain-(p*lambda)
recursion, so the expected disagreement decays at rate
    rho(p*lambda) = max(|1 - p*lambda*gamma_2|, |1 - p*lambda*gamma_N|),
converging iff p*lambda < 2/gamma_N. This script checks that the empirical
first-moment decay rate of real Bernoulli-gated consensus runs matches rho(p*lambda),
on two structurally different graphs. Spectral quantities reuse utils/spectral_consensus.

Run:  python scripts/gated_consensus_convergence.py --lang en \\
        --out RL_MACPO_IEEE_English_with_images/media/gated_convergence.pdf

Synthetic validation (demo_mode): Bernoulli-gated consensus on ring/ER graphs;
not production NDO/MACPO runs.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

demo_mode = True  # synthetic rate validation; keep out of production data paths

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
from utils.pub_figure import apply_pub_style, panel_label  # noqa: E402
from utils.spectral_consensus import (  # noqa: E402
    spectral_gap,
    spectral_radius,
    chebyshev_optimal_gain,
)

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402


TXT = {
    "zh": {
        "pred": "一阶矩理论 $\\rho(p\\lambda)$", "emp": "一阶矩实测",
        "pred_ms": "均方理论 $\\rho_{\\mathrm{ms}}$", "emp_ms": "均方实测",
        "xlabel": "触发率 $p=\\bar p_{\\mathrm{comm}}$", "ylabel": "每轮误差衰减率",
        "thr": "一阶矩阈值",
        "ring": "环形网络", "er": "随机图 (ER)",
    },
    "en": {
        "pred": "First moment $\\rho(p\\lambda)$", "emp": "First moment (meas.)",
        "pred_ms": "Mean square $\\rho_{\\mathrm{ms}}$", "emp_ms": "Mean square (meas.)",
        "xlabel": "Trigger rate $p=\\bar p_{\\mathrm{comm}}$", "ylabel": "Per-loop error decay rate",
        "thr": "First-moment limit",
        "ring": "Ring graph", "er": "Random graph (ER)",
    },
}


def ring_mixing(n: int, sw: float = 0.5) -> np.ndarray:
    W = np.zeros((n, n))
    for i in range(n):
        for j in ((i - 1) % n, (i + 1) % n):
            W[i, j] = (1 - sw) / 2
        W[i, i] = sw
    return W


def er_mixing(n: int, seed: int = 3, pedge: float = 0.35) -> np.ndarray:
    """连通 Erdős–Rényi 图上的 Metropolis–Hastings 双随机混合矩阵。"""
    rng = np.random.default_rng(seed)
    while True:
        A = (rng.random((n, n)) < pedge).astype(float)
        A = np.triu(A, 1)
        A = A + A.T
        deg = A.sum(1)
        if np.all(deg > 0):
            break
    W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if A[i, j] > 0:
                W[i, j] = 1.0 / (1.0 + max(deg[i], deg[j]))
        W[i, i] = 1.0 - W[i].sum()
    return W


def empirical_rate(W: np.ndarray, lam: float, p: float, *, T: int = 300,
                   reps: int = 6000, seed: int = 0) -> float:
    """真实 Bernoulli 间歇共识的一阶矩（期望误差）几何衰减率。

    对多条随机门控轨迹求 e_t 的向量均值 => E[e_t]，再拟合 ‖E[e_t]‖ 的几何率。
    """
    n = W.shape[0]
    L = np.eye(n) - W
    rng = np.random.default_rng(seed)
    e0 = rng.standard_normal(n)
    e0 -= e0.mean()
    e0 /= np.linalg.norm(e0)
    acc = np.zeros((T, n))
    for _ in range(reps):
        e = e0.copy()
        for t in range(T):
            acc[t] += e
            if rng.random() < p:
                e = e - lam * (L @ e)
    mean_e = acc / reps
    norms = np.linalg.norm(mean_e, axis=1)
    # 取衰减明显、未触数值下限的窗口拟合几何率
    valid = norms > 1e-10
    idx = np.flatnonzero(valid)
    if idx.size < 5:
        return float("nan")
    lo, hi = idx[len(idx) // 4], idx[-1]
    slope = (np.log(norms[hi]) - np.log(norms[lo])) / (hi - lo)
    return float(np.exp(slope))


def empirical_ms_rate(W: np.ndarray, lam: float, p: float, *, T: int = 300,
                      reps: int = 8000, seed: int = 1) -> float:
    """真实 Bernoulli 间歇共识的均方 E‖e_t‖^2 几何衰减率。"""
    n = W.shape[0]
    L = np.eye(n) - W
    rng = np.random.default_rng(seed)
    e0 = rng.standard_normal(n)
    e0 -= e0.mean()
    e0 /= np.linalg.norm(e0)
    S = np.zeros(T)
    for _ in range(reps):
        e = e0.copy()
        for t in range(T):
            S[t] += e @ e
            if rng.random() < p:
                e = e - lam * (L @ e)
    S /= reps
    valid = S > 1e-12
    idx = np.flatnonzero(valid)
    if idx.size < 5:
        return float("nan")
    lo, hi = idx[len(idx) // 4], idx[-1]
    slope = (np.log(S[hi]) - np.log(S[lo])) / (hi - lo)
    return float(np.exp(slope))


def panel(ax, W, name, txt, ps, letter: str):
    g2, gN = spectral_gap(W)
    lam = chebyshev_optimal_gain(g2, gN)
    rho = spectral_radius(lam, g2, gN)
    pred = [spectral_radius(p * lam, g2, gN) for p in ps]
    emp = [empirical_rate(W, lam, p) for p in ps]
    pred_ms = [(1 - p) + p * rho ** 2 for p in ps]
    emp_ms = [empirical_ms_rate(W, lam, p) for p in ps]
    p_thr = 2.0 / (lam * gN)
    ax.plot(ps, pred, "-", color="tab:blue", lw=1.4, label=txt["pred"])
    ax.plot(ps, emp, "o", color="tab:blue", ms=4, mfc="none", label=txt["emp"])
    ax.plot(ps, pred_ms, "-", color="tab:green", lw=1.4, label=txt["pred_ms"])
    ax.plot(ps, emp_ms, "s", color="tab:green", ms=4, mfc="none", label=txt["emp_ms"])
    ax.axhline(1.0, ls="--", color="0.5", lw=0.7)
    if p_thr <= ps[-1]:
        ax.axvline(p_thr, ls=":", color="tab:red", lw=0.9, label=txt["thr"])
    ax.set_title(f"{name}  ($\\gamma_2$={g2:.3f}, $\\gamma_N$={gN:.3f}, $\\lambda^\\star$={lam:.2f})")
    ax.set_xlabel(txt["xlabel"])
    ax.set_ylabel(txt["ylabel"])
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(loc="best", handlelength=1.5)
    panel_label(ax, letter)
    print(f"[{name}] 1st max|pred-emp|={np.nanmax(np.abs(np.array(pred)-np.array(emp))):.4f}  "
          f"MS max|pred-emp|={np.nanmax(np.abs(np.array(pred_ms)-np.array(emp_ms))):.4f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/gated_consensus_convergence.png")
    args = ap.parse_args()
    txt = TXT[args.lang]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    apply_pub_style(font_size=7.0)
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
    })

    ps = np.linspace(0.05, 1.0, 12)
    # synthetic graph demo boundary: Bernoulli intermittent consensus on ring/ER
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.55))
    panel(axes[0], ring_mixing(12), txt["ring"], txt, ps, "a")
    panel(axes[1], er_mixing(16), txt["er"], txt, ps, "b")
    for a in axes:
        set_numeric_tick_font_dejavu(a)
    fig.tight_layout(pad=0.4)
    fig.savefig(args.out, dpi=600, bbox_inches="tight")
    _base, _ = os.path.splitext(args.out)
    fig.savefig(_base + ".svg", bbox_inches="tight")
    print(f"saved: {args.out} (+ svg)")


if __name__ == "__main__":
    main()
