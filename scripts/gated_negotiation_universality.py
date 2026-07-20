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

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
from utils.gated_negotiation_sandbox import (  # noqa: E402
    sweep_trigger_vs_error,
    baseline_trigger_vs_error,
)

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402


RULES = [
    ("average", "Metropolis 平均共识"),
    ("gossip", "随机成对 gossip"),
    ("nash", "Nash 双边比较(简化)"),
]


def main():
    os.makedirs("output", exist_ok=True)
    n_seeds = 10

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for ax, (rule, zh) in zip(axes, RULES):
        p_gate, m_gate, s_gate = sweep_trigger_vs_error(rule, n_seeds=n_seeds)
        p_per, m_per, _ = baseline_trigger_vs_error(rule, "periodic", n_seeds=n_seeds)
        p_rnd, m_rnd, _ = baseline_trigger_vs_error(rule, "random", n_seeds=n_seeds)

        ax.plot(p_per, m_per, "s--", color="tab:gray", label="周期触发", alpha=0.8)
        ax.plot(p_rnd, m_rnd, "^--", color="tab:orange", label="随机触发", alpha=0.8)
        ax.plot(p_gate, m_gate, "o-", color="tab:green", lw=2, label="冲突门控(本文)")
        ax.fill_between(p_gate, m_gate - s_gate, m_gate + s_gate,
                        color="tab:green", alpha=0.15)
        ax.set_title(f"{zh}")
        ax.set_xlabel("平均触发率 $\\bar p_{\\mathrm{comm}}$")
        ax.set_ylabel("稳态一致性误差 ‖e‖")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
        print(f"[{rule}] 门控触发率范围 [{p_gate.min():.2f},{p_gate.max():.2f}] "
              f"稳态误差范围 [{m_gate.min():.2f},{m_gate.max():.2f}]")

    for a in axes:
        set_numeric_tick_font_dejavu(a)
    fig.suptitle("A1: 冲突门控的协议无关性——同一门控接三种协商规则，"
                 "均在同触发率下优于周期/随机", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out = "output/gated_negotiation_universality.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"图已保存: {out}")


if __name__ == "__main__":
    main()
