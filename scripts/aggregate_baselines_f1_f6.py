#!/usr/bin/env python3
"""Summarize GFPDO/DPSO 25-run baselines under MACPO_sourcecode/output_baselines_*."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.baseline_log_stats import (  # noqa: E402
    count_completed_runs,
    load_baseline_series_optional,
    summarize,
)

FUNCS = [f"F{i}" for i in range(1, 7)]
OPTS = ["LLSO", "CSO"]
METHODS = {"dpso": "DPSO1", "gfpdo": "GFPDO"}


def aggregate_algo(out_dir: Path, algo: str, runs: int) -> dict:
    method = METHODS[algo]
    rows: dict[str, dict] = {}
    for fn in FUNCS:
        rows[fn] = {}
        for opt in OPTS:
            n_done = count_completed_runs(out_dir, method, fn, opt, runs)
            entry: dict = {"n_completed": n_done, "n_expected": runs}
            if n_done > 0:
                vals, missing = load_baseline_series_optional(
                    out_dir, method, fn, opt, runs
                )
                entry["missing"] = missing
                if len(vals):
                    entry.update(summarize(vals))
            rows[fn][opt] = entry
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dpso-dir",
        type=Path,
        default=_REPO / "MACPO_sourcecode" / "output_baselines_dpso_25runs",
    )
    ap.add_argument(
        "--gfpdo-dir",
        type=Path,
        default=_REPO / "MACPO_sourcecode" / "output_baselines_gfpdo_25runs",
    )
    ap.add_argument("--runs", type=int, default=25)
    ap.add_argument(
        "--out",
        type=Path,
        default=_REPO / "MACPO_sourcecode" / "output_baselines_f1_f6_summary.json",
    )
    args = ap.parse_args()

    report: dict = {"runs": args.runs, "algorithms": {}}
    for algo, out_dir in [("dpso", args.dpso_dir), ("gfpdo", args.gfpdo_dir)]:
        if not out_dir.is_dir():
            print(f"SKIP {algo}: {out_dir} not found")
            continue
        report["algorithms"][algo] = {
            "out_dir": str(out_dir),
            "functions": aggregate_algo(out_dir, algo, args.runs),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")

    for algo, block in report.get("algorithms", {}).items():
        print(f"\n== {algo.upper()} ==")
        for fn in FUNCS:
            for opt in OPTS:
                e = block["functions"][fn][opt]
                n = e.get("n_completed", 0)
                if e.get("mean") is not None:
                    print(
                        f"  {fn} {opt}: {n}/{args.runs} "
                        f"mean={e['mean']:.4e} std={e['std']:.4e}"
                    )
                else:
                    print(f"  {fn} {opt}: {n}/{args.runs} (incomplete)")


if __name__ == "__main__":
    main()
