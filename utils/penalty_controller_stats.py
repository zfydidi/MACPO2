"""Aggregate F3/F5 penalty-controller baseline runs (MACPO vs EMA vs fixed vs RL)."""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.comm_rate_stats import load_run_comm_rates
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt
MACPO_LLSO = _REPO / "MACPO_original_output" / "LLSO_25runs"


def _f_pure_from_rl_log(path: Path) -> float | None:
    try:
        cols = column_dict(load_llso_final_txt(path))
    except (ValueError, OSError):
        return None
    if "f_pure_bsf" in cols and len(cols["f_pure_bsf"]):
        return float(cols["f_pure_bsf"][-1])
    for key in ("f_pure", "global_fit", "fitness"):
        if key in cols and len(cols[key]):
            return float(cols[key][-1])
    return None


def _f_pure_from_macpo_log(path: Path) -> float | None:
    if not path.is_file():
        return None
    lines = [
        ln.strip()
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip() and not ln.lower().startswith("iteration")
    ]
    if not lines:
        return None
    last = lines[-1].split()
    if len(last) < 4:
        return None
    try:
        return float(last[3])
    except ValueError:
        return None


def _summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "std": None}
    if len(values) == 1:
        return {"n": 1, "mean": float(values[0]), "std": 0.0}
    return {"n": len(values), "mean": float(st.mean(values)), "std": float(st.pstdev(values))}


def rl_log_paths(root: Path, func: str, runs: int = 25) -> list[Path]:
    paths: list[Path] = []
    for i in range(1, runs + 1):
        run_id = f"{i:02d}"
        for name in (
            f"{func}_LLSO_final_run{run_id}.txt",
            f"{func}_LLSO_final_run{i}.txt",
            f"{func}_LLSO_run{run_id}.txt",
        ):
            p = root / name
            if p.is_file():
                paths.append(p)
                break
    return paths


def macpo_log_paths(func: str, runs: int = 25) -> list[Path]:
    paths: list[Path] = []
    for i in range(1, runs + 1):
        for name in (f"{func}_LLSO_run{i:02d}.txt", f"{func}_LLSO_run{i}.txt"):
            p = MACPO_LLSO / name
            if p.is_file():
                paths.append(p)
                break
    return paths


def aggregate_controller(
    func: str,
    controller: str,
    root: Path,
    *,
    runs: int = 25,
) -> dict[str, Any]:
    if controller == "MACPO":
        paths = macpo_log_paths(func, runs)
        f_vals = [_f_pure_from_macpo_log(p) for p in paths]
        comm_vals = [1.0] * len([v for v in f_vals if v is not None])
    else:
        paths = rl_log_paths(root, func, runs)
        f_vals = [_f_pure_from_rl_log(p) for p in paths]
        comm_vals = load_run_comm_rates(paths)
    f_clean = [v for v in f_vals if v is not None]
    return {
        "controller": controller,
        "function": func,
        "n_logs": len(paths),
        "fitness": _summarize(f_clean),
        "comm_rate": _summarize(comm_vals),
        "log_dir": str(root),
    }


def aggregate_penalty_baselines(
    *,
    out_root: Path,
    funcs: tuple[str, ...] = ("F3", "F5"),
    runs: int = 25,
) -> dict[str, Any]:
    controllers = {
        "MACPO": MACPO_LLSO,
        "FixedSchedule": out_root / "FixedSchedule",
        "EMA_Penalty": out_root / "EMA_Penalty",
        "RL": out_root / "Selection_0.9_0.7_0.5",
    }
    rows: list[dict[str, Any]] = []
    for func in funcs:
        for name, root in controllers.items():
            if name == "MACPO":
                row = aggregate_controller(func, name, root, runs=runs)
            else:
                row = aggregate_controller(func, name, root, runs=runs)
            rows.append(row)
    return {"runs": runs, "functions": list(funcs), "rows": rows}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=_REPO / "ablation_experiments" / "results" / "penalty_controller_f3_f5",
    )
    parser.add_argument("--runs", type=int, default=25)
    parser.add_argument(
        "--out",
        type=Path,
        default=_REPO
        / "RL_MACPO_IEEE_English_with_images"
        / "media"
        / "penalty_controller_f3_f5.json",
    )
    args = parser.parse_args()
    payload = aggregate_penalty_baselines(out_root=args.root, runs=args.runs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({len(payload['rows'])} rows)")


if __name__ == "__main__":
    main()
