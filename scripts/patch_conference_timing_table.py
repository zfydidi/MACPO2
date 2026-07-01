#!/usr/bin/env python3
"""Build wall-time summary JSON from per-run timing CSV (F1-F6 archive logs)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

_REPO = Path(__file__).resolve().parents[1]
DEFAULT_CSV = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "wall_time_f1_f6_from_logs.csv"
DEFAULT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "wall_time_f1_f6_summary.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_JSON)
    args = ap.parse_args()
    if not args.csv.is_file():
        raise SystemExit(f"Missing CSV: {args.csv}")

    buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
    with args.csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buckets[(row["func"], row["algorithm"])].append(float(row["seconds_wall"]))

    summary = {}
    for (func, algo), vals in sorted(buckets.items()):
        summary.setdefault(func, {})[algo] = {
            "n": len(vals),
            "mean_s": mean(vals),
            "std_s": pstdev(vals) if len(vals) > 1 else 0.0,
        }

    payload = {"source_csv": str(args.csv.resolve()), "functions": summary}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({sum(v['n'] for f in summary.values() for v in f.values())} runs)")


if __name__ == "__main__":
    main()
