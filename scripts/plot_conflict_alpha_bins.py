#!/usr/bin/env python3
"""
Optional diagnostic: high-conflict quantile bins vs mean alpha (pooled over runs).

**Bins:** All (conflict, alpha) points are pooled, sorted by conflict, then split into
``n_bins`` groups with equal counts (quantile bins). Q1 = lowest-conflict quintile,
Q5 = highest. Exact conflict ranges per bin are listed in the ``.txt`` meta file next
to the PDF — not on the x-axis (avoids overlapping tick labels).

Example:
  cd /path/to/MACPO2
  python3 scripts/plot_conflict_alpha_bins.py \\
    --runs-dir output/RL-output_runs25_rho \\
    --functions F1 F2 F3 F4 F5 F6 \\
    --n-bins 5 \\
    --ncols 3 \\
    --y-scale auto \\
    --out RL_MACPO_IEEE_English_with_images/media/conflict_alpha_bins_F1_F6.pdf

Axis ticks use ASCII scientific notation. For many benchmarks, use ``--ncols`` to
avoid an overly wide figure (e.g. 3 columns × 2 rows for six functions).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.conflict_alpha_bins import analyze_function_dir
from utils.mpl_font import setup_cjk_font

setup_cjk_font()

import matplotlib as mpl

mpl.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from utils.mpl_sci_ticks import (
    fmt_tick_sci_ascii,
    set_numeric_tick_font_dejavu,
    style_axes_reference,
)


def _scale_alpha(y: np.ndarray) -> tuple[np.ndarray, float]:
    """Scale large alpha for plotting; magnitude appears in tick labels, not axis title."""
    m = float(np.nanmax(np.abs(y)))
    if m >= 1e5:
        return y / 1e6, 1e6
    return y, 1.0


def _should_use_log_y(mean_s: np.ndarray, ratio_threshold: float = 25.0) -> bool:
    """If tallest bar is >> shortest positive bar, linear y compresses low bins."""
    m = np.asarray(mean_s, dtype=float)
    pos = m[m > 0]
    if pos.size == 0:
        return False
    r = float(np.nanmax(m) / max(np.nanmin(pos), 1e-300))
    return r >= ratio_threshold


def _bar_mean_std(
    ax,
    x: np.ndarray,
    mean_s: np.ndarray,
    std_s: np.ndarray,
    colors,
    *,
    log_y: bool,
) -> None:
    """Bar + error caps; use log y when bins span orders of magnitude."""
    mean_s = np.asarray(mean_s, dtype=float)
    std_s = np.asarray(std_s, dtype=float)
    mean_s = np.maximum(mean_s, 1e-300)
    lo = np.maximum(mean_s - std_s, mean_s * 1e-4)
    hi = mean_s + std_s

    if log_y:
        ax.bar(x, mean_s, color=colors, edgecolor="0.3", linewidth=0.6)
        ax.errorbar(
            x,
            mean_s,
            yerr=[mean_s - lo, hi - mean_s],
            fmt="none",
            ecolor="0.2",
            capsize=3,
            elinewidth=1.0,
        )
    else:
        ax.bar(
            x,
            mean_s,
            yerr=std_s,
            capsize=3,
            color=colors,
            edgecolor="0.3",
            linewidth=0.6,
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Conflict–alpha quantile bin plot")
    ap.add_argument("--runs-dir", type=Path, required=True)
    ap.add_argument(
        "--functions",
        nargs="+",
        default=["F3", "F5"],
        help="Benchmark ids (default: F3 F5)",
    )
    ap.add_argument("--n-bins", type=int, default=5)
    ap.add_argument("--out", "-o", type=Path, required=True)
    ap.add_argument(
        "--ncols",
        type=int,
        default=None,
        help="Subplot columns (default: all in one row if ≤3 functions, else 3)",
    )
    ap.add_argument(
        "--w-per-panel",
        type=float,
        default=2.85,
        help="Panel width in inches (default: 2.85)",
    )
    ap.add_argument(
        "--h-per-panel",
        type=float,
        default=2.5,
        help="Panel height in inches (default: 2.5)",
    )
    ap.add_argument(
        "--y-scale",
        choices=("auto", "linear", "log"),
        default="auto",
        help="auto: log y if max/min mean alpha across bins exceeds ~25x (default)",
    )
    args = ap.parse_args()

    n_fn = len(args.functions)
    if args.ncols is not None:
        ncols = max(1, args.ncols)
    elif n_fn <= 3:
        ncols = n_fn
    else:
        ncols = 3
    nrows = int(np.ceil(n_fn / ncols))

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(args.w_per_panel * ncols, args.h_per_panel * nrows),
        constrained_layout=True,
    )
    axes_arr = np.atleast_1d(axes).ravel()

    summary_lines: list[str] = []
    bin_range_lines: list[str] = []

    for idx, fn in enumerate(args.functions):
        ax = axes_arr[idx]
        res = analyze_function_dir(args.runs_dir, fn, n_bins=args.n_bins)
        mean_s, scale = _scale_alpha(res.mean_alpha)
        std_s = res.std_alpha / scale

        x = np.arange(1, res.n_bins + 1)
        colors = plt.cm.viridis(np.linspace(0.2, 0.85, res.n_bins))

        if args.y_scale == "log":
            use_log = True
        elif args.y_scale == "linear":
            use_log = False
        else:
            use_log = _should_use_log_y(mean_s)

        if use_log:
            ax.set_yscale("log")
        _bar_mean_std(ax, x, mean_s, std_s, colors, log_y=use_log)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_tick_sci_ascii))

        ax.set_xticks(x)
        # Only Q1..Qk on ticks — per-bin [lo,hi] strings overlap badly when bars are narrow.
        labels = [f"Q{b + 1}" for b in range(res.n_bins)]
        ax.set_xticklabels(labels, fontsize=8, fontfamily="DejaVu Sans")
        ax.set_ylabel("Mean alpha +/- std", fontsize=9, fontfamily="DejaVu Sans")
        ax.set_xlabel(
            "Conflict quantile (equal count)",
            fontsize=8,
            fontfamily="DejaVu Sans",
        )
        style_axes_reference(ax)
        ax.grid(False, axis="x")
        ax.set_title(fn, fontsize=10, fontfamily="DejaVu Sans")
        set_numeric_tick_font_dejavu(ax)

        if res.spearman_rho is not None:
            ax.text(
                0.98,
                0.98,
                f"rho = {res.spearman_rho:.3f}",
                transform=ax.transAxes,
                fontsize=7,
                verticalalignment="top",
                horizontalalignment="right",
                fontfamily="DejaVu Sans",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.35),
            )
            summary_lines.append(f"{fn}: Spearman rho = {res.spearman_rho:.4f} (n_pts={res.n_points})")

        bin_range_lines.append(f"{fn} conflict range per bin (scientific):")
        for b in range(res.n_bins):
            bin_range_lines.append(
                f"  Q{b + 1}: [{res.conflict_lo[b]:.4e}, {res.conflict_hi[b]:.4e}]"
            )
        bin_range_lines.append("")

    for j in range(n_fn, axes_arr.size):
        axes_arr[j].set_visible(False)

    fig.suptitle("Mean alpha by conflict bin", fontsize=10, fontfamily="DejaVu Sans")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", bbox_inches="tight")

    meta = out.with_suffix(".txt")
    meta.write_text(
        "\n".join(
            [
                f"runs_dir={args.runs_dir.resolve()}",
                f"functions={' '.join(args.functions)}",
                f"n_bins={args.n_bins}",
                f"layout_ncols={ncols}",
                "",
                "Quantile bins: equal count on pooled conflict; Q1 = lowest conflict, Q5 = highest.",
                "",
                *bin_range_lines,
                *summary_lines,
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out.resolve()}")
    print(f"Meta  {meta.resolve()}")


if __name__ == "__main__":
    main()
