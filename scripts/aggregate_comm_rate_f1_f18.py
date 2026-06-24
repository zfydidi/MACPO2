#!/usr/bin/env python3
"""Aggregate comm_rate from RL-MACPO trajectory logs into comm_rate_f1_f18.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.comm_rate_stats import aggregate_function_comm, rl_llso_log_paths  # noqa: E402
from utils.ndo_run_stats import FUNCS_F1_F6, FUNCS_F7_F18  # noqa: E402

RL_F1_F6 = (
    _REPO
    / "ablation_experiments"
    / "Exp4_Variable_Selection"
    / "MACPO2_WithSelection_0.9_0.7_0.5"
    / "output"
)
RL_F7_F18 = _REPO / "MACPO2_deployment" / "output" / "LLSO"
COMM_OUT = _REPO / "ablation_experiments" / "results" / "comm_rate_f1_f18"
OUT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_rate_f1_f18.json"


def _paths_f1_f6(func: str, runs: int) -> list[Path]:
    custom = COMM_OUT / "F1_F6" / func
    if custom.is_dir():
        ps = sorted(custom.glob(f"{func}_LLSO_final_comm_*.txt"))
        if ps:
            return ps[:runs]
    return rl_llso_log_paths(
        func,
        root=RL_F1_F6,
        pattern=f"{func}_LLSO_run{{run02}}.txt",
        runs=runs,
    )


def _paths_f7_f18(func: str, runs: int) -> list[Path]:
    custom = COMM_OUT / "F7_F18" / func
    if custom.is_dir():
        ps = sorted(custom.glob(f"{func}_LLSO_final_comm_*.txt"))
        if not ps:
            ps = sorted(custom.glob(f"{func}_exp*.txt"))
        if ps:
            return ps[:runs]
    return rl_llso_log_paths(
        func,
        root=RL_F7_F18 / func,
        pattern=f"{func}_exp{{run02}}.txt",
        runs=runs,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=25)
    ap.add_argument("--out", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    rows: dict[str, dict] = {}
    for fn in FUNCS_F1_F6:
        paths = _paths_f1_f6(fn, args.runs)
        rows[fn] = aggregate_function_comm(fn, paths)
        rows[fn]["source"] = str(paths[0].parent) if paths else None
        rows[fn]["n_paths"] = len(paths)

    for fn in FUNCS_F7_F18:
        paths = _paths_f7_f18(fn, args.runs)
        rows[fn] = aggregate_function_comm(fn, paths)
        rows[fn]["source"] = str(paths[0].parent) if paths else None
        rows[fn]["n_paths"] = len(paths)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}")
    for fn in list(FUNCS_F1_F6) + list(FUNCS_F7_F18):
        r = rows[fn]
        m = r.get("rl_comm_rate_mean")
        print(
            fn,
            f"n={r.get('n_paths', 0)}",
            f"RL comm={m * 100:.1f}%" if m is not None else "RL comm=MISSING",
        )


if __name__ == "__main__":
    main()
