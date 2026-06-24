#!/usr/bin/env python3
"""MACPO baseline vs RL-MACPO(Full) 配对仿真实验。

实验协议：
- 问题集：F1–F6（网络化分布式黑盒优化标准测试集）
- 进程数：20（MPI）
- 优化器：LLSO
- 配对种子：MACPO_PAIR_SEED=run_id，保证两算法随机初始化一致
- 输出：experiments/patent_paired_comparison/raw/{MACPO,RL-MACPO}/

用法：
  python3 scripts/run_patent_paired_experiment.py --smoke       # F1×2 runs 快速验证
  python3 scripts/run_patent_paired_experiment.py --runs 25   # 完整实验
  python3 scripts/run_patent_paired_experiment.py --funcs F1 F3 --runs 5
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACPO_BIN = ROOT / "MACPO_sourcecode" / "build" / "MACPO_source"
RL_BIN = ROOT / "RL-MACPO" / "build" / "MACPO_simplified"
EXP_DIR = ROOT / "experiments" / "patent_paired_comparison"
RAW_MACPO = EXP_DIR / "raw" / "MACPO"
RAW_RL = EXP_DIR / "raw" / "RL-MACPO"
FUNCS_DEFAULT = ["F1", "F2", "F3", "F4", "F5", "F6"]
NP_DEFAULT = "20"


def run_cmd(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, float, str, str]:
    t0 = time.time()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.returncode, time.time() - t0, p.stdout, p.stderr


def ensure_bins() -> None:
    missing = [b for b in (MACPO_BIN, RL_BIN) if not b.exists()]
    if not missing:
        return
    print("正在编译缺失的二进制…", file=sys.stderr)
    for proj, target in [
        (ROOT / "MACPO_sourcecode" / "build", "MACPO_source"),
        (ROOT / "RL-MACPO" / "build", "MACPO_simplified"),
    ]:
        code, _, out, err = run_cmd(["make", target], proj)
        if code != 0:
            raise RuntimeError(f"编译失败 {proj}:\n{out}\n{err}")


def run_one(func: str, run_id: int, np_: str, skip_existing: bool) -> dict:
    rid = f"run{run_id:02d}"
    macpo_std = RAW_MACPO / f"{func}_{rid}.txt"
    macpo_native = RAW_MACPO / f"{func}_LLSO_{rid}.txt"
    rl_std = RAW_RL / f"{func}_{rid}.txt"
    rl_native = ROOT / "RL-MACPO" / "output" / f"{func}_LLSO_final_{rid}.txt"
    seed = str(run_id)
    env = {"MACPO_PAIR_SEED": seed}
    result = {"func": func, "run_id": run_id, "seed": seed}

    if not skip_existing or not macpo_std.exists():
        cmd = [
            "mpirun", "--oversubscribe", "-n", np_,
            str(MACPO_BIN), func, rid, "LLSO", str(RAW_MACPO) + "/",
        ]
        code, elapsed, out, err = run_cmd(cmd, ROOT / "MACPO_sourcecode", env)
        log_path = EXP_DIR / "logs" / f"MACPO_{func}_{rid}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(out + "\n" + err, encoding="utf-8")
        if macpo_native.exists() and not macpo_std.exists():
            shutil.copy2(macpo_native, macpo_std)
        result["macpo"] = {
            "ok": code == 0 and macpo_std.exists(),
            "wall_s": elapsed,
            "log": str(log_path),
            "output": str(macpo_std),
        }
        if code != 0 or not macpo_std.exists():
            result["macpo"]["error"] = err[-500:] if err else "output missing"
    else:
        result["macpo"] = {"ok": True, "skipped": True}

    if not skip_existing or not rl_std.exists():
        cmd = [
            "mpirun", "--oversubscribe", "-n", np_,
            str(RL_BIN), func, rid, "Full", str(RAW_RL) + "/",
        ]
        code, elapsed, out, err = run_cmd(cmd, ROOT / "RL-MACPO", env)
        src = rl_native if rl_native.exists() else RAW_RL / f"{func}_LLSO_final_{rid}.txt"
        if src.exists():
            shutil.copy2(src, rl_std)
        log_path = EXP_DIR / "logs" / f"RL-MACPO_{func}_{rid}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(out + "\n" + err, encoding="utf-8")
        result["rl_macpo"] = {
            "ok": code == 0 and rl_std.exists(),
            "wall_s": elapsed,
            "log": str(log_path),
            "output": str(rl_std),
        }
        if code != 0 or not rl_std.exists():
            result["rl_macpo"]["error"] = err[-500:] if err else "output missing"
    else:
        result["rl_macpo"] = {"ok": True, "skipped": True}

    return result


def write_manifest(funcs: list[str], runs: int, np_: str, results: list[dict]) -> None:
    manifest = {
        "experiment": "patent_paired_comparison",
        "description": "MACPO baseline vs RL-MACPO(Full) on NDO benchmarks F1-F6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "benchmarks": funcs,
            "runs_per_func": runs,
            "mpi_processes": int(np_),
            "optimizer": "LLSO",
            "macpo_binary": str(MACPO_BIN.relative_to(ROOT)),
            "rl_macpo_binary": str(RL_BIN.relative_to(ROOT)),
            "rl_config": "Full",
            "pair_seed_env": "MACPO_PAIR_SEED=run_id",
            "metrics": [
                "f_pure", "f_penalty", "conflict", "wall_s",
                "comm_rate", "avg_nego_dims", "rl_updates", "total_evals",
            ],
        },
        "jobs": results,
    }
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    (EXP_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MACPO vs RL-MACPO 配对仿真实验")
    parser.add_argument("--funcs", nargs="+", default=FUNCS_DEFAULT)
    parser.add_argument("--runs", type=int, default=25)
    parser.add_argument("--np", type=str, default=NP_DEFAULT)
    parser.add_argument("--smoke", action="store_true", help="F1×2 runs 快速验证")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip", dest="skip_existing", action="store_false")
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()

    if args.smoke:
        args.funcs = ["F1"]
        args.runs = 2

    RAW_MACPO.mkdir(parents=True, exist_ok=True)
    RAW_RL.mkdir(parents=True, exist_ok=True)

    if args.aggregate_only:
        subprocess.check_call(
            [sys.executable, str(ROOT / "utils" / "patent_experiment_aggregate.py")],
            cwd=str(ROOT),
        )
        return

    ensure_bins()

    total = len(args.funcs) * args.runs * 2
    print(f"实验开始：{len(args.funcs)} 函数 × {args.runs} 次 × 2 算法 = {total} 次 MPI 运行")
    results = []
    done = 0
    for func in args.funcs:
        for run_id in range(1, args.runs + 1):
            print(f"[{done+1}/{total}] {func} run{run_id:02d} …", flush=True)
            r = run_one(func, run_id, args.np, args.skip_existing)
            results.append(r)
            done += 2
            macpo_ok = r.get("macpo", {}).get("ok", False)
            rl_ok = r.get("rl_macpo", {}).get("ok", False)
            if not macpo_ok or not rl_ok:
                print(f"  WARNING: MACPO ok={macpo_ok}, RL ok={rl_ok}", file=sys.stderr)

    write_manifest(args.funcs, args.runs, args.np, results)
    print("聚合结果…")
    subprocess.check_call(
        [sys.executable, str(ROOT / "utils" / "patent_experiment_aggregate.py")],
        cwd=str(ROOT),
    )
    print(f"[完成] 结果目录：{EXP_DIR}")


if __name__ == "__main__":
    main()
