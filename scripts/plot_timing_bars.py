#!/usr/bin/env python3
"""
从 timing_from_logs_s.csv 绘制墙钟时间柱状图：
- 按测试函数：每个 F1–F6 上 MACPO vs RL-MACPO 的 25 次运行 **平均时间**（可选 ±std）。
- 总体：两种算法各 150 次单次运行的 **平均时间**（可选 ±std）。

依赖：scripts/extract_timing_from_run_logs.py 生成的 CSV。
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.mpl_font import setup_cjk_font

import matplotlib.pyplot as plt

FUNCS = ["F1", "F2", "F3", "F4", "F5", "F6"]
COLORS = {"MACPO": "#2166ac", "RL-MACPO": "#d73027"}


def load_csv(path: str):
    """返回 func -> algorithm -> list of seconds."""
    d: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            d[row["func"]][row["algorithm"]].append(float(row["seconds_wall"]))
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--csv",
        default=os.path.join(ROOT, "MACPO_sourcecode", "output_runs25", "timing_from_logs_s.csv"),
    )
    ap.add_argument(
        "--out_dir",
        default=os.path.join(ROOT, "RL_MACPO_IEEE_English_with_images", "media", "fes"),
    )
    ap.add_argument("--no_errorbar", action="store_true", help="Do not draw std over 25 runs")
    args = ap.parse_args()

    if not os.path.isfile(args.csv):
        print("Run first: python3 scripts/extract_timing_from_run_logs.py", file=sys.stderr)
        sys.exit(1)

    setup_cjk_font()
    data = load_csv(args.csv)

    os.makedirs(args.out_dir, exist_ok=True)

    # --- By function: mean ± std over 25 runs ---
    x = np.arange(len(FUNCS))
    width = 0.35
    m_mean, m_std = [], []
    r_mean, r_std = [], []
    for fn in FUNCS:
        mv = data[fn]["MACPO"]
        rv = data[fn]["RL-MACPO"]
        m_mean.append(np.mean(mv))
        m_std.append(np.std(mv, ddof=1) if len(mv) > 1 else 0.0)
        r_mean.append(np.mean(rv))
        r_std.append(np.std(rv, ddof=1) if len(rv) > 1 else 0.0)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    yerr_m = None if args.no_errorbar else m_std
    yerr_r = None if args.no_errorbar else r_std
    ax.bar(
        x - width / 2,
        m_mean,
        width,
        label="MACPO",
        color=COLORS["MACPO"],
        yerr=yerr_m,
        capsize=3,
        ecolor="0.35",
    )
    ax.bar(
        x + width / 2,
        r_mean,
        width,
        label="RL-MACPO",
        color=COLORS["RL-MACPO"],
        yerr=yerr_r,
        capsize=3,
        ecolor="0.35",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(FUNCS)
    ax.set_ylabel("Mean wall-clock time per run (s)")
    ax.set_xlabel("Benchmark function")
    title = "Mean wall time over 25 runs (from log-reconstructed timing)"
    if not args.no_errorbar:
        title += "; error bars: std over 25 runs"
    ax.set_title(title)
    ax.legend(loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out1 = os.path.join(args.out_dir, "timing_bar_by_function.pdf")
    fig.savefig(out1, bbox_inches="tight")
    plt.close()
    print("Saved", out1)

    # --- Overall: 150 runs per algorithm ---
    all_m = []
    all_r = []
    for fn in FUNCS:
        all_m.extend(data[fn]["MACPO"])
        all_r.extend(data[fn]["RL-MACPO"])
    om, or_ = np.mean(all_m), np.mean(all_r)
    sm, sr = np.std(all_m, ddof=1), np.std(all_r, ddof=1)

    fig, ax = plt.subplots(figsize=(4.5, 4.0))
    labels = ["MACPO", "RL-MACPO"]
    means = [om, or_]
    stds = [sm, sr]
    colors = [COLORS["MACPO"], COLORS["RL-MACPO"]]
    ax.bar(
        labels,
        means,
        color=colors,
        width=0.5,
        yerr=None if args.no_errorbar else stds,
        capsize=4,
        ecolor="0.35",
    )
    ax.set_ylabel("Mean wall-clock time per run (s)")
    if args.no_errorbar:
        ax.set_title("Overall mean over 150 runs per method (F1–F6 × 25)")
    else:
        ax.set_title("Overall mean over 150 runs per method; error bars: std across runs")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out2 = os.path.join(args.out_dir, "timing_bar_overall.pdf")
    fig.savefig(out2, bbox_inches="tight")
    plt.close()
    print("Saved", out2)
    print(
        f"Summary: MACPO mean={om:.3f}s (std across 150 runs={sm:.3f}), "
        f"RL-MACPO mean={or_:.3f}s (std={sr:.3f})"
    )


if __name__ == "__main__":
    main()
