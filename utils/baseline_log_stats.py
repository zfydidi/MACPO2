"""Parse GFPDO/DPSO completion logs under MACPO_sourcecode/output_baselines*."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

_FINAL_RE = re.compile(
    r"final fitness=([0-9.eE+-]+)", re.IGNORECASE
)


def parse_final_fitness_log(path: Path | str) -> float | None:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    m = _FINAL_RE.search(text)
    return float(m.group(1)) if m else None


def load_baseline_series(
    out_dir: Path | str,
    method: str,
    func: str,
    embedded: str,
    exp_low: int = 1,
    exp_high: int = 5,
) -> np.ndarray:
    d = Path(out_dir)
    tag = func.upper()
    emb = embedded.upper()
    vals: list[float] = []
    for i in range(exp_low, exp_high + 1):
        ex = f"ex{i:02d}"
        p = d / f"{method}_{tag}_{emb}_{ex}.log"
        if not p.is_file():
            raise FileNotFoundError(p)
        fit = parse_final_fitness_log(p)
        if fit is None:
            raise ValueError(f"No final fitness in {p}")
        vals.append(fit)
    return np.asarray(vals, dtype=np.float64)


def summarize(vals: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
        "n": float(len(vals)),
    }
