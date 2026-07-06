#!/usr/bin/env python3
"""
合成 F1–F6 为 2×3 面板图（两行三列）：纵轴统一 10²–10¹²（6 个主刻度），横轴 4 个刻度，
每子图标题为函数名，坐标轴标签为 Evaluations / fitness，刻度朝内。
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.mpl_font import setup_cjk_font
from utils.fes_plot import plot_fes_panel_2x3

FUNCS = ["F1", "F2", "F3", "F4", "F5", "F6"]


def collect_paths(func: str, directory: str, exid: str, n_runs: int, side: str) -> list[str]:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exid", default="paper_r01")
    ap.add_argument("--n_runs", type=int, default=25)
    ap.add_argument(
        "--out",
        default=os.path.join(
            ROOT, "RL_MACPO_IEEE_English_with_images", "media", "fes", "F1_F6_panel.pdf"
        ),
    )
    ap.add_argument(
        "--macpo_dir",
        default=os.path.join(ROOT, "MACPO_sourcecode", "output_runs25"),
    )
    ap.add_argument(
        "--rl_dir",
        default=os.path.join(ROOT, "RL-MACPO", "output_runs25"),
    )
    args = ap.parse_args()

    items: list[tuple[str, list[str], list[str]]] = []
    for fn in FUNCS:
        macpo_files = collect_paths(fn, args.macpo_dir, args.exid, args.n_runs, "macpo")
        rl_files = collect_paths(fn, args.rl_dir, args.exid, args.n_runs, "rl")
        if not macpo_files or not rl_files:
            print(f"Abort {fn}: MACPO={len(macpo_files)} RL={len(rl_files)}", file=sys.stderr)
            sys.exit(1)
        items.append((fn, macpo_files, rl_files))

    plot_fes_panel_2x3(items, args.out, setup_font=setup_cjk_font)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
