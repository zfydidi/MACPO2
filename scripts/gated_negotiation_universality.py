"""
A1: 冲突门控的协议无关性验证（通用协商沙盘）
=============================================

论证：论文的冲突门控只依赖黑箱 CI 与触发信号，与底层协商范式无关。
把**同一个门控层**接到三种结构不同的协商规则（average / gossip / nash）上，
比较"触发率 vs 稳态一致性误差"的权衡曲线，并与同预算的周期/随机触发对比。

结论若成立：三种规则下门控曲线都位于周期/随机基线的下方（同触发率误差更低），
说明"低冲突时跳过协商不掉质量"是门控层本身的性质，而非 MACPO negotiation 专属。

运行:  python scripts/gated_negotiation_universality.py
输出:  output/gated_negotiation_universality.png
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
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
        "sub": "同预算门控更优: vs周期 {a:.0f}% / vs随机 {b:.0f}%",
        "sup": "A1: 冲突门控的协议无关性——同一门控接三种结构不同的协商规则，"
               "在通信稀缺工作区均达到不劣于/优于周期与随机触发的权衡",
    },
    "en": {
        "peri": "Periodic", "rnd": "Random", "gate": "Conflict gate (ours)",
        "xlabel": "Average trigger rate $\\bar p_{\\mathrm{comm}}$",
        "ylabel": "Steady consensus error $\\|e\\|$",
        "sub": "Gate better at matched budget: vs periodic {a:.0f}\\% / vs random {b:.0f}\\%",
        "sup": "Protocol-agnostic conflict gating: one gate on three structurally different "
               "negotiation rules, matching or beating periodic/random at scarce budget",
    },
}

# 聚焦通信稀缺工作区（论文默认约 1/12≈0.08），p→1 时各法平凡收敛不再有区分度。
P_LO, P_HI = 0.03, 0.6
PERIOD_GRID = np.array([2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 30, 40])


def _win_rate(p_gate, m_gate, p_base, m_base):
    """在门控每个触发率点上插值基线误差，统计门控更优（误差更低）的比例。"""
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
    n_seeds = args.seeds

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for ax, (rule, name) in zip(axes, rules):
        p_gate, m_gate, s_gate = sweep_gate_frontier(rule, n_seeds=n_seeds)
        p_per, m_per, _ = baseline_trigger_vs_error(
            rule, "periodic", period_grid=PERIOD_GRID, n_seeds=n_seeds)
        p_rnd, m_rnd, _ = baseline_trigger_vs_error(
            rule, "random", period_grid=PERIOD_GRID, n_seeds=n_seeds)

        win_per = _win_rate(p_gate, m_gate, p_per, m_per)
        win_rnd = _win_rate(p_gate, m_gate, p_rnd, m_rnd)

        ax.plot(p_per, m_per, "s--", color="tab:gray", label=txt["peri"], alpha=0.85)
        ax.plot(p_rnd, m_rnd, "^--", color="tab:orange", label=txt["rnd"], alpha=0.85)
        ax.plot(p_gate, m_gate, "o-", color="tab:green", lw=2, label=txt["gate"])
        ax.fill_between(p_gate, m_gate - s_gate, m_gate + s_gate,
                        color="tab:green", alpha=0.15)
        ax.set_xlim(P_LO, P_HI)
        ax.set_title(f"{name}\n" + txt["sub"].format(a=win_per * 100, b=win_rnd * 100),
                     fontsize=10)
        ax.set_xlabel(txt["xlabel"])
        ax.set_ylabel(txt["ylabel"])
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        print(f"[{rule}] gate p∈[{p_gate.min():.3f},{p_gate.max():.3f}] "
              f"err∈[{m_gate.min():.2f},{m_gate.max():.2f}] "
              f"win vs periodic={win_per*100:.0f}% vs random={win_rnd*100:.0f}%")

    for a in axes:
        set_numeric_tick_font_dejavu(a)
    fig.suptitle(txt["sup"], fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"图已保存: {args.out}")


if __name__ == "__main__":
    main()
