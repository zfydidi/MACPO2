#!/usr/bin/env python3
"""
Mean ± std over many RL-MACPO runs (e.g. 25 seeds) for conflict-sensitive benchmarks.

Typical use (paper): F3 and F5 rows, four metrics per row — stronger than a single trace.

Example:
  cd /path/to/MACPO2
  python3 scripts/plot_rl_metrics_runs25_panel.py \\
    --runs-dir output/RL-output_runs25 \\
    --functions F3 F5 \\
    --out RL_MACPO_IEEE_English_with_images/media/rl_metrics_F3_F5_mean25.pdf
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from utils.mpl_font import setup_cjk_font
from utils.rl_macpo_metrics_agg import aggregate_by_eval, glob_run_files, resolve_column
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np


def _fmt_fes_k(x: float, _pos: int) -> str:
    if not np.isfinite(x):
        return ""
    axv = abs(x)
    if axv >= 1e6:
        return f"{x/1e6:.1f}M"
    if axv >= 1e3:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"


def _log_tick_ascii(v: float, _pos: int) -> str:
    if v <= 0 or not np.isfinite(v):
        return ""
    return f"{v:.2e}"


def _has_column(paths: list[Path], col: str) -> bool:
    if not paths:
        return False
    try:
        cd = column_dict(load_llso_final_txt(paths[0]))
        return col in cd
    except (OSError, ValueError, KeyError):
        return False


def main() -> None:
    setup_cjk_font()
    mpl.rcParams["axes.unicode_minus"] = False

    ap = argparse.ArgumentParser(
        description="Plot mean ± std RL metrics over 25 runs (F3/F5 recommended)."
    )
    ap.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("output/RL-output_runs25"),
        help="Directory containing F*_LLSO_final_run*.txt",
    )
    ap.add_argument(
        "--functions",
        nargs="+",
        default=["F3", "F5"],
        help="Benchmark ids (default: F3 F5 — conflict-highlighted in MACPO narrative)",
    )
    ap.add_argument("--out", "-o", type=Path, required=True, help="Output PDF path")
    ap.add_argument("--n-grid", type=int, default=256, help="Interpolation grid size")
    args = ap.parse_args()

    runs_dir = args.runs_dir
    if not runs_dir.is_dir():
        raise SystemExit(f"Not a directory: {runs_dir.resolve()}")

    n_fn = len(args.functions)
    fig, axes = plt.subplots(n_fn, 4, figsize=(12.5, 3.4 * n_fn), constrained_layout=True)
    if n_fn == 1:
        axes = np.array([axes])

    n_used_global = 0
    for row, fn in enumerate(args.functions):
        paths = glob_run_files(runs_dir, fn)
        if len(paths) < 2:
            raise SystemExit(f"Need at least 2 run files for {fn} under {runs_dir}")

        ax0, ax1, ax2, ax3 = axes[row]

        # --- mean alpha (scaled); 20-col: avg_alpha, legacy: alpha_avg ---
        alpha_col = resolve_column(paths, "avg_alpha", "alpha_avg")
        eg, m, s, n_used = aggregate_by_eval(paths, alpha_col, n_grid=args.n_grid)
        n_used_global = n_used
        scale = 1e6 if float(np.nanmax(m)) >= 1e5 else 1.0
        m_s, s_s = m / scale, s / scale
        ax0.fill_between(eg, m_s - s_s, m_s + s_s, alpha=0.35, color="C0")
        ax0.plot(eg, m_s, color="C0", lw=1.3)
        ax0.set_ylabel(
            f"{fn}: mean alpha (x {scale:.0e})" if scale != 1 else f"{fn}: mean alpha"
        )
        ax0.set_title("Mean alpha ± std" if row == 0 else "")
        ax0.grid(True, alpha=0.35)
        ax0.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

        # --- rho (20-col logs) or penalty (legacy 13-col) ---
        if _has_column(paths, "rho_avg"):
            eg, m, s = aggregate_by_eval(paths, "rho_avg", n_grid=args.n_grid)[:3]
            ax1.fill_between(eg, m - s, m + s, alpha=0.35, color="C1")
            ax1.plot(eg, m, color="C1", lw=1.3)
            ax1.set_ylabel(f"{fn}: mean rho")
            ax1.set_title("Mean rho ± std" if row == 0 else "")
        else:
            eg, m, s = aggregate_by_eval(paths, "penalty", n_grid=args.n_grid)[:3]
            m = np.maximum(m, 1e-300)
            s = np.clip(s, 0, None)
            ratio = float(np.nanmax(m) / max(np.nanmin(m), 1e-300))
            if ratio > 50:
                lo = np.maximum(m - s, 1e-300)
                hi = m + s
                ax1.fill_between(eg, lo, hi, alpha=0.35, color="C1")
                ax1.plot(eg, m, color="C1", lw=1.3)
                ax1.set_yscale("log")
                ax1.yaxis.set_major_formatter(mticker.FuncFormatter(_log_tick_ascii))
                ax1.set_ylabel(f"{fn}: penalty (log)")
            else:
                ax1.fill_between(eg, m - s, m + s, alpha=0.35, color="C1")
                ax1.plot(eg, m, color="C1", lw=1.3)
                ax1.set_ylabel(f"{fn}: penalty")
            ax1.set_title("Penalty term ± std" if row == 0 else "")
        ax1.grid(True, alpha=0.35)
        ax1.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

        # --- conflict (log) ---
        eg, m, s = aggregate_by_eval(paths, "conflict", n_grid=args.n_grid)[:3]
        m = np.maximum(m, 1e-300)
        lo = np.maximum(m - s, 1e-300)
        hi = m + s
        ax2.fill_between(eg, lo, hi, alpha=0.35, color="C2")
        ax2.plot(eg, m, color="C2", lw=1.3)
        ax2.set_yscale("log")
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(_log_tick_ascii))
        ax2.set_ylabel(f"{fn}: conflict (log)")
        ax2.set_title("Conflict ± std" if row == 0 else "")
        ax2.grid(True, alpha=0.35)
        ax2.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

        # --- reward ---
        eg, m, s = aggregate_by_eval(paths, "reward", n_grid=args.n_grid)[:3]
        ax3.fill_between(eg, m - s, m + s, alpha=0.35, color="C3")
        ax3.plot(eg, m, color="C3", lw=1.3)
        ax3.set_ylabel(f"{fn}: reward")
        ax3.set_title("RL reward ± std" if row == 0 else "")
        ax3.set_ylim(-1.05, 0.15)
        ax3.grid(True, alpha=0.35)
        ax3.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_fes_k))

        if row == n_fn - 1:
            for ax in (ax0, ax1, ax2, ax3):
                ax.set_xlabel("Cumulative evaluations (FES)")

    fig.suptitle(
        f"RL-MACPO: mean ± std over {n_used_global} runs per function — "
        f"{', '.join(args.functions)}",
        fontsize=10,
        fontfamily="DejaVu Sans",
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="pdf", bbox_inches="tight")
    print(f"Wrote {out.resolve()} (n_runs={n_used_global}, dir={runs_dir.resolve()})")


if __name__ == "__main__":
    main()
