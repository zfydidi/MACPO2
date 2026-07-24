"""
A1: protocol-agnostic conflict gating (sandbox).

Same three-layer gate on Metropolis / gossip / best-response; trigger-rate vs
steady consensus error vs periodic/random at matched budget.

Run:  python scripts/gated_negotiation_universality.py --lang en \\
        --out RL_MACPO_IEEE_English_with_images/media/gated_universality.pdf
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
from utils.pub_figure import apply_pub_style, panel_label  # noqa: E402
from utils.gated_negotiation_sandbox import (  # noqa: E402
    sweep_gate_frontier,
    baseline_trigger_vs_error,
)

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

RULES_ZH = [
    ("average", "Metropolis 平均共识"),
    ("gossip", "随机成对 gossip"),
    ("nash", "Nash 双边比较(简化)"),
]
RULES_EN = [
    ("average", "Metropolis averaging"),
    ("gossip", "Randomized gossip"),
    ("nash", "Best-response (simplified)"),
]
TXT = {
    "zh": {
        "peri": "周期触发", "rnd": "随机触发", "gate": "冲突门控(本文)",
        "xlabel": "平均触发率 $\\bar p_{\\mathrm{comm}}$",
        "ylabel": "稳态一致性误差 ‖e‖",
        "sub": "同预算更优: 周期 {a:.0f}% / 随机 {b:.0f}%",
    },
    "en": {
        "peri": "Periodic", "rnd": "Random", "gate": "Conflict gate (ours)",
        "xlabel": "Average trigger rate $\\bar p_{\\mathrm{comm}}$",
        "ylabel": "Steady consensus error $\\|e\\|$",
        # matplotlib (non-usetex): use plain %; caption carries the scientific claim
        "sub": "Matched-budget win: periodic {a:.0f}% / random {b:.0f}%",
    },
}
P_LO, P_HI = 0.03, 0.6
PERIOD_GRID = np.array([2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 30, 40])
PANEL = "abc"


def _win_rate(p_gate, m_gate, p_base, m_base):
    mask = (p_gate >= p_base.min()) & (p_gate <= p_base.max())
    if mask.sum() == 0:
        return float("nan")
    base_interp = np.interp(p_gate[mask], p_base, m_base)
    return float(np.mean(m_gate[mask] < base_interp))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/gated_negotiation_universality.png")
    ap.add_argument("--seeds", type=int, default=15)
    args = ap.parse_args()
    txt = TXT[args.lang]
    rules = RULES_EN if args.lang == "en" else RULES_ZH
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    apply_pub_style(font_size=7.0)
    # nature-figure QA (must appear in this source for validate_figure.py)
    import matplotlib as mpl
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
    })

    # ~183 mm double-column width (Nature/IEEE friendly), no in-figure suptitle
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35))
    for ax, (rule, name), letter in zip(axes, rules, PANEL):
        # synthetic sandbox demo boundary: frontiers from rng shocks + gate sweeps
        p_gate, m_gate, s_gate = sweep_gate_frontier(rule, n_seeds=args.seeds)
        p_per, m_per, _ = baseline_trigger_vs_error(
            rule, "periodic", period_grid=PERIOD_GRID, n_seeds=args.seeds)
        p_rnd, m_rnd, _ = baseline_trigger_vs_error(
            rule, "random", period_grid=PERIOD_GRID, n_seeds=args.seeds)
        win_per = _win_rate(p_gate, m_gate, p_per, m_per)
        win_rnd = _win_rate(p_gate, m_gate, p_rnd, m_rnd)

        ax.plot(p_per, m_per, "s--", color="0.45", label=txt["peri"], ms=3.5, lw=1.0)
        ax.plot(p_rnd, m_rnd, "^--", color="tab:orange", label=txt["rnd"], ms=3.5, lw=1.0)
        ax.plot(p_gate, m_gate, "o-", color="tab:green", lw=1.4, ms=3.5, label=txt["gate"])
        ax.fill_between(p_gate, m_gate - s_gate, m_gate + s_gate,
                        color="tab:green", alpha=0.15)
        ax.set_xlim(P_LO, P_HI)
        ax.set_title(f"{name}\n{txt['sub'].format(a=win_per * 100, b=win_rnd * 100)}")
        ax.set_xlabel(txt["xlabel"])
        ax.set_ylabel(txt["ylabel"])
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(loc="best", handlelength=1.6)
        panel_label(ax, letter)
        set_numeric_tick_font_dejavu(ax)
        print(f"[{rule}] win vs periodic={win_per*100:.0f}% vs random={win_rnd*100:.0f}%")

    fig.tight_layout(pad=0.4)
    fig.savefig(args.out, dpi=600, bbox_inches="tight")
    _base, _ = os.path.splitext(args.out)
    fig.savefig(_base + ".svg", bbox_inches="tight")
    print(f"saved: {args.out} (+ svg)")


if __name__ == "__main__":
    main()
