#!/usr/bin/env python3
"""
Run communication-policy baselines on F1--F6 (LLSO, 20 agents).

Methods:
  Full              — conflict-gated RL-MACPO (Selection_0.9_0.7_0.5)
  PeriodicK2/3/5    — fixed-interval negotiation
  FixedThreshold    — absolute-threshold gate (no variable selection)
  FixedThresholdNoFailSafe — fixed threshold, fail-safe disabled (event-style)
  RelativeThresholdFailSafe — relative threshold + fail-safe (ablation reference)
"""
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
OUT = ROOT / "ablation_experiments" / "results" / "comm_baselines"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_baselines_f1_f6.json"

METHODS = (
    "Full",
    "PeriodicK2",
    "PeriodicK3",
    "PeriodicK5",
    "FixedThreshold",
    "FixedThresholdNoFailSafe",
    "RelativeThresholdFailSafe",
)
FUNCS = ("F1", "F2", "F3", "F4", "F5", "F6")

# Match main F1--F6 table configuration.
FULL_CONFIG = "Selection_0.9_0.7_0.5"


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


def _mpirun_prefix() -> list[str]:
    """WSL2 OpenMPI: match run_comm_rate_f1_f18.sh (btl-vader fix)."""
    import os

    prefix = ["mpirun", "--allow-run-as-root"]
    mca = os.environ.get("MACPO_MPIRUN_MCA", "").strip()
    if mca:
        prefix.extend(mca.split())
    elif os.environ.get("OMPI_MCA_btl_vader_single_copy_mechanism") == "none":
        prefix.extend(["--mca", "btl_vader_single_copy_mechanism", "none"])
    elif Path("/proc/version").is_file():
        try:
            if "microsoft" in Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower():
                prefix.extend(["--mca", "btl_vader_single_copy_mechanism", "none"])
        except OSError:
            pass
    return prefix


def run_cmd(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, float, str]:
    """Run command and stream stdout/stderr to console (for long mpirun jobs)."""
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    t0 = time.time()
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd),
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
    print(f"<<< exit={code} elapsed={elapsed:.1f}s", flush=True)
    return code, elapsed, "".join(chunks)


def run_artifacts_ok(out_file: Path) -> bool:
    if not out_file.is_file():
        return False
    text = out_file.read_text(encoding="utf-8", errors="replace")
    return parse_final_fitness(text) is not None and parse_cost_stats(text) is not None


def summarize(vals: list[float]) -> tuple[float | None, float | None]:
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], 0.0
    return mean(vals), pstdev(vals)


def method_config(method: str) -> str:
    if method == "Full":
        return FULL_CONFIG
    return method


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--np", type=str, default="20")
    ap.add_argument("--funcs", type=str, default=",".join(FUNCS))
    ap.add_argument("--methods", type=str, default=",".join(METHODS))
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--sleep-sec", type=float, default=0.0, help="每次 run 结束后休眠秒数，降低 CPU 占用")
    args = ap.parse_args()

    bin_path = RLMACPO / "build" / "MACPO_simplified"
    if not bin_path.is_file():
        raise SystemExit(
            f"缺少 {bin_path}\n"
            "请先在 WSL 编译:\n"
            "  cd RL-MACPO && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_CXX_COMPILER=mpicxx && cmake --build build -j1"
        )

    funcs = tuple(f.strip() for f in args.funcs.split(",") if f.strip())
    methods = tuple(m.strip() for m in args.methods.split(",") if m.strip())
    raw = OUT / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    total_jobs = len(funcs) * len(methods) * args.runs
    print(
        f"comm_baselines: funcs={','.join(funcs)} methods={len(methods)} "
        f"runs={args.runs} np={args.np} jobs≈{total_jobs}",
        flush=True,
    )
    print("提示: 每次 MPI 通常需 20–60 分钟；下方会实时打印 mpirun 输出。", flush=True)

    for func in funcs:
        for method in methods:
            comms: list[float] = []
            fits: list[float] = []
            for rid in range(1, args.runs + 1):
                exid = f"cb_{method}_r{rid:02d}"
                log = raw / f"{func}_{method}_r{rid:02d}.log"
                out_file = RLMACPO / "output" / f"{func}_LLSO_final_{exid}.txt"
                if args.skip_existing and run_artifacts_ok(out_file):
                    text = out_file.read_text(encoding="utf-8", errors="replace")
                    print(f"{func} {method} r{rid:02d} skip-existing (ok)", flush=True)
                else:
                    cfg = method_config(method)
                    cmd = [
                        *_mpirun_prefix(),
                        "-np",
                        args.np,
                        "--oversubscribe",
                        "./build/MACPO_simplified",
                        func,
                        exid,
                        cfg,
                    ]
                    env = dict(__import__("os").environ)
                    if method == "FixedThresholdNoFailSafe":
                        env["MACPO_DISABLE_FAILSAFE"] = "1"
                    code, elapsed, out = run_cmd(cmd, RLMACPO, env=env)
                    text = out_file.read_text(encoding="utf-8", errors="replace") if out_file.is_file() else ""
                    log.write_text(out + "\n\n=== OUTFILE ===\n" + text, encoding="utf-8")
                    stats = parse_cost_stats(text) if text else None
                    fit = parse_final_fitness(text) if text else None
                    print(
                        f"{func} {method} r{rid:02d} code={code} {elapsed:.1f}s "
                        f"comm={stats['comm_rate'] if stats else None} fit={fit}",
                        flush=True,
                    )
                    if args.sleep_sec > 0:
                        time.sleep(args.sleep_sec)
                stats = parse_cost_stats(text) if text else None
                fit = parse_final_fitness(text) if text else None
                if stats:
                    comms.append(stats["comm_rate"])
                if fit is not None:
                    fits.append(fit)
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
