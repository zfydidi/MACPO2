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


def parse_final_fitness_iter(path: Path | str) -> float | None:
    """Last BestFitness from iter_{METHOD}_F*_OPT_ex*.txt (CSV: iter, fitness)."""
    lines = [
        ln.strip()
        for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip() and not ln.lower().startswith("iteration")
    ]
    if not lines:
        return None
    last = lines[-1]
    if "," in last:
        part = last.split(",")[-1].strip()
    else:
        part = last.split()[-1]
    try:
        return float(part)
    except ValueError:
        return None


def parse_final_fitness_any(path: Path | str) -> float | None:
    p = Path(path)
    if not p.is_file():
        return None
    if p.suffix == ".log" or "final fitness" in p.read_text(encoding="utf-8", errors="replace")[:500]:
        fit = parse_final_fitness_log(p)
        if fit is not None:
            return fit
    if p.name.startswith("iter_"):
        return parse_final_fitness_iter(p)
    return None


def _candidate_paths(
    out_dir: Path,
    method: str,
    func: str,
    embedded: str,
    ex: str,
) -> list[Path]:
    tag = func.upper()
    emb = embedded.upper()
    return [
        out_dir / f"{method}_{tag}_{emb}_{ex}.log",
        out_dir / f"iter_{method}_{tag}_{emb}_{ex}.txt",
    ]


def load_baseline_series_optional(
    out_dir: Path | str,
    method: str,
    func: str,
    embedded: str,
    runs: int = 25,
) -> tuple[np.ndarray, list[str]]:
    """Return (values, missing ex ids) — does not raise on missing runs."""
    d = Path(out_dir)
    vals: list[float] = []
    missing: list[str] = []
    for i in range(1, runs + 1):
        ex = f"ex{i:02d}"
        fit = None
        for p in _candidate_paths(d, method, func, embedded, ex):
            fit = parse_final_fitness_any(p)
            if fit is not None:
                break
        if fit is None:
            missing.append(ex)
        else:
            vals.append(fit)
    return np.asarray(vals, dtype=np.float64), missing


def load_baseline_series(
    out_dir: Path | str,
    method: str,
    func: str,
    embedded: str,
    exp_low: int = 1,
    exp_high: int = 25,
) -> np.ndarray:
    d = Path(out_dir)
    vals: list[float] = []
    for i in range(exp_low, exp_high + 1):
        ex = f"ex{i:02d}"
        fit = None
        used = None
        for p in _candidate_paths(d, method, func, embedded, ex):
            fit = parse_final_fitness_any(p)
            if fit is not None:
                used = p
                break
        if fit is None:
            raise FileNotFoundError(
                f"No final fitness for {method} {func} {embedded} {ex} under {d}"
            )
        vals.append(fit)
    return np.asarray(vals, dtype=np.float64)


def summarize(vals: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
        "n": float(len(vals)),
    }


def count_completed_runs(
    out_dir: Path | str,
    method: str,
    func: str,
    embedded: str,
    runs: int = 25,
) -> int:
    d = Path(out_dir)
    n = 0
    for i in range(1, runs + 1):
        ex = f"ex{i:02d}"
        for p in _candidate_paths(d, method, func, embedded, ex):
            if parse_final_fitness_any(p) is not None:
                n += 1
                break
    return n
