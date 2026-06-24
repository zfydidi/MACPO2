#!/usr/bin/env python3
"""
Mean ± std over many RL-MACPO runs — **one PDF per metric** (alpha, rho, conflict, reward).

Layout: grid of subplots, one benchmark per subplot. Title = function id (e.g. F2);
y-axis = short metric name (left); each subplot has its own x-axis label and sparse ticks.
Inward ticks, light grid; large dynamic range uses log y with minor log ticks (“ruler”).

Example:
  cd /path/to/MACPO2
  python3 scripts/plot_rl_metrics_runs25_by_metric.py \\
    --runs-dir output/RL-output_runs25_rho \\
    --functions F1 F2 F3 F4 F5 F6 \\
    --out-dir RL_MACPO_IEEE_English_with_images/media \\
    --file-tag mean25_rho
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.mpl_font import setup_cjk_font

setup_cjk_font()

import matplotlib as mpl

mpl.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
import numpy as np

from utils.mpl_sci_ticks import (
    set_numeric_tick_font_dejavu,
    set_xaxis_eval_sci_sparse,
    set_yaxis_log_ruler,
    set_yaxis_sci_linear,
    style_axes_reference,
)
from utils.rl_macpo_metrics_agg import aggregate_by_eval, glob_run_files, resolve_column
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt


def _has_column(paths: list[Path], col: str) -> bool:
    if not paths:
        return False
    try:
        cd = column_dict(load_llso_final_txt(paths[0]))
        return col in cd
    except (OSError, ValueError, KeyError):
        return False


def _should_log_y(mean_y: np.ndarray, *, ratio_threshold: float = 50.0) -> bool:
    m = np.asarray(mean_y, dtype=float)
    pos = m[m > 0]
    if pos.size == 0:
        return False
    return float(np.nanmax(m) / max(np.nanmin(pos), 1e-300)) >= ratio_threshold


def _plot_alpha(ax, paths: list[Path], n_grid: int) -> None:
    col = resolve_column(paths, "avg_alpha", "alpha_avg")
    eg, m, s, _ = aggregate_by_eval(paths, col, n_grid=n_grid)
    m = np.asarray(m, float)
    s = np.asarray(s, float)
    scale = 1e6 if float(np.nanmax(m)) >= 1e5 else 1.0
    m_s, s_s = m / scale, s / scale
    lo, hi = m_s - s_s, m_s + s_s
    if _should_log_y(m_s):
        m_pos = np.maximum(m_s, 1e-300)
        lo = np.maximum(m_pos - s_s, m_pos * 1e-4)
        hi = m_pos + s_s
        ax.fill_between(eg, lo, hi, alpha=0.35, color="C0")
        ax.plot(eg, m_pos, color="C0", lw=1.3)
        set_yaxis_log_ruler(ax)
    else:
        ax.fill_between(eg, lo, hi, alpha=0.35, color="C0")
        ax.plot(eg, m_s, color="C0", lw=1.3)
        set_yaxis_sci_linear(ax)
    ax.set_ylabel("Mean alpha +/- std")


def _plot_rho_or_penalty(ax, paths: list[Path], n_grid: int) -> None:
    if _has_column(paths, "rho_avg"):
        eg, m, s, _ = aggregate_by_eval(paths, "rho_avg", n_grid=n_grid)
        ax.fill_between(eg, m - s, m + s, alpha=0.35, color="C1")
        ax.plot(eg, m, color="C1", lw=1.3)
        set_yaxis_sci_linear(ax)
        ax.set_ylabel("Mean rho +/- std")
        return
    eg, m, s, _ = aggregate_by_eval(paths, "penalty", n_grid=n_grid)
    m = np.maximum(np.asarray(m, float), 1e-300)
    s = np.clip(np.asarray(s, float), 0, None)
    if _should_log_y(m):
        lo = np.maximum(m - s, 1e-300)
        hi = m + s
        ax.fill_between(eg, lo, hi, alpha=0.35, color="C1")
        ax.plot(eg, m, color="C1", lw=1.3)
        set_yaxis_log_ruler(ax)
        ax.set_ylabel("Penalty +/- std")
    else:
        ax.fill_between(eg, m - s, m + s, alpha=0.35, color="C1")
        ax.plot(eg, m, color="C1", lw=1.3)
        set_yaxis_sci_linear(ax)
        ax.set_ylabel("Penalty +/- std")


def _plot_conflict(ax, paths: list[Path], n_grid: int) -> None:
    eg, m, s, _ = aggregate_by_eval(paths, "conflict", n_grid=n_grid)
    m = np.maximum(np.asarray(m, float), 1e-300)
    s = np.asarray(s, float)
    lo = np.maximum(m - s, 1e-300)
    hi = m + s
    ax.fill_between(eg, lo, hi, alpha=0.35, color="C2")
    ax.plot(eg, m, color="C2", lw=1.3)
    set_yaxis_log_ruler(ax)
    ax.set_ylabel("Conflict +/- std")


def _plot_reward(ax, paths: list[Path], n_grid: int) -> None:
    eg, m, s, _ = aggregate_by_eval(paths, "reward", n_grid=n_grid)
    ax.fill_between(eg, m - s, m + s, alpha=0.35, color="C3")
    ax.plot(eg, m, color="C3", lw=1.3)
    ax.set_ylim(-1.05, 0.15)
    set_yaxis_sci_linear(ax)
    ax.set_ylabel("Reward +/- std")


def _column_for_metric(paths: list[Path], metric: str) -> str:
    if metric == "alpha":
        return resolve_column(paths, "avg_alpha", "alpha_avg")
    if metric == "rho":
        return "rho_avg" if _has_column(paths, "rho_avg") else "penalty"
    if metric == "conflict":
        return "conflict"
    return "reward"


def _metric_suptitle(metric: str, example_paths: list[Path]) -> str:
    """Short figure title (no run count); rho vs penalty follows first benchmark file."""
    if metric == "alpha":
        return "Mean alpha"
    if metric == "rho":
        return "Mean rho" if _has_column(example_paths, "rho_avg") else "Penalty"
    if metric == "conflict":
        return "Conflict"
    return "Reward"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="One PDF per RL metric: mean ± std over runs, subplot per function."
    )
    ap.add_argument("--runs-dir", type=Path, required=True)
    ap.add_argument(
        "--functions",
        nargs="+",
        default=["F1", "F2", "F3", "F4", "F5", "F6"],
        help="Benchmark ids in subplot order (default: F1 … F6)",
    )
    ap.add_argument("--out-dir", type=Path, required=True, help="Directory for PDF outputs")
    ap.add_argument(
        "--file-tag",
        type=str,
        default="",
        help="Optional tag in filenames, e.g. mean25_rho → rl_metrics_mean25_rho_<metric>.pdf",
    )
    ap.add_argument(
        "--ncols",
        type=int,
        default=2,
        help="Subplot columns (default: 2)",
    )
    ap.add_argument("--n-grid", type=int, default=256, help="Interpolation grid size")
    ap.add_argument(
        "--x-max-ticks",
        type=int,
        default=5,
        help="Max major ticks on the x (evaluations) axis per subplot (default: 5, reduces overlap)",
    )
    ap.add_argument(
        "--metrics",
        nargs="+",
        choices=("alpha", "rho", "conflict", "reward"),
        default=["alpha", "rho", "conflict", "reward"],
        help="Which metrics to export (default: all four)",
    )
    args = ap.parse_args()

    runs_dir = args.runs_dir
    if not runs_dir.is_dir():
        raise SystemExit(f"Not a directory: {runs_dir.resolve()}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = args.file_tag.strip()
    prefix = "rl_metrics"
    if tag:
        prefix = f"{prefix}_{tag}"

    dispatch = {
        "alpha": _plot_alpha,
        "rho": _plot_rho_or_penalty,
        "conflict": _plot_conflict,
        "reward": _plot_reward,
    }

    n_fn = len(args.functions)
    ncols = max(1, int(args.ncols))
    nrows = int(np.ceil(n_fn / ncols))

    for metric in args.metrics:
        example_paths = glob_run_files(runs_dir, args.functions[0])
        if len(example_paths) < 2:
            raise SystemExit(
                f"Need at least 2 run files for {args.functions[0]} under {runs_dir}"
            )

        fig, axes = plt.subplots(
            nrows,
            ncols,
            figsize=(4.2 * ncols, 3.2 * nrows),
            constrained_layout=True,
            sharex=True,
            sharey=False,
        )
        axes_arr = np.atleast_1d(axes).ravel()

        n_used_global = 0
        for i, fn in enumerate(args.functions):
            ax = axes_arr[i]
            paths = glob_run_files(runs_dir, fn)
            if len(paths) < 2:
                raise SystemExit(f"Need at least 2 run files for {fn} under {runs_dir}")
            dispatch[metric](ax, paths, args.n_grid)
            col = _column_for_metric(paths, metric)
            n_used_global = aggregate_by_eval(paths, col, n_grid=args.n_grid)[3]

            ax.yaxis.label.set_fontfamily("DejaVu Sans")
            ax.set_title(fn, fontsize=11, fontfamily="DejaVu Sans")
            style_axes_reference(ax)
            set_numeric_tick_font_dejavu(ax)

        for j in range(n_fn, axes_arr.size):
            axes_arr[j].set_visible(False)

        # sharex=True hides x tick labels on non-bottom rows; force every used axis to show them.
        set_xaxis_eval_sci_sparse(axes_arr[0], max_ticks=args.x_max_ticks)
        for i in range(n_fn):
            axes_arr[i].tick_params(axis="x", which="major", labelbottom=True)
            axes_arr[i].set_xlabel(
                "Cumulative evaluations",
                fontfamily="DejaVu Sans",
            )
            set_numeric_tick_font_dejavu(axes_arr[i])

        fig.suptitle(
            _metric_suptitle(metric, example_paths),
            fontsize=10,
            fontfamily="DejaVu Sans",
        )

        out = out_dir / f"{prefix}_{metric}.pdf"
        fig.savefig(out, format="pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out.resolve()} (n_runs={n_used_global}, metric={metric})")


if __name__ == "__main__":
    main()