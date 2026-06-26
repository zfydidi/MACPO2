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
    is_synthetic_scalability_benchmark,
)
from scripts.run_comm_baselines import (  # noqa: E402
    _mpirun_prefix,
    parse_cost_stats,
    parse_final_fitness,
    read_run_artifact,
    run_artifacts_ok,
    summarize,
)

RLMACPO = ROOT / "RL-MACPO"
# 与 WSL 上 output1/output 目录对齐（Mac 汇总也读这里）
DEFAULT_OUTPUT_DIR = RLMACPO / "output1" / "output"
OUT = ROOT / "ablation_experiments" / "results" / "scalability"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "scalability_chain.json"


def _out_dir_arg(output_dir: Path) -> str:
    p = str(output_dir.resolve())
    return p if p.endswith("/") else p + "/"


def read_scale_artifact(output_dir: Path, func: str, name: str, method: str, rid: int) -> dict | None:
    exid = f"scale_{name}_{method}_r{rid:02d}"
    out_file = output_dir / f"{func}_LLSO_final_{exid}.txt"
    stats, fit = read_run_artifact(out_file)
    if stats and fit is not None:
        return {"comm_rate": stats["comm_rate"], "fitness": fit}
    # 手动 smoke 试跑：控制台对应 F1S50_LLSO_final_smoke01.txt（AlwaysOn ≈ MACPO）
    if method == "MACPO" and rid == 1 and name in ("F1S50", "F1S100"):
        smoke = output_dir / f"{func}_LLSO_final_smoke01.txt"
        stats, fit = read_run_artifact(smoke)
        if stats and fit is not None:
            return {"comm_rate": stats["comm_rate"], "fitness": fit}
    return None


def aggregate_scale_rows(
    names: list[str],
    runs: int,
    output_dir: Path,
) -> list[dict]:
    lookup = {alias: (n, key) for alias, n, key in SCALABILITY_BENCHMARKS}
    rows: list[dict] = []
    for name in names:
        if name not in lookup:
            print(f"Skip unknown benchmark {name}")
            continue
        n_agents, func = lookup[name]
        for method in ("MACPO", "RL-MACPO"):
            comms, fits = [], []
            for rid in range(1, runs + 1):
                rec = read_scale_artifact(output_dir, func, name, method, rid)
                if rec:
                    comms.append(rec["comm_rate"])
                    fits.append(rec["fitness"])
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
    return rows


def run_one(func: str, np_: str, method: str, exid: str, output_dir: Path) -> dict | None:
    cfg = "Selection_0.9_0.7_0.5" if method == "RL-MACPO" else "AlwaysOn"
    out_file = output_dir / f"{func}_LLSO_final_{exid}.txt"
    cmd = [
        *_mpirun_prefix(),
        "-np",
        np_,
        "--oversubscribe",
        "./build/MACPO_simplified",
        func,
        exid,
        cfg,
        _out_dir_arg(output_dir),
    ]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    print(f"    输出: {out_file}", flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=str(RLMACPO), check=False).returncode
    elapsed = time.time() - t0
    print(f"<<< {func} {method} {exid} exit={rc} elapsed={elapsed:.1f}s", flush=True)
    if not out_file.is_file():
        print(f"    !! 缺少输出文件: {out_file}", flush=True)
        return None
    stats, fit = read_run_artifact(out_file)
    if not stats or fit is None:
        print(f"    !! 输出不完整（无 COST_STATS 或 fitness）: {out_file}", flush=True)
        return None
    return {"comm_rate": stats["comm_rate"], "fitness": fit}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--benchmarks", type=str, default="F1,F7,F13")
    ap.add_argument("--sleep-sec", type=float, default=0.0, help="每次 run 结束后休眠秒数")
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="MACPO_simplified 输出 .txt 目录（默认 RL-MACPO/output1/output）",
    )
    ap.add_argument(
        "--aggregate-only",
        action="store_true",
        help="仅从已有 output .txt 汇总 JSON，不启动 MPI",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="已有完整 .txt 则跳过该 run",
    )
    args = ap.parse_args()

    names = [b.strip() for b in args.benchmarks.split(",") if b.strip()]
    output_dir = args.output_dir.resolve()

    if args.aggregate_only:
        if not output_dir.is_dir():
            raise SystemExit(f"aggregate-only: 目录不存在 {output_dir}")
        rows = aggregate_scale_rows(names, args.runs, output_dir)
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"aggregate-only from {output_dir}")
        print(f"Wrote {JSON_OUT} ({len(rows)} rows)")
        return

    written = ensure_scalability_benchmarks()
    if written:
        print(f"Prepared scalability benchmarks: {written}")

    bin_path = RLMACPO / "build" / "MACPO_simplified"
    if not bin_path.is_file():
        raise SystemExit(f"缺少 {bin_path}，请先在 RL-MACPO 内 cmake 编译")

    lookup = {alias: (n, key) for alias, n, key in SCALABILITY_BENCHMARKS}
    rows: list[dict] = []
    OUT.mkdir(parents=True, exist_ok=True)

    print(
        f"scalability: benchmarks={','.join(names)} runs={args.runs} "
        f"sleep={args.sleep_sec}s out={output_dir}",
        flush=True,
    )
    print(
        "顺序: 每个 benchmark 先跑 MACPO(AlwaysOn)×runs，再跑 RL-MACPO(Selection)×runs",
        flush=True,
    )
    print("提示: 每次 MPI 通常需 20–60 分钟；下方会实时打印 mpirun 输出。", flush=True)

    for name in names:
        if name not in lookup:
            print(f"Skip unknown benchmark {name}")
            continue
        n_agents, func = lookup[name]
        if is_synthetic_scalability_benchmark(name) and not benchmark_data_complete(func):
            raise SystemExit(
                f"{func} 缺少 Benchmarks/data 文件。请运行:\n"
                f"  python3 -c \"from utils.chain_benchmark_codegen import ensure_scalability_benchmarks; "
                f"print(ensure_scalability_benchmarks())\""
            )
        np_ = str(n_agents)
        for method in ("MACPO", "RL-MACPO"):
            print(f"\n==== {name} | {method} | {args.runs} runs ====", flush=True)
            comms, fits = [], []
            for rid in range(1, args.runs + 1):
                exid = f"scale_{name}_{method}_r{rid:02d}"
                out_file = output_dir / f"{func}_LLSO_final_{exid}.txt"
                if args.skip_existing and run_artifacts_ok(out_file):
                    rec = read_scale_artifact(output_dir, func, name, method, rid)
                    if rec:
                        comms.append(rec["comm_rate"])
                        fits.append(rec["fitness"])
                        print(
                            f"{name} {method} r{rid:02d} skip-existing "
                            f"comm={rec['comm_rate']:.3f} fit={rec['fitness']:.4g}",
                            flush=True,
                        )
                        continue
                rec = run_one(func, np_, method, exid, output_dir)
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
