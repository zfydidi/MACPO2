"""
Empirical per-loop drift statistics from archived RL-MACPO logs.

Proposition 1 uses per-dimension normalized gap e_d^t. Logs do not archive e_d
per dimension; we therefore report |Δ conflict| between consecutive outer loops
as a conservative proxy for per-loop movement in the logged conflict signal
(Eq. ci_dim aggregate).
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from utils.rl_macpo_metrics_agg import glob_run_files
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt

_DIFF_FOOTER_RE = re.compile(
    r"diff_mean=([\d.eE+-]+).*diff_max=([\d.eE+-]+).*diff_p95=([\d.eE+-]+)", re.I
)


@dataclass(frozen=True)
class DriftRunStats:
    n_steps: int
    n_silent_steps: int
    delta_mean: float
    delta_max: float
    delta_p95: float
    footer_diff_max: float | None
    footer_diff_p95: float | None
    footer_diff_mean: float | None


def _parse_diff_footer(meta: list[str]) -> tuple[float | None, float | None, float | None]:
    for line in meta:
        if "GATE_DEBUG_CI_TAU" not in line:
            continue
        m = _DIFF_FOOTER_RE.search(line)
        if m:
            return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None, None, None


def drift_stats_from_log(path: Path) -> DriftRunStats | None:
    try:
        loaded = load_llso_final_txt(path)
    except (ValueError, OSError):
        return None
    cd = column_dict(loaded)
    if "conflict" not in cd:
        return None
    conflict = np.asarray(cd["conflict"], dtype=float)
    if conflict.size < 2:
        return None
    delta = np.abs(np.diff(conflict))
    silent_mask = np.ones(delta.shape[0], dtype=bool)
    if "gate_comm" in cd:
        gate = np.asarray(cd["gate_comm"], dtype=float)
        # step t->t+1 attributed to post-step gate_comm at t+1 (silent if no comm at t+1)
        silent_mask = gate[1:] < 0.5
    silent_delta = delta[silent_mask] if np.any(silent_mask) else delta
    fmean, fmax, fp95 = _parse_diff_footer(loaded["meta"])
    return DriftRunStats(
        n_steps=int(delta.size),
        n_silent_steps=int(silent_delta.size),
        delta_mean=float(np.mean(silent_delta)),
        delta_max=float(np.max(silent_delta)),
        delta_p95=float(np.percentile(silent_delta, 95)),
        footer_diff_max=fmax,
        footer_diff_p95=fp95,
        footer_diff_mean=fmean,
    )


def aggregate_drift_for_function(log_dir: Path, func_id: str) -> dict[str, float]:
    paths = glob_run_files(log_dir, func_id)
    if not paths:
        return {}
    runs: list[DriftRunStats] = []
    for p in paths:
        st = drift_stats_from_log(p)
        if st is not None:
            runs.append(st)
    if not runs:
        return {"n_runs": 0}
    pooled = np.concatenate(
        [
            np.array([r.delta_mean, r.delta_max, r.delta_p95])
            for r in runs
        ]
    )
    footer_max = [r.footer_diff_max for r in runs if r.footer_diff_max is not None]
    footer_p95 = [r.footer_diff_p95 for r in runs if r.footer_diff_p95 is not None]
    footer_mean = [r.footer_diff_mean for r in runs if r.footer_diff_mean is not None]
    return {
        "n_runs": len(runs),
        "mean_delta_mean": float(np.mean([r.delta_mean for r in runs])),
        "mean_delta_max": float(np.mean([r.delta_max for r in runs])),
        "pooled_delta_p95": float(np.percentile(pooled, 95)),
        "pooled_delta_max": float(np.max([r.delta_max for r in runs])),
        "footer_diff_max_mean": float(np.mean(footer_max)) if footer_max else None,
        "footer_diff_p95_mean": float(np.mean(footer_p95)) if footer_p95 else None,
        "footer_diff_mean_mean": float(np.mean(footer_mean)) if footer_mean else None,
        "pooled_footer_diff_max": float(np.max(footer_max)) if footer_max else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-loop conflict drift stats for Appendix")
    parser.add_argument(
        "--log-root",
        type=Path,
        default=Path("experiments/patent_paired_comparison/raw/RL-MACPO"),
    )
    parser.add_argument(
        "--pattern",
        default="F{func}_LLSO_final_run*.txt",
        help="Glob pattern with {func} placeholder",
    )
    parser.add_argument(
        "--functions",
        default="F1,F2,F3,F4,F5,F6",
        help="Comma-separated benchmark names",
    )
    parser.add_argument("--out-json", type=Path, required=True)
    args = parser.parse_args()

    out: dict[str, dict] = {}
    for func in args.functions.split(","):
        func = func.strip()
        stats = aggregate_drift_for_function(args.log_root, func)
        out[func] = stats

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
