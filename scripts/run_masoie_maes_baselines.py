#!/usr/bin/env python3
"""
Clone/build/run MASOIE (and MAES-CCSA if present) on F1--F6.

Source: iamrice GitHub (TEVC 2024/2025 competition reference implementations).
Note: MASOIE/MAES target consensus-based DBO benchmarks; numbers are reported
alongside MACPO NDO with an explicit cross-paradigm caveat in the paper.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "external_baselines" / "iamrice_cdo"
MASOIE_REPO = "https://github.com/iamrice/Multi-Agent-Swarm-Optimization-with-Adaptive-Internal-and-External-Learning-in-TEVC-2024.git"
COMP_REPO = "https://github.com/iamrice/Proposal-for-Competition-on-Black-box-Consensus-based-Distributed-Optimization.git"
OUT_DIR = ROOT / "ablation_experiments" / "results" / "masoie_maes_f1f6"
JSON_OUT = ROOT / "RL_MACPO_IEEE_English_with_images" / "media" / "masoie_maes_f1f6.json"
FUNCS = [f"F{i}" for i in range(1, 7)]
NP_MAP = {f"F{i}": 20 for i in range(1, 7)}


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f">>> {' '.join(cmd)}", flush=True)
    res = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)
    if check and res.returncode != 0:
        raise RuntimeError(
            f"Command failed ({res.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res


def ensure_vendor() -> Path:
    VENDOR.mkdir(parents=True, exist_ok=True)
    masoie_dir = VENDOR / "TEVC2024-MASOIE"
    if not masoie_dir.is_dir():
        run_cmd(["git", "clone", "--depth", "1", MASOIE_REPO, str(VENDOR / "masoie_repo")])
        cloned = VENDOR / "masoie_repo" / "TEVC2024-MASOIE"
        if cloned.is_dir():
            shutil.move(str(cloned), str(masoie_dir))
        else:
            raise RuntimeError("TEVC2024-MASOIE not found in cloned MASOIE repo")
    comp_dir = VENDOR / "competition"
    if not comp_dir.is_dir():
        run_cmd(["git", "clone", "--depth", "1", COMP_REPO, str(comp_dir)])
    repo_root = VENDOR / "masoie_repo"
    for name in ("Benchmarks", "framework", "util", "Eigen"):
        src = repo_root / name
        dst = VENDOR / name
        if src.is_dir() and not dst.exists():
            dst.symlink_to(src, target_is_directory=True)
    return masoie_dir


def build_masoie(masoie_dir: Path) -> Path:
    exe = masoie_dir / "masoie"
    # Always rebuild to match current mpic++ (OpenMPI vs MPICH).
    if exe.is_file():
        exe.unlink()
    repo_root = VENDOR / "masoie_repo"
    framework = repo_root / "framework"
    bench = repo_root / "Benchmarks"
    eigen_inc = repo_root / "Eigen"
    if not framework.is_dir():
        framework = masoie_dir.parent / "framework"
    if not bench.is_dir():
        bench = masoie_dir.parent / "Benchmarks"
    include_args = ["-I", str(framework), "-I", str(bench), "-I", str(repo_root)]
    if eigen_inc.is_dir():
        include_args.extend(["-I", str(eigen_inc)])
    else:
        for p in (
            Path("/opt/homebrew/include/eigen3"),
            Path("/usr/local/include/eigen3"),
        ):
            if p.is_dir():
                include_args.extend(["-I", str(p)])
                break
    cmd = [
        "mpic++",
        "-std=c++11",
        "-O2",
        "MASOIE.cpp",
        str(framework / "framework.cpp"),
        str(framework / "main.cpp"),
        str(bench / "Benchmarks.cpp"),
        *include_args,
        "-o",
        str(exe),
    ]
    run_cmd(cmd, cwd=masoie_dir)
    return exe


def parse_fitness(text: str) -> float:
    for pat in (
        r"fitness:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        r"Best Fitness:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        r"final:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        r"Final fitness:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
        r"best fitness:\s*([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)",
    ):
        hits = re.findall(pat, text, flags=re.I)
        if hits:
            return float(hits[-1])
    raise ValueError("Could not parse fitness from MASOIE output")


def run_masoie_batch(exe: Path, masoie_dir: Path, funcs: list[str], runs: int, resume: bool) -> dict:
    raw = OUT_DIR / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    for func in funcs:
        vals: list[float] = []
        np_ = str(NP_MAP.get(func, 20))
        for r in range(1, runs + 1):
            log_path = raw / f"MASOIE_{func}_run{r:02d}.log"
            if resume and log_path.is_file():
                try:
                    vals.append(parse_fitness(log_path.read_text(encoding="utf-8", errors="replace")))
                    print(f"[SKIP] MASOIE {func} run {r}/{runs}", flush=True)
                    continue
                except ValueError:
                    pass
            cmd = ["mpirun", "-np", np_, "--oversubscribe", str(exe), func]
            run_cwd = masoie_dir
            res = run_cmd(cmd, cwd=run_cwd, check=False)
            log_path.write_text(
                f"# CMD: {' '.join(cmd)}\n# EXIT: {res.returncode}\n{res.stdout}\n--- STDERR ---\n{res.stderr}\n",
                encoding="utf-8",
            )
            if res.returncode != 0:
                raise RuntimeError(f"MASOIE failed: {log_path}")
            vals.append(parse_fitness(res.stdout + "\n" + res.stderr))
            print(f"[OK] MASOIE {func} run {r}/{runs} fitness={vals[-1]:.6e}", flush=True)
        summary[func] = {
            "n": len(vals),
            "mean": mean(vals),
            "std": pstdev(vals) if len(vals) > 1 else 0.0,
            "median": sorted(vals)[len(vals) // 2],
            "values": vals,
        }
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=25)
    ap.add_argument("--funcs", type=str, default=",".join(FUNCS))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()
    funcs = [f.strip() for f in args.funcs.split(",") if f.strip()]

    if args.aggregate_only:
        raw = OUT_DIR / "raw"
        summary = {}
        for func in funcs:
            vals = []
            for r in range(1, args.runs + 1):
                log_path = raw / f"MASOIE_{func}_run{r:02d}.log"
                if log_path.is_file():
                    vals.append(parse_fitness(log_path.read_text(encoding="utf-8", errors="replace")))
            if vals:
                summary[func] = {
                    "n": len(vals),
                    "mean": mean(vals),
                    "std": pstdev(vals) if len(vals) > 1 else 0.0,
                    "median": sorted(vals)[len(vals) // 2],
                }
        payload = {"method": "MASOIE", "runs_target": args.runs, "functions": summary}
        JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {JSON_OUT}")
        return

    masoie_dir = ensure_vendor()
    exe = build_masoie(masoie_dir)
    if args.build_only:
        print(f"Built {exe}")
        return

    summary = run_masoie_batch(exe, masoie_dir, funcs, args.runs, args.resume)
    payload = {
        "method": "MASOIE",
        "source_repo": MASOIE_REPO,
        "runs_target": args.runs,
        "note": "Consensus-based DBO benchmark; not identical to MACPO NDO F1-F6 topology.",
        "functions": {k: {kk: vv for kk, vv in v.items() if kk != "values"} for k, v in summary.items()},
        "raw_values": {k: v["values"] for k, v in summary.items()},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {JSON_OUT}")


if __name__ == "__main__":
    main()
