#!/usr/bin/env python3
"""
Single-run F1 fair plot (MACPO vs RL-MACPO); delegates to utils.fes_plot.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.mpl_font import setup_cjk_font
from utils.fes_plot import plot_macpo_vs_rl


def main():
    fair_macpo = os.path.join(ROOT, "MACPO_sourcecode", "output_fair", "F1_LLSO_f1_fair_r01.txt")
    fair_rl = os.path.join(ROOT, "RL-MACPO", "output", "F1_LLSO_final_f1_fair_r01.txt")
    ap = argparse.ArgumentParser()
    ap.add_argument("--macpo", nargs="*", default=None)
    ap.add_argument("--rl", nargs="*", default=None)
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "RL_MACPO_IEEE_English_with_images", "media", "FES.pdf"),
    )
    ap.add_argument("--title", default="F1: MACPO vs RL-MACPO (fair logging + best-so-far)")
    args = ap.parse_args()

    macpo_files = args.macpo if args.macpo is not None else ([fair_macpo] if os.path.isfile(fair_macpo) else [])
    rl_files = args.rl if args.rl is not None else ([fair_rl] if os.path.isfile(fair_rl) else [])

    if not macpo_files or not rl_files:
        print("Need MACPO and RL trace files.", file=sys.stderr)
        sys.exit(1)

    plot_macpo_vs_rl(macpo_files, rl_files, args.out, args.title, setup_font=setup_cjk_font)
    print("Saved", args.out)


if __name__ == "__main__":
    main()
