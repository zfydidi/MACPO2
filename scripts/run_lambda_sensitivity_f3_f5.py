#!/usr/bin/env python3
"""
Lambda sensitivity for conflict-gated RL-MACPO on F3/F5.

Uses headline stack Selection_0.9_0.7_0.5 (RL + variable selection + full gate)
and overrides only MACPO_REL_LAMBDA. Fail-safe stays at default K=10.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
RLMACPO = ROOT / "RL-MACPO"
OUT = ROOT / "ablation_experiments" / "results" / "lambda_sensitivity_f3_f5"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "lambda_sensitivity_f3_f5.json"
CSV_OUT = OUT / "lambda_sensitivity_summary.csv"
CONFIG = "Selection_0.9_0.7_0.5"
DEFAULT_LAMBDAS = (0.8, 1.0, 1.2, 1.4)
DEFAULT_FUNCS = ("F3", "F5")


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


def summarize(vals: list[float]) -> tuple[float | None, float | None]:
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return mean(vals), pstdev(vals)


def artifact_path(output_dir: Path, func: str, lam: float, rid: int) -> Path:
    lam_s = f"{lam:g}".replace(".", "p")
    exid = f"lam{lam_s}_r{rid:02d}"
    return output_dir / f"{func}_LLSO_final_{exid}.txt"


def read_artifact(path: Path) -> tuple[dict | None, float | None]:
    if not path.is_file():
        return None, None
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_cost_stats(text), parse_final_fitness(text)


def artifact_ok(path: Path) -> bool:
    stats, fit = read_artifact(path)
    return stats is not None and fit is not None


def _mpirun_prefix() -> list[str]:
    prefix = ["mpirun", "--oversubscribe"]
    mca = os.environ.get("MACPO_MPIRUN_MCA", "").strip()
    if mca:
        prefix.extend(mca.split())
    return prefix


def aggregate(
    funcs: tuple[str, ...],
    lambdas: tuple[float, ...],
    runs: int,
    output_dir: Path,
) -> list[dict]:
    rows: list[dict] = []
    for func in funcs:
        for lam in lambdas:
            comms: list[float] = []
            fits: list[float] = []
            walls: list[float] = []
            for rid in range(1, runs + 1):
                path = artifact_path(output_dir, func, lam, rid)
                stats, fit = read_artifact(path)
                if stats:
                    comms.append(stats["comm_rate"])
                    walls.append(stats["wall_s"])
                if fit is not None:
                    fits.append(fit)
            cm, cs = summarize(comms)
            fm, fs = summarize(fits)
            wm, ws = summarize(walls)
            rows.append(
                {
                    "func": func,
                    "lambda": lam,
                    "config": CONFIG,
                    "n": len(fits),
                    "comm_rate_mean": cm,
                    "comm_rate_std": cs,
                    "final_fitness_mean": fm,
                    "final_fitness_std": fs,
                    "wall_s_mean": wm,
                    "wall_s_std": ws,
                }
            )
    return rows


def write_outputs(rows: list[dict], runs: int, funcs: tuple[str, ...], lambdas: tuple[float, ...]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": CONFIG,
        "runs_target": runs,
        "functions": list(funcs),
        "lambdas": list(lambdas),
        "fail_safe": {"enabled": True, "k": 10},
        "rows": rows,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    header = (
        "func,lambda,n,comm_rate_mean,comm_rate_std,"
        "final_fitness_mean,final_fitness_std,wall_s_mean,wall_s_std\n"
    )
    lines = [header]
    for r in rows:
        lines.append(
            f"{r['func']},{r['lambda']},{r['n']},"
            f"{r['comm_rate_mean']},{r['comm_rate_std']},"
            f"{r['final_fitness_mean']},{r['final_fitness_std']},"
            f"{r['wall_s_mean']},{r['wall_s_std']}\n"
        )
    CSV_OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {JSON_OUT}")
    print(f"Wrote {CSV_OUT}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--np", type=str, default="20")
    ap.add_argument("--funcs", type=str, default=",".join(DEFAULT_FUNCS))
    ap.add_argument("--lambdas", type=str, default=",".join(str(x) for x in DEFAULT_LAMBDAS))
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    ap.add_argument("--output-dir", type=Path, default=RLMACPO / "output")
    ap.add_argument("--sleep-sec", type=float, default=0.0)
    args = ap.parse_args()

    funcs = tuple(f.strip() for f in args.funcs.split(",") if f.strip())
    lambdas = tuple(float(x.strip()) for x in args.lambdas.split(",") if x.strip())
    output_dir = args.output_dir.resolve()

    if args.aggregate_only:
        rows = aggregate(funcs, lambdas, args.runs, output_dir)
        write_outputs(rows, args.runs, funcs, lambdas)
        return

    bin_path = RLMACPO / "build" / "MACPO_simplified"
    if not bin_path.is_file():
        raise SystemExit(f"Missing {bin_path}")

    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    total = len(funcs) * len(lambdas) * args.runs
    print(
        f"lambda_sensitivity: funcs={','.join(funcs)} lambdas={lambdas} "
        f"runs={args.runs} jobs={total}",
        flush=True,
    )

    job = 0
    for func in funcs:
        for lam in lambdas:
            for rid in range(1, args.runs + 1):
                job += 1
                lam_s = f"{lam:g}".replace(".", "p")
                exid = f"lam{lam_s}_r{rid:02d}"
                out_file = artifact_path(output_dir, func, lam, rid)
                log = raw / f"{func}_lam{lam_s}_r{rid:02d}.log"
                if args.skip_existing and artifact_ok(out_file):
                    print(f"[{job}/{total}] {func} λ={lam} r{rid:02d} skip-existing", flush=True)
                    continue

                env = os.environ.copy()
                env["MACPO_REL_LAMBDA"] = f"{lam:g}"
                env["MACPO_PAIR_SEED"] = str(rid)
                env.pop("MACPO_DISABLE_FAILSAFE", None)

                cmd = [
                    *_mpirun_prefix(),
                    "-np",
                    args.np,
                    "-x",
                    "MACPO_REL_LAMBDA",
                    "-x",
                    "MACPO_PAIR_SEED",
                    "./build/MACPO_simplified",
                    func,
                    exid,
                    CONFIG,
                ]
                print(f"\n[{job}/{total}] >>> {' '.join(cmd)}", flush=True)
                t0 = time.time()
                p = subprocess.Popen(
                    cmd,
                    cwd=str(RLMACPO),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    bufsize=1,
                )
                chunks: list[str] = []
                assert p.stdout is not None
                for line in p.stdout:
                    chunks.append(line)
                    print(line, end="", flush=True)
                code = p.wait()
                elapsed = time.time() - t0
                log.write_text("".join(chunks), encoding="utf-8")
                print(f"<<< exit={code} elapsed={elapsed:.1f}s log={log}", flush=True)
                if code != 0:
                    raise SystemExit(f"Run failed: {func} λ={lam} r{rid:02d}")
                if args.sleep_sec > 0:
                    time.sleep(args.sleep_sec)

    rows = aggregate(funcs, lambdas, args.runs, output_dir)
    write_outputs(rows, args.runs, funcs, lambdas)


if __name__ == "__main__":
    main()
