#!/usr/bin/env python3
"""
Single-run diagnostic: conflict and mean penalty weight vs FES on F3 and F5 (high-conflict cases).

Shades iterations with conflict above/below the temporal median and annotates mean alpha in each half.
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


def _fmt_fes_k(x: float, _pos: int) -> str:
    axv = abs(x)
    if axv >= 1e6:
        return f"{x/1e6:.1f}M"
    if axv >= 1e3:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"


def _alpha_key(cd: dict) -> str | None:
    for n in ("avg_alpha", "alpha_avg"):
        if n in cd:
            return n
    return None


def _plot_one(ax_l, ax_r, path: Path, title: str) -> None:
    parsed = load_llso_final_txt(path)
    cd = column_dict(parsed)
    if "eval" not in cd or "conflict" not in cd:
        raise KeyError(f"Need eval, conflict in {path}")
    x = cd["eval"]
    c = np.asarray(cd["conflict"], dtype=float)
    ak = _alpha_key(cd)
    if ak is None:
        raise KeyError(f"No avg_alpha/alpha_avg in {path}")
    a = np.asarray(cd[ak], dtype=float)

    med = float(np.median(c))
    low_mask = c <= med
    high_mask = ~low_mask

    x_arr = np.asarray(x, dtype=float)

    def _shade_contiguous(mask: np.ndarray, color: str) -> None:
        """Shade each maximal contiguous index run where mask is True."""
        n = len(mask)
        i = 0
        while i < n:
            if not mask[i]:
                i += 1
                continue
            j = i
            while j < n and mask[j]:
                j += 1
            x0, x1 = float(x_arr[i]), float(x_arr[j - 1])
            ax_l.axvspan(x0, x1, color=color, alpha=0.35, zorder=0)
            i = j

    _shade_contiguous(low_mask, "#cfe2f3")
    _shade_contiguous(high_mask, "#fce5cd")

    ax_l.plot(x_arr, c, color="C0", lw=1.4, zorder=2, label="conflict")
    ax_l.set_ylabel("Conflict (proxy)")
    ax_l.grid(True, alpha=0.35)
    ax_l.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    ymax = float(np.nanmax(np.abs(a)))
    scale = 1e6 if ymax >= 1e5 else 1.0
    ya = a / scale
    ax_r.plot(x_arr, ya, color="C3", lw=1.2, zorder=2, label="mean alpha")
    ax_r.set_ylabel("Mean alpha" + (" (scaled 1e6)" if scale >= 1e5 else ""))
    ax_r.grid(True, alpha=0.35)
    ax_r.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

    def _m(mk: np.ndarray) -> str:
        if not np.any(mk):
            return "N/A"
        return f"{float(np.mean(a[mk])):.3g}"

    txt = (
        f"median conflict: {med:.3g}\n"
        f"mean alpha (c<=median): {_m(low_mask)}\n"
        f"mean alpha (c>median): {_m(high_mask)}"
    )
    ax_l.text(
        0.02,
        0.98,
        txt,
        transform=ax_l.transAxes,
        va="top",
        ha="left",
        fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.88),
        zorder=5,
    )
    ax_l.set_title(title, fontsize=9, pad=6)


def main() -> None:
    setup_cjk_font()
    mpl.rcParams["axes.unicode_minus"] = False

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--f3",
        type=Path,
        default=_REPO_ROOT / "RL-MACPO" / "output" / "F3_LLSO_final_panel_fair_f6.txt",
    )
    ap.add_argument(
        "--f5",
        type=Path,
        default=_REPO_ROOT / "RL-MACPO" / "output" / "F5_LLSO_final_panel_fair_f6.txt",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT
        / "RL_MACPO_IEEE_English_with_images"
        / "media"
        / "f3_f5_conflict_alpha_micro.pdf",
    )
    args = ap.parse_args()

    fig, axes = plt.subplots(2, 1, figsize=(6.8, 5.2), constrained_layout=True, sharex=False)
    for ax, p, lab in (
        (axes[0], args.f3, "F3 (homogeneous Rosenbrock)"),
        (axes[1], args.f5, "F5 (heterogeneous Elliptic--Rosenbrock)"),
    ):
        ax_l = ax
        ax_r = ax.twinx()
        _plot_one(ax_l, ax_r, p, lab)

    axes[1].set_xlabel("Cumulative evaluations (FES)")
    for tick in axes[1].get_xticklabels():
        tick.set_fontfamily("DejaVu Sans")

    fig.canvas.draw()
    for ax in fig.axes:
        for tick in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
            tick.set_fontfamily("DejaVu Sans")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, format="pdf", bbox_inches="tight")
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
