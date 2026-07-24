"""A2: gated-MASOIE operating-point recovery (fitness vs trigger rate).

Run:  python scripts/plot_masoie_gated_recovery.py --lang en \\
        --out RL_MACPO_IEEE_English_with_images/media/masoie_gated_recovery.pdf
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
from utils.pub_figure import apply_pub_style  # noqa: E402

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "RL_MACPO_IEEE_English_with_images", "media")
ABLATION = os.path.join(MEDIA, "masoie_gated_ablation.json")
KSWEEP = os.path.join(MEDIA, "masoie_gated_ksweep.json")

FUNCS = ["F2", "F4", "F6"]
COLORS = {"F2": "#b2182b", "F4": "#ef8a62", "F6": "#1a9850"}  # colorblind-safer diverging + green
TXT = {
    "zh": {"xlabel": "平均触发率 $\\bar p_{\\mathrm{comm}}$",
           "ylabel": "归一化 fitness (gated / always-on)",
           "parity": "always-on (=1)",
           "lab": {"F2": "F2 (共识临界)", "F4": "F4 (共识临界)", "F6": "F6 (共识宽容)"}},
    "en": {"xlabel": "Average trigger rate $\\bar p_{\\mathrm{comm}}$",
           "ylabel": "Normalized fitness (gated / always-on)",
           "parity": "Always-on parity (=1)",
           "lab": {"F2": "F2 (consensus-critical)", "F4": "F4 (consensus-critical)",
                   "F6": "F6 (consensus-tolerant)"}},
}


def collect(func):
    """Return arrays (trigger, ratio, K_label) sorted by trigger rate."""
    ab = json.load(open(ABLATION))
    ks = json.load(open(KSWEEP))
    ao_fit = ab["functions"]["always_on"][func]["fitness"]["mean"]
    pts = []
    for arm, d in ks["functions"].items():
        if func in d and arm.startswith("gated_K"):
            k = int(arm.replace("gated_K", ""))
            pts.append((d[func]["trigger_rate"]["mean"],
                        d[func]["fitness"]["mean"] / ao_fit, k))
    g10 = ab["functions"]["gated"][func]
    pts.append((g10["trigger_rate"]["mean"], g10["fitness"]["mean"] / ao_fit, 10))
    pts.sort(key=lambda t: t[0])
    return np.array([p[0] for p in pts]), np.array([p[1] for p in pts]), [p[2] for p in pts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/masoie_gated_recovery.png")
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

    fig, ax = plt.subplots(figsize=(3.5, 2.6))  # ~89 mm single-column
    eps = 1e-12  # positivity guard for log axis
    for f in FUNCS:
        trig, ratio, ks = collect(f)
        ratio = np.maximum(ratio, eps)
        ax.plot(trig, ratio, "o-", color=COLORS[f], lw=1.4, ms=4.5, label=txt["lab"][f])
        for x, y, k in zip(trig, ratio, ks):
            ax.annotate(f"$K$={k}", (x, y), textcoords="offset points",
                        xytext=(3, 3), fontsize=5.5, color=COLORS[f])
        print(f"[{f}] trigger {np.round(trig,3)} ratio {np.round(ratio,3)}")
    ax.axhline(1.0, ls="--", color="0.4", lw=0.9, label=txt["parity"])
    ax.set_yscale("log")
    ax.set_xlabel(txt["xlabel"])
    ax.set_ylabel(txt["ylabel"])
    ax.grid(alpha=0.25, which="both", lw=0.5)
    ax.legend(loc="best", handlelength=1.5)
    set_numeric_tick_font_dejavu(ax)
    fig.tight_layout(pad=0.3)
    fig.savefig(args.out, dpi=600, bbox_inches="tight")
    _base, _ = os.path.splitext(args.out)
    fig.savefig(_base + ".svg", bbox_inches="tight")
    print(f"saved: {args.out} (+ svg)")


if __name__ == "__main__":
    main()
