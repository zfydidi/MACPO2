#!/usr/bin/env python3
"""Run periodic-communication baselines (PeriodicK2/3/5) on F1, F2, F5."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
RLMACPO = ROOT / "RL-MACPO"
OUT = ROOT / "ablation_experiments" / "results" / "periodic_baseline"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "periodic_baseline_f125.json"

METHODS = ("Full", "PeriodicK2", "PeriodicK3", "PeriodicK5")
FUNCS = ("F1", "F2", "F5")


def parse_cost_stats(text: str) -> dict | None:
    m = re.search(
        r"# COST_STATS.*?comm_rate=([0-9.eE+-]+).*?total_time_ms=([0-9.eE+-]+)",
        text,
        re.S,
    )
    if not m:
        return None
    return {"comm_rate": float(m.group(1)), "wall_s": float(m.group(2)) / 1000.0}


def parse_final_fitness(text: str) -> float | None:
    rows = re.findall(r"^\d+\t[^\n]+$", text, re.M)
    if rows:
        last = rows[-1].split("\t")
        if len(last) >= 4:
            try:
                return float(last[3])
            except ValueError:
                pass
    m = re.search(r"Completed \[LLSO\]:.*?final fitness=([0-9.eE+-]+)", text)
    return float(m.group(1)) if m else None


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, float, str]:
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, time.time() - t0, p.stdout


def summarize(vals: list[float]) -> tuple[float | None, float | None]:
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return mean(vals), pstdev(vals)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--np", type=str, default="20")
    args = ap.parse_args()

    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for func in FUNCS:
        for method in METHODS:
            comms: list[float] = []
            fits: list[float] = []
            for rid in range(1, args.runs + 1):
                exid = f"per_{method}_r{rid:02d}"
                cmd = ["mpirun", "-np", args.np, "--oversubscribe", "./build/MACPO_simplified", func, exid, method]
                code, elapsed, out = run_cmd(cmd, RLMACPO)
                log = raw / f"{func}_{method}_r{rid:02d}.log"
                out_file = RLMACPO / "output" / f"{func}_LLSO_final_{exid}.txt"
                text = out_file.read_text(encoding="utf-8", errors="replace") if out_file.is_file() else ""
                log.write_text(out + "\n\n=== OUTFILE ===\n" + text, encoding="utf-8")
                stats = parse_cost_stats(text) if text else None
                fit = parse_final_fitness(text) if text else None
                if stats:
                    comms.append(stats["comm_rate"])
                if fit is not None:
                    fits.append(fit)
                print(
                    f"{func} {method} r{rid:02d} code={code} {elapsed:.1f}s "
                    f"comm={stats['comm_rate'] if stats else None} fit={fit}"
                )
            cm, cs = summarize(comms)
            fm, fs = summarize(fits)
            rows.append(
                {
                    "func": func,
                    "method": method,
                    "n": len(fits),
                    "comm_rate_mean": cm,
                    "comm_rate_std": cs,
                    "final_fitness_mean": fm,
                    "final_fitness_std": fs,
                }
            )

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {JSON_OUT}")


if __name__ == "__main__":
    main()
