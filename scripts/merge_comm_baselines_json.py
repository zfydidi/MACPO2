#!/usr/bin/env python3
"""Merge comm-baseline artifacts from RL-MACPO/output and output1/output."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import mean, pstdev

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

DIRS = [_REPO / "RL-MACPO/output", _REPO / "RL-MACPO/output1/output"]
OUT = _REPO / "RL_MACPO_IEEE_English_with_images/media/comm_baselines_f1_f6.json"
METHODS = (
    "Full",
    "PeriodicK2",
    "PeriodicK3",
    "PeriodicK5",
    "FixedThreshold",
    "FixedThresholdNoFailSafe",
    "RelativeThresholdFailSafe",
)
FUNCS = [f"F{i}" for i in range(1, 7)]


def parse_cost_stats(text: str) -> float | None:
    m = re.search(r"# COST_STATS.*?comm_rate=([0-9.eE+-]+)", text, re.S)
    return float(m.group(1)) if m else None


def parse_fit(text: str) -> float | None:
    rows = re.findall(r"^\d+\t[^\n]+$", text, re.M)
    if rows:
        last = rows[-1].split("\t")
        if len(last) >= 4:
            try:
                return float(last[3])
            except ValueError:
                pass
    m = re.search(r"final fitness=([0-9.eE+-]+)", text)
    return float(m.group(1)) if m else None


def main() -> None:
    rows = []
    for func in FUNCS:
        for method in METHODS:
            comms, fits = [], []
            for rid in range(1, 26):
                exid = f"cb_{method}_r{rid:02d}"
                found = None
                for d in DIRS:
                    p = d / f"{func}_LLSO_final_{exid}.txt"
                    if p.is_file():
                        found = p
                        break
                if not found:
                    continue
                t = found.read_text(encoding="utf-8", errors="replace")
                c, f = parse_cost_stats(t), parse_fit(t)
                if c is not None:
                    comms.append(c)
                if f is not None:
                    fits.append(f)
            if fits:
                rows.append(
                    {
                        "func": func,
                        "method": method,
                        "n": len(fits),
                        "comm_rate_mean": mean(comms) if comms else None,
                        "comm_rate_std": pstdev(comms) if len(comms) > 1 else 0.0,
                        "final_fitness_mean": mean(fits),
                        "final_fitness_std": pstdev(fits) if len(fits) > 1 else 0.0,
                    }
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    bad = [r for r in rows if r["n"] != 25]
    print(f"Wrote {OUT} ({len(rows)} rows, incomplete={len(bad)})")


if __name__ == "__main__":
    main()
