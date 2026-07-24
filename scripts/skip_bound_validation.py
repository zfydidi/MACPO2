"""B1: skip-bound validation (system-level non-expansive penalty).

Run:  python scripts/skip_bound_validation.py --lang en \\
        --out RL_MACPO_IEEE_English_with_images/media/skip_bound_validation.pdf

Synthetic validation (demo_mode): sandbox conflict shocks; not production NDO runs.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

demo_mode = True  # synthetic skip-bound check; keep out of production data paths

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
from utils.pub_figure import apply_pub_style, panel_label  # noqa: E402
from utils.gated_negotiation_sandbox import measure_skip_bound  # noqa: E402

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

RULES_ZH = [("average", "Metropolis 平均共识"), ("gossip", "随机成对 gossip"),
            ("nash", "Nash 双边最佳响应(简化)")]
RULES_EN = [("average", "Metropolis averaging"), ("gossip", "Randomized gossip"),
            ("nash", "Best-response (simplified)")]
N_AGENTS, D_DIMS = 12, 4
PANEL = "abc"
TXT = {
    "zh": {"xlabel": "平均冲突 $\\overline{\\mathrm{CI}}$",
           "ylabel": "系统级放弃改进 $\\Delta P$",
           "bound": "理论上界", "pts": "实测"},
    "en": {"xlabel": "Mean conflict $\\overline{\\mathrm{CI}}$",
           "ylabel": "System-level forgone $\\Delta P$",
           "bound": "Theory bound", "pts": "Measured"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/skip_bound_validation.png")
    args = ap.parse_args()
    txt = TXT[args.lang]
    rules = RULES_EN if args.lang == "en" else RULES_ZH
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

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35))
    slope = N_AGENTS * D_DIMS
    for ax, (rule, name), letter in zip(axes, rules, PANEL):
        # demo_mode: synthetic sandbox; measure_skip_bound uses rng conflict shocks
        ci, drop, bound = measure_skip_bound(rule, aggregate=True)
        holds = float(np.mean(drop <= bound + 1e-9))
        ratio = drop / np.maximum(bound, 1e-12)
        idx = np.random.default_rng(0).choice(ci.size, size=min(4000, ci.size), replace=False)
        ax.scatter(ci[idx], drop[idx], s=3, alpha=0.28, color="tab:green",
                   rasterized=True, label=txt["pts"])
        ax.axhline(0.0, color="0.5", lw=0.6)
        xline = np.linspace(0, max(ci.max(), 1e-6), 80)
        ax.plot(xline, slope * xline, "-", color="tab:red", lw=1.3, label=txt["bound"])
        # data-driven y-limit so the bound is readable but not empty space-dominated
        y_hi = max(float(np.percentile(drop, 99.5)) * 1.35, float(drop.max()) * 1.05, 1e-3)
        ax.set_xlim(0, ci.max() * 1.02)
        ax.set_ylim(min(0.0, float(drop.min()) * 1.05), y_hi)
        hold_txt = (f"bound holds {holds*100:.0f}%" if args.lang == "en"
                    else f"界成立 {holds*100:.0f}%")
        p95 = float(np.percentile(ratio, 95))
        ax.set_title(f"{name}\n{hold_txt}; 95th $\\Delta P$/bound={p95:.2f}")
        ax.set_xlabel(txt["xlabel"])
        ax.set_ylabel(txt["ylabel"])
        ax.grid(alpha=0.25, lw=0.5)
        ax.legend(loc="upper left", handlelength=1.4)
        panel_label(ax, letter)
        set_numeric_tick_font_dejavu(ax)
        print(f"[{rule}] holds {holds*100:.1f}%  p95 ratio={p95:.3f}  "
              f"corr={np.corrcoef(ci, drop)[0,1]:.3f}")

    fig.tight_layout(pad=0.4)
    fig.savefig(args.out, dpi=600, bbox_inches="tight")
    _base, _ = os.path.splitext(args.out)
    fig.savefig(_base + ".svg", bbox_inches="tight")
    print(f"saved: {args.out} (+ svg)")


if __name__ == "__main__":
    main()
