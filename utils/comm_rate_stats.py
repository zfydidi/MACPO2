"""Parse RL-MACPO / MACPO logs for communication trigger rate (comm_rate)."""
from __future__ import annotations

import re
import statistics as st
from pathlib import Path
from typing import Any

import numpy as np

from utils.rl_macpo_runlog import column_dict, load_llso_final_txt

_COST_STATS_RE = re.compile(
    r"#\s*COST_STATS.*?comm_rate=([0-9.eE+-]+)",
    re.S,
)


def parse_comm_rate_from_text(text: str) -> float | None:
    m = _COST_STATS_RE.search(text)
    if m:
        return float(m.group(1))
    return None


def parse_comm_rate_from_file(path: Path | str) -> float | None:
    path = Path(path)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    rate = parse_comm_rate_from_text(text)
    if rate is not None:
        return rate
    try:
        cols = column_dict(load_llso_final_txt(path))
    except (ValueError, OSError):
        return None
    if "gate_comm" not in cols:
        return None
    gc = cols["gate_comm"]
    if len(gc) == 0:
        return None
    return float(np.mean(gc))


def summarize_comm_rates(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "std": None}
    if len(values) == 1:
        return {"n": 1, "mean": float(values[0]), "std": 0.0}
    return {
        "n": len(values),
        "mean": float(st.mean(values)),
        "std": float(st.pstdev(values)),
    }


def load_run_comm_rates(paths: list[Path | str]) -> list[float]:
    out: list[float] = []
    for p in paths:
        v = parse_comm_rate_from_file(p)
        if v is not None:
            out.append(v)
    return out


def rl_llso_log_paths(
    func: str,
    *,
    root: Path,
    pattern: str,
    runs: int = 25,
) -> list[Path]:
    paths: list[Path] = []
    for i in range(1, runs + 1):
        for fmt in (pattern.format(run=i, run02=f"{i:02d}"),):
            p = root / fmt
            if p.is_file():
                paths.append(p)
                break
    return paths


def aggregate_function_comm(
    func: str,
    rl_paths: list[Path],
    macpo_rate: float = 1.0,
) -> dict[str, Any]:
    rl_vals = load_run_comm_rates(rl_paths)
    rl = summarize_comm_rates(rl_vals)
    m_mean = macpo_rate
    r_mean = rl["mean"]
    reduction = None
    if m_mean is not None and r_mean is not None and m_mean > 0:
        reduction = (m_mean - r_mean) / m_mean * 100.0
    return {
        "func": func,
        "macpo_comm_rate": m_mean,
        "rl_comm_rate_mean": r_mean,
        "rl_comm_rate_std": rl["std"],
        "rl_n": rl["n"],
        "comm_reduction_pct": reduction,
    }
