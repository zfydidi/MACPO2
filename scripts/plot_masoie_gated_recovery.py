"""A2 operating-point recovery: terminal fitness vs trigger rate for gated MASOIE.

Reads the default-gate ablation (masoie_gated_ablation.json) and the fail-safe-K
sweep (masoie_gated_ksweep.json), and plots normalized fitness (gated / always-on)
against the average trigger rate for the consensus-critical functions F2, F4 and the
consensus-tolerant F6. Values below the parity line (ratio = 1) beat always-on MASOIE.
Shows that a gentler gate (smaller K -> higher trigger rate) recovers F2/F4, while F6
is improved at every setting -- consistent with Propositions~2--3 (consensus-critical
problems need a higher trigger rate).

Run:  python scripts/plot_masoie_gated_recovery.py [--lang en] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "RL_MACPO_IEEE_English_with_images", "media")
ABLATION = os.path.join(MEDIA, "masoie_gated_ablation.json")
KSWEEP = os.path.join(MEDIA, "masoie_gated_ksweep.json")

FUNCS = ["F2", "F4", "F6"]
COLORS = {"F2": "tab:red", "F4": "tab:orange", "F6": "tab:green"}
TXT = {
    "zh": {"xlabel": "平均触发率 $\\bar p_{\\mathrm{comm}}$",
           "ylabel": "归一化 fitness (gated / always-on)",
           "parity": "always-on 基准 (=1)",
           "title": "A2 操作点恢复：降低 fail-safe $K$ 提高触发率，共识临界的 F2/F4 恢复，F6 全程更优",
           "lab": {"F2": "F2 (共识临界)", "F4": "F4 (共识临界)", "F6": "F6 (共识宽容)"}},
    "en": {"xlabel": "Average trigger rate $\\bar p_{\\mathrm{comm}}$",
           "ylabel": "Normalized fitness (gated / always-on)",
           "parity": "Always-on parity (=1)",
           "title": "Operating-point recovery: a smaller fail-safe $K$ raises the trigger rate and recovers the consensus-critical F2/F4; F6 improves throughout",
           "lab": {"F2": "F2 (consensus-critical)", "F4": "F4 (consensus-critical)",
                   "F6": "F6 (consensus-tolerant)"}},
}


def collect(func):
    ab = json.load(open(ABLATION))
    ks = json.load(open(KSWEEP))
    ao = ab["functions"]["always_on"][func]
    ao_fit = ao["fitness"]["mean"]
    pts = []  # (trigger, fitness_ratio)
    for arm, d in ks["functions"].items():
        if func in d and arm.startswith("gated_K"):
            pts.append((d[func]["trigger_rate"]["mean"], d[func]["fitness"]["mean"] / ao_fit))
    g10 = ab["functions"]["gated"][func]
    pts.append((g10["trigger_rate"]["mean"], g10["fitness"]["mean"] / ao_fit))
    pts.sort()
    return np.array(pts), ao_fit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/masoie_gated_recovery.png")
    args = ap.parse_args()
    txt = TXT[args.lang]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for f in FUNCS:
        pts, _ = collect(f)
        ax.plot(pts[:, 0], pts[:, 1], "o-", color=COLORS[f], lw=2, ms=6, label=txt["lab"][f])
        print(f"[{f}] trigger {np.round(pts[:,0],3)} ratio {np.round(pts[:,1],3)}")
    ax.axhline(1.0, ls="--", color="gray", label=txt["parity"])
    ax.set_yscale("log")
    ax.set_xlabel(txt["xlabel"])
    ax.set_ylabel(txt["ylabel"])
    ax.set_title(txt["title"], fontsize=10)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=9)
    set_numeric_tick_font_dejavu(ax)
    fig.tight_layout()
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"图已保存: {args.out}")


if __name__ == "__main__":
    main()
