#!/usr/bin/env python3
"""A2: conflict-gated MASOIE vs always-on MASOIE (matched budget).

Demonstrates that the paper's three-layer conflict gate is NOT MACPO-specific: it
attaches to MASOIE's structurally different external-learning negotiation and cuts
communication while keeping terminal fitness comparable. Both arms use the SAME
gated binary (external_baselines/masoie_gated/MASOIE_gated.cpp); the only difference
is the gate parameters, so the comparison isolates the gate:

  * always-on : MASOIE_LAMBDA=0 MASOIE_K=1  -> communicate every outer loop
  * gated     : paper defaults (lambda=1.2, K=10)

Outputs raw logs + an aggregated JSON consumed by the paper.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "external_baselines" / "iamrice_cdo"
REPO = VENDOR / "masoie_repo"
GATED_SRC = ROOT / "external_baselines" / "masoie_gated" / "MASOIE_gated.cpp"
GATED_EXE = ROOT / "external_baselines" / "masoie_gated" / "masoie_gated"
RUN_CWD = VENDOR / "TEVC2024-MASOIE"  # cwd so ../Benchmarks/default_config.json resolves
OUT_DIR = ROOT / "ablation_experiments" / "results" / "masoie_gated"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "masoie_gated_ablation.json"

FUNCS = [f"F{i}" for i in range(1, 7)]
NP = 20  # MPI ranks = agents

ARMS = {
    "always_on": {"MASOIE_LAMBDA": "0", "MASOIE_K": "1"},
    "gated": {"MASOIE_LAMBDA": "1.2", "MASOIE_K": "10"},
}


def build() -> None:
    eigen = None
    for p in ("/opt/homebrew/include/eigen3", "/usr/local/include/eigen3"):
        if Path(p).is_dir():
            eigen = p
            break
    cmd = [
        "mpic++", "-std=c++11", "-O2",
        str(GATED_SRC),
        str(REPO / "framework" / "framework.cpp"),
        str(REPO / "framework" / "main.cpp"),
        str(REPO / "Benchmarks" / "Benchmarks.cpp"),
        "-I", str(REPO / "framework"), "-I", str(REPO / "Benchmarks"), "-I", str(REPO),
        "-I", str(VENDOR / "TEVC2024-MASOIE"),
    ]
    if eigen:
        cmd += ["-I", eigen]
    cmd += ["-o", str(GATED_EXE)]
    print(">>>", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"build failed:\n{r.stderr}")
    print(f"built {GATED_EXE}", flush=True)


_PAT = {
    "fitness": re.compile(r"fitness:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "disagreement": re.compile(r"disagreement:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "comm": re.compile(r"communication cost:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"),
    "trigger": re.compile(r"trigger_rate:\s*([+-]?\d+(?:\.\d+)?)"),
}


def parse(text: str) -> dict:
    out = {}
    for k, pat in _PAT.items():
        m = pat.findall(text)
        if m:
            out[k] = float(m[-1])
    return out


def run_env(tag: str, env_params: dict, func: str, seed_idx: int,
            resume: bool = True, timeout: int = 300) -> dict:
    """Run one gated-MASOIE trial with arbitrary gate env params. tag names the log."""
    log = OUT_DIR / "raw" / f"{tag}_{func}_run{seed_idx:02d}.log"
    if resume and log.is_file():
        m = parse(log.read_text(encoding="utf-8", errors="replace"))
        if "fitness" in m and "comm" in m:
            return m  # already done, reuse
    env = dict(os.environ)
    env.update(env_params)
    cmd = ["mpirun", "-np", str(NP), "--oversubscribe", str(GATED_EXE), func]
    r = subprocess.run(cmd, cwd=str(RUN_CWD), text=True, capture_output=True,
                       env=env, timeout=timeout)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"# EXIT {r.returncode}\n{r.stdout}\n--- STDERR ---\n{r.stderr}\n", encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"run failed {tag} {func} #{seed_idx}: see {log}")
    return parse(r.stdout + "\n" + r.stderr)


def run_one(arm: str, func: str, seed_idx: int, resume: bool = True,
            timeout: int = 300) -> dict:
    return run_env(arm, ARMS[arm], func, seed_idx, resume=resume, timeout=timeout)


def agg(vals):
    return {"n": len(vals), "mean": mean(vals), "std": pstdev(vals) if len(vals) > 1 else 0.0,
            "median": sorted(vals)[len(vals) // 2]} if vals else {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--funcs", type=str, default=",".join(FUNCS))
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--ksweep", type=str, default="",
                    help="comma-separated fail-safe K grid; enables operating-point sweep mode (lambda=1.2)")
    ap.add_argument("--out-name", type=str, default="masoie_gated_ablation",
                    help="basename for the output JSON")
    args = ap.parse_args()
    funcs = [f.strip() for f in args.funcs.split(",") if f.strip()]

    # operating-point sweep mode: gate at fixed lambda=1.2, varying fail-safe K
    if args.ksweep.strip():
        ARMS.clear()
        for k in [int(x) for x in args.ksweep.split(",") if x.strip()]:
            ARMS[f"gated_K{k}"] = {"MASOIE_LAMBDA": "1.2", "MASOIE_K": str(k)}
        ARMS["always_on"] = {"MASOIE_LAMBDA": "0", "MASOIE_K": "1"}

    json_out = JSON_OUT.parent / f"{args.out_name}.json"

    if not args.no_build:
        build()

    results = {arm: {} for arm in ARMS}
    for func in funcs:
        for arm in ARMS:
            fit, dis, comm, trig = [], [], [], []
            for s in range(1, args.runs + 1):
                m = run_one(arm, func, s)
                fit.append(m.get("fitness", float("nan")))
                dis.append(m.get("disagreement", float("nan")))
                comm.append(m.get("comm", float("nan")))
                if "trigger" in m:
                    trig.append(m["trigger"])
                print(f"[{arm} {func} {s}/{args.runs}] fit={m.get('fitness'):.4e} "
                      f"comm={m.get('comm'):.3e} trig={m.get('trigger', float('nan')):.3f}", flush=True)
            results[arm][func] = {
                "fitness": agg(fit), "disagreement": agg(dis),
                "comm_cost": agg(comm), "trigger_rate": agg(trig),
            }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment": "conflict-gated MASOIE vs always-on MASOIE (same binary, matched budget)",
        "runs_target": args.runs, "np": NP, "arms": ARMS, "functions": results,
    }
    (OUT_DIR / f"{args.out_name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {json_out}")


if __name__ == "__main__":
    main()
