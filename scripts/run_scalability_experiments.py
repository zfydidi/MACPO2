#!/usr/bin/env python3
"""Run MACPO vs RL-MACPO scalability pilots on chain-scale benchmarks."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.chain_benchmark_codegen import (  # noqa: E402
    SCALABILITY_BENCHMARKS,
    benchmark_data_complete,
    ensure_scalability_benchmarks,
)
from scripts.run_comm_baselines import (  # noqa: E402
    _mpirun_prefix,
    parse_cost_stats,
    parse_final_fitness,
    summarize,
)

RLMACPO = ROOT / "RL-MACPO"
OUT = ROOT / "ablation_experiments" / "results" / "scalability"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "scalability_chain.json"


def run_one(func: str, np_: str, method: str, exid: str) -> dict | None:
    cfg = "Selection_0.9_0.7_0.5" if method == "RL-MACPO" else "AlwaysOn"
    cmd = [
        *_mpirun_prefix(),
        "-np",
        np_,
        "--oversubscribe",
        "./build/MACPO_simplified",
        func,
        exid,
        cfg,
    ]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=str(RLMACPO), check=False).returncode
    elapsed = time.time() - t0
    print(f"<<< {func} {method} {exid} exit={rc} elapsed={elapsed:.1f}s", flush=True)
    out_file = RLMACPO / "output" / f"{func}_LLSO_final_{exid}.txt"
    if not out_file.is_file():
        return None
    text = out_file.read_text(encoding="utf-8", errors="replace")
    stats = parse_cost_stats(text)
    fit = parse_final_fitness(text)
    if not stats or fit is None:
        return None
    return {"comm_rate": stats["comm_rate"], "fitness": fit}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--benchmarks", type=str, default="F1,F7,F13")
    ap.add_argument("--sleep-sec", type=float, default=0.0, help="每次 run 结束后休眠秒数")
    args = ap.parse_args()

    written = ensure_scalability_benchmarks()
    if written:
        print(f"Prepared scalability benchmarks: {written}")

    bin_path = RLMACPO / "build" / "MACPO_simplified"
    if not bin_path.is_file():
        raise SystemExit(f"缺少 {bin_path}，请先在 RL-MACPO 内 cmake 编译")

    names = [b.strip() for b in args.benchmarks.split(",") if b.strip()]
    lookup = {alias: (n, key) for alias, n, key in SCALABILITY_BENCHMARKS}
    rows: list[dict] = []
    OUT.mkdir(parents=True, exist_ok=True)

    print(
        f"scalability: benchmarks={','.join(names)} runs={args.runs} sleep={args.sleep_sec}s",
        flush=True,
    )
    print("提示: 每次 MPI 通常需 20–60 分钟；下方会实时打印 mpirun 输出。", flush=True)

    for name in names:
        if name not in lookup:
            print(f"Skip unknown benchmark {name}")
            continue
        n_agents, func = lookup[name]
        if not benchmark_data_complete(func):
            raise SystemExit(
                f"{func} 缺少 Benchmarks/data 文件。请运行:\n"
                f"  python3 -c \"from utils.chain_benchmark_codegen import ensure_scalability_benchmarks; "
                f"print(ensure_scalability_benchmarks())\""
            )
        np_ = str(n_agents)
        for method in ("MACPO", "RL-MACPO"):
            comms, fits = [], []
            for rid in range(1, args.runs + 1):
                exid = f"scale_{name}_{method}_r{rid:02d}"
                rec = run_one(func, np_, method, exid)
                if rec:
                    comms.append(rec["comm_rate"])
                    fits.append(rec["fitness"])
                    print(f"{name} {method} r{rid}: comm={rec['comm_rate']:.3f} fit={rec['fitness']:.4g}", flush=True)
                    if args.sleep_sec > 0:
                        time.sleep(args.sleep_sec)
            cm, cs = summarize(comms)
            fm, fs = summarize(fits)
            rows.append(
                {
                    "benchmark": name,
                    "func": func,
                    "agents": n_agents,
                    "method": method,
                    "runs": len(fits),
                    "comm_rate_mean": cm,
                    "comm_rate_std": cs,
                    "fitness_mean": fm,
                    "fitness_std": fs,
                }
            )

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {JSON_OUT}")


if __name__ == "__main__":
    main()
