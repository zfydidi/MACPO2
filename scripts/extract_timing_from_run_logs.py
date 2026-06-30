#!/usr/bin/env python3
"""
从已保存的轨迹 txt 末尾解析耗时（补录，无需重跑）。
- MACPO:  # Completed ... total time=9s
- RL-MACPO: Completed [LLSO]: ... total time=3017ms
输出 CSV: func,run_id,algorithm,seconds_wall (RL 的 ms 转为 s)
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

RE_MACPO = re.compile(r"total time\s*=\s*(\d+)\s*s", re.I)
RE_RL_MS = re.compile(r"total time\s*=\s*(\d+)\s*ms", re.I)
# RL-MACPO 写入文件末尾的 COST_STATS 行
RE_RL_COST_MS = re.compile(r"total_time_ms\s*=\s*(\d+)")
RE_MACPO_NAME = re.compile(r"^(F\d)_LLSO_(run\d+)\.txt$")
RE_RL_NAME = re.compile(r"^(F\d)_LLSO_final_(run\d+)\.txt$")


def parse_file(path: str) -> float | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            tail = f.read()[-8000:]
    except OSError:
        return None
    m = RE_RL_COST_MS.search(tail)
    if m:
        return int(m.group(1)) / 1000.0
    m = RE_RL_MS.search(tail)
    if m:
        return int(m.group(1)) / 1000.0
    m = RE_MACPO.search(tail)
    if m:
        return float(m.group(1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--macpo_dir",
        default=os.path.join(ROOT, "MACPO_original_output", "LLSO_25runs"),
        help="MACPO F1-F6 logs (F*_LLSO_run*.txt); many archives lack total time= lines",
    )
    ap.add_argument(
        "--rl_dir",
        default=os.path.join(ROOT, "output", "RL-output_runs25"),
        help="RL F1-F6 pilot logs (F*_LLSO_final_run*.txt with # COST_STATS total_time_ms)",
    )
    ap.add_argument(
        "--out",
        default=os.path.join(ROOT, "output", "RL-output_runs25", "timing_from_logs_s.csv"),
    )
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob(os.path.join(args.macpo_dir, "F*_LLSO_run*.txt"))):
        base = os.path.basename(path)
        m = RE_MACPO_NAME.match(base)
        if not m:
            continue
        func, rid = m.group(1), m.group(2)
        sec = parse_file(path)
        if sec is not None:
            rows.append((func, rid, "MACPO", f"{sec:.3f}"))

    for path in sorted(glob.glob(os.path.join(args.rl_dir, "F*_LLSO_final_run*.txt"))):
        base = os.path.basename(path)
        m = RE_RL_NAME.match(base)
        if not m:
            continue
        func, rid = m.group(1), m.group(2)
        sec = parse_file(path)
        if sec is not None:
            rows.append((func, rid, "RL-MACPO", f"{sec:.3f}"))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("func,run_id,algorithm,seconds_wall\n")
        for r in sorted(rows):
            f.write(",".join(r) + "\n")
    print(f"Wrote {len(rows)} rows -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
