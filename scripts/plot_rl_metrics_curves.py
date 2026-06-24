#!/usr/bin/env python3
"""
Plot RL-MACPO per-iteration metrics from *_LLSO_final_*.txt.

Example (from repository root):
  python3 scripts/plot_rl_metrics_curves.py \\
    --input RL-MACPO/output/F3_LLSO_final_ex01.txt \\
    --out RL_MACPO_IEEE_English_with_images/media/rl_metrics_F3.pdf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.mpl_font import setup_cjk_font
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


def _first_col(cd: dict, *names: str) -> str | None:
    for n in names:
        if n in cd:
            return n
    return None


def _fmt_fes_k(x: float, _pos: int) -> str:
    """FES tick labels: 0, 20k, 40k, … (ASCII)."""
    if not np.isfinite(x):
        return ""
    axv = abs(x)
    if axv >= 1e6:
        return f"{x/1e6:.1f}M"
    if axv >= 1e3:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"


def _apply_log_y_formatter(ax) -> None:
    """ASCII scientific notation on log y (avoids missing superscript glyphs)."""

    def _fmt_sci_ascii(v: float, _pos: int) -> str:
        if v <= 0 or not np.isfinite(v):
            return ""
        return f"{v:.2e}"

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt_sci_ascii))


def _style_alpha_axis(ax, x: np.ndarray, y: np.ndarray) -> None:
    """Scale very large alpha for readable linear ticks (ASCII labels)."""
    ymax = float(np.nanmax(np.abs(y)))
    if ymax >= 1e5:
        s = 1e6
        ax.plot(x, y / s, lw=1.2, color="C0")
        ax.set_ylabel("Mean alpha (values divided by 1e6)")
    else:
        ax.plot(x, y, lw=1.2, color="C0")
        ax.set_ylabel("Mean alpha")


def main() -> None:
    setup_cjk_font()
    mpl.rcParams["axes.unicode_minus"] = False

    ap = argparse.ArgumentParser(description="Plot RL-MACPO metrics from *_LLSO_final_*.txt")
    ap.add_argument("--input", "-i", required=True, help="Path to F*_LLSO_final_*.txt")
    ap.add_argument("--out", "-o", required=True, help="Output PDF path")
    ap.add_argument(
        "--x",
        choices=("eval", "iter"),
        default="eval",
        help="Horizontal axis (default: eval = cumulative black-box evaluations)",
    )
    args = ap.parse_args()

    parsed = load_llso_final_txt(args.input)
    cd = column_dict(parsed)
    x_key = args.x
    if x_key not in cd:
        raise KeyError(f"Missing column {x_key} in {args.input}")
    x = cd[x_key]

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.2), constrained_layout=True)
    ax_a, ax_b = axes[0]
    ax_c, ax_d = axes[1]

    xlabel_bottom = "Cumulative evaluations (FES)" if x_key == "eval" else "Outer iteration index"

    # --- Top-left: mean alpha ---
    alpha_key = _first_col(cd, "avg_alpha", "alpha_avg")
    if alpha_key is not None:
        _style_alpha_axis(ax_a, x, cd[alpha_key])
        ax_a.legend([f"column `{alpha_key}`"], loc="upper right", fontsize=7)
    else:
        ax_a.text(0.5, 0.5, "No alpha column", ha="center", va="center", transform=ax_a.transAxes)
    ax_a.grid(True, alpha=0.35)
    ax_a.set_xlabel("")
    ax_a.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    # --- Top-right: rho, or fallback (legacy logs) ---
    rho_key = _first_col(cd, "rho_avg")
    penalty_key = _first_col(cd, "penalty")

    if rho_key is not None:
        ax_b.plot(x, cd[rho_key], lw=1.2, color="C1", label=f"`{rho_key}`")
        ax_b.set_ylabel("Mean rho (RL weight ratio)")
        ax_b.legend(loc="upper right", fontsize=7)
    elif penalty_key is not None:
        yp = np.asarray(cd[penalty_key], dtype=float)
        yp_pos = np.maximum(np.abs(yp), 1e-300)
        ratio = float(np.nanmax(yp_pos) / max(np.nanmin(yp_pos), 1e-300))
        ax_b.plot(x, yp_pos, lw=1.2, color="C1")
        if ratio > 50:
            ax_b.set_yscale("log")
            _apply_log_y_formatter(ax_b)
            ax_b.set_ylabel("Penalty term (log scale)\n(penalized minus pure)")
        else:
            ax_b.set_ylabel("Penalty term (penalized minus pure)")
        ax_b.set_title(
            "Legacy log: rho not logged — penalty magnitude instead",
            fontsize=8,
            fontstyle="italic",
            fontfamily="DejaVu Sans",
        )
    else:
        ax_b.text(
            0.5,
            0.5,
            "No rho_avg or penalty column.",
            ha="center",
            va="center",
            transform=ax_b.transAxes,
        )
    ax_b.grid(True, alpha=0.35)
    ax_b.set_xlabel("")
    ax_b.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    # --- Bottom-left: conflict ---
    if "conflict" in cd:
        yc = np.maximum(cd["conflict"], 1e-300)
        ax_c.plot(x, yc, lw=1.2, color="C0")
        ax_c.set_yscale("log")
        _apply_log_y_formatter(ax_c)
        ax_c.set_ylabel("Conflict (local, log scale)")
    else:
        ax_c.text(0.5, 0.5, "No conflict column", ha="center", va="center", transform=ax_c.transAxes)
    ax_c.grid(True, alpha=0.35)
    ax_c.set_xlabel(xlabel_bottom)
    ax_c.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    # --- Bottom-right: reward (+ optional gate) ---
    if "reward" in cd:
        ax_d.plot(x, cd["reward"], lw=1.2, color="C0")
        ax_d.set_ylabel("RL reward")
        ax_d.set_ylim(-1.05, 0.15)
    else:
        ax_d.text(0.5, 0.5, "No reward column", ha="center", va="center", transform=ax_d.transAxes)
    ax_d.grid(True, alpha=0.35)
    ax_d.set_xlabel(xlabel_bottom)
    ax_d.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    if "gate_comm" in cd:
        ax_gate = ax_d.twinx()
        ax_gate.step(x, cd["gate_comm"], where="post", color="C3", alpha=0.5, lw=0.9)
        ax_gate.set_ylabel("Negotiation gate (0/1)", color="C3")
        ax_gate.set_ylim(-0.1, 1.1)
        for t in ax_gate.get_yticklabels():
            t.set_fontfamily("DejaVu Sans")

    fig.suptitle(
        Path(args.input).name,
        fontsize=9,
        y=1.02,
        fontfamily="DejaVu Sans",
    )

    # Tick fonts: DejaVu for numeric ticks (CJK body font may lack minus/superscripts)
    fig.canvas.draw()
    for ax in fig.axes:
        for tick in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            tick.set_fontfamily("DejaVu Sans")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", bbox_inches="tight")
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
