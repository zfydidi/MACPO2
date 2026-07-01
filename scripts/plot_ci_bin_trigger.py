#!/usr/bin/env python3
"""
Mechanism check: P(communication | conflict quantile) from pooled run logs.

Bins: equal-count quintiles on pooled conflict (CI proxy); Q1 = lowest conflict.
Y-axis: mean gate_comm (empirical trigger probability) per bin.

Example:
  cd /path/to/MACPO2
  python3 scripts/plot_ci_bin_trigger.py \\
    --runs-dir experiments/patent_paired_comparison/raw/RL-MACPO \\
    --functions F1 F2 F3 F4 F5 F6 \\
    --out RL_MACPO_IEEE_English_with_images/media/ci_bin_trigger_F1_F6.pdf

Use patent paired logs (gate_comm populated). ``output/RL-output_runs25_rho`` is for RL
trajectory diagnostics only (gate_comm all zero).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.ci_bin_trigger import analyze_function_dir
from utils.mpl_font import setup_cjk_font

setup_cjk_font()

import matplotlib.pyplot as plt
import numpy as np

from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu, style_axes_reference


def main() -> None:
    ap = argparse.ArgumentParser(description="P(communication | conflict bin) plot")
    ap.add_argument("--runs-dir", type=Path, required=True)
    ap.add_argument(
        "--functions",
        nargs="+",
        default=["F1", "F2", "F3", "F4", "F5", "F6"],
    )
    ap.add_argument("--n-bins", type=int, default=5)
    ap.add_argument(
        "--source",
        choices=("trajectory", "meta"),
        default="trajectory",
        help="trajectory: pooled conflict quintiles + mean gate_comm; "
        "meta: aggregate # CI_BIN_TRIGGER footer",
    )
    ap.add_argument(
        "--exclude-iter0",
        action="store_true",
        help="Drop iter==0 rows (paired init forces first-round communication)",
    )
    ap.add_argument("--out", "-o", type=Path, required=True)
    ap.add_argument("--ncols", type=int, default=None)
    ap.add_argument("--w-per-panel", type=float, default=2.85)
    ap.add_argument("--h-per-panel", type=float, default=2.5)
    args = ap.parse_args()

    n_fn = len(args.functions)
    ncols = args.ncols if args.ncols is not None else (n_fn if n_fn <= 3 else 3)
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
        res = analyze_function_dir(
            args.runs_dir,
            fn,
            n_bins=args.n_bins,
            source=args.source,
            exclude_iter0=args.exclude_iter0,
        )

        x = np.arange(1, res.n_bins + 1)
        colors = plt.cm.plasma(np.linspace(0.15, 0.85, res.n_bins))

        ax.bar(
            x,
            res.trigger_prob,
            yerr=res.std_trigger,
            capsize=3,
            color=colors,
            edgecolor="0.3",
            linewidth=0.6,
        )
        ax.set_ylim(0.0, 1.05)
        ax.set_xticks(x)
        ax.set_xticklabels([f"Q{b + 1}" for b in range(res.n_bins)], fontsize=8, fontfamily="DejaVu Sans")
        ax.set_ylabel("P(communication)", fontsize=9, fontfamily="DejaVu Sans")
        xlabel = (
            "Mean-CI quantile (per run)"
            if args.source == "meta"
            else "Conflict quantile (equal count)"
        )
        ax.set_xlabel(xlabel, fontsize=8, fontfamily="DejaVu Sans")
        style_axes_reference(ax)
        ax.grid(False, axis="x")
        ax.set_title(fn, fontsize=10, fontfamily="DejaVu Sans")
        set_numeric_tick_font_dejavu(ax)

        if res.spearman_rho is not None and res.spearman_rho >= 0.15:
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
            summary_lines.append(
                f"{fn}: Spearman rho(conflict, gate_comm) = {res.spearman_rho:.4f} "
                f"(n_pts={res.n_points})"
            )

        if args.source == "meta":
            bin_range_lines.append(f"{fn} CI_BIN_TRIGGER pooled (bin0 = lowest mean CI):")
            for b in range(res.n_bins):
                bin_range_lines.append(
                    f"  Q{b + 1}: p_comm={res.trigger_prob[b]:.4f} n={res.count[b]}"
                )
        else:
            bin_range_lines.append(f"{fn} conflict range per bin (scientific):")
            for b in range(res.n_bins):
                bin_range_lines.append(
                    f"  Q{b + 1}: [{res.conflict_lo[b]:.4e}, {res.conflict_hi[b]:.4e}] "
                    f"p_comm={res.trigger_prob[b]:.4f} n={res.count[b]}"
                )
        bin_range_lines.append("")

    for j in range(n_fn, axes_arr.size):
        axes_arr[j].set_visible(False)

    fig.suptitle(
        "Communication trigger rate by conflict quantile",
        fontsize=10,
        fontfamily="DejaVu Sans",
    )

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
                f"source={args.source}",
                f"exclude_iter0={args.exclude_iter0}",
                f"layout_ncols={ncols}",
                "",
                "Quantile bins: equal count on pooled conflict; Q1 = lowest conflict.",
                "trigger_prob = mean gate_comm within each bin.",
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
