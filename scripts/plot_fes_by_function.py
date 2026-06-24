#!/usr/bin/env python3
"""
Generate F1.pdf ... F6.pdf (MACPO vs RL-MACPO, FES vs best-so-far f_pure).

Single run (default):  {F}_LLSO_{exid}.txt  vs  {F}_LLSO_final_{exid}.txt
Multi run (--n_runs N): {F}_LLSO_run01..runNN.txt vs {F}_LLSO_final_run01..runNN.txt
  (same layout as MACPO_original_output/LLSO_25runs for baseline.)
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.mpl_font import setup_cjk_font
from utils.fes_plot import NO_STD_SHADE_FUNCS, plot_macpo_vs_rl

FUNCS = ["F1", "F2", "F3", "F4", "F5", "F6"]


def collect_paths(func: str, directory: str, exid: str, n_runs: int, side: str) -> list[str]:
    """
    side: 'macpo' -> {F}_LLSO_{exid}.txt or {F}_LLSO_run{i}.txt
          'rl'    -> {F}_LLSO_final_{exid}.txt or {F}_LLSO_final_run{i}.txt
    """
    paths = []
    if n_runs <= 1:
        if side == "macpo":
            paths = [os.path.join(directory, f"{func}_LLSO_{exid}.txt")]
        else:
            paths = [os.path.join(directory, f"{func}_LLSO_final_{exid}.txt")]
    else:
        for i in range(1, n_runs + 1):
            if side == "macpo":
                paths.append(os.path.join(directory, f"{func}_LLSO_run{i:02d}.txt"))
            else:
                paths.append(os.path.join(directory, f"{func}_LLSO_final_run{i:02d}.txt"))
    return [p for p in paths if os.path.isfile(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exid", default="paper_r01", help="Single-run suffix when --n_runs 1")
    ap.add_argument(
        "--n_runs",
        type=int,
        default=1,
        help="Number of independent runs. If >1, expects run01..runNN file names (see docstring).",
    )
    ap.add_argument(
        "--out_dir",
        default=os.path.join(ROOT, "RL_MACPO_IEEE_English_with_images", "media", "fes"),
        help="Output directory; each figure saved as {F1..F6}.pdf",
    )
    ap.add_argument(
        "--macpo_dir",
        default=os.path.join(ROOT, "MACPO_sourcecode", "output_fair"),
    )
    ap.add_argument(
        "--rl_dir",
        default=os.path.join(ROOT, "RL-MACPO", "output"),
    )
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    for fn in FUNCS:
        macpo_files = collect_paths(fn, args.macpo_dir, args.exid, args.n_runs, "macpo")
        rl_files = collect_paths(fn, args.rl_dir, args.exid, args.n_runs, "rl")
        out = os.path.join(args.out_dir, f"{fn}.pdf")
        if not macpo_files:
            print(f"Skip {fn}: no MACPO logs in {args.macpo_dir}", file=sys.stderr)
            continue
        if not rl_files:
            print(f"Skip {fn}: no RL-MACPO logs in {args.rl_dir}", file=sys.stderr)
            continue
        if args.n_runs > 1 and (len(macpo_files) != args.n_runs or len(rl_files) != args.n_runs):
            print(
                f"Warning {fn}: expected {args.n_runs} files per side, "
                f"got MACPO={len(macpo_files)} RL={len(rl_files)} (using what exists)",
                file=sys.stderr,
            )
        show_shade = fn not in NO_STD_SHADE_FUNCS
        if args.n_runs > 1:
            if show_shade:
                title = f"{fn}: MACPO vs RL-MACPO (mean +/- std over runs, best-so-far vs FES)"
            else:
                title = f"{fn}: MACPO vs RL-MACPO (mean over runs, best-so-far vs FES)"
        else:
            title = f"{fn}: MACPO vs RL-MACPO (best-so-far vs FES)"
        emin, emax, nm, nr = plot_macpo_vs_rl(
            macpo_files,
            rl_files,
            out,
            title,
            setup_font=setup_cjk_font,
            show_std_shade=show_shade,
        )
        print(f"Saved {out} | FES [{emin:.0f}, {emax:.0f}] | runs MACPO={nm} RL={nr}")


if __name__ == "__main__":
    main()
