"""
Bin-wise association between conflict and mean alpha from RL-MACPO run logs.

Typical use: equal-count quantile bins on pooled conflict (high conflict → higher alpha).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from utils.rl_macpo_metrics_agg import glob_run_files, resolve_column
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt


@dataclass(frozen=True)
class ConflictAlphaBinResult:
    """Equal-count quantile bins on conflict (sorted), then stats on alpha within each bin."""

    n_bins: int
    n_points: int
    n_runs: int
    conflict_lo: np.ndarray  # shape (n_bins,)
    conflict_hi: np.ndarray
    mean_alpha: np.ndarray
    std_alpha: np.ndarray
    count: np.ndarray
    spearman_rho: float | None  # None if scipy unavailable


def pool_conflict_alpha(paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate (conflict, alpha) over all iteration rows and all runs."""
    c_all: list[np.ndarray] = []
    a_all: list[np.ndarray] = []
    for p in paths:
        parsed = load_llso_final_txt(p)
        cd = column_dict(parsed)
        if "conflict" not in cd:
            raise ValueError(f"Missing 'conflict' in {p}")
        alpha_key = resolve_column([p], "avg_alpha", "alpha_avg")
        c_all.append(np.asarray(cd["conflict"], dtype=float))
        a_all.append(np.asarray(cd[alpha_key], dtype=float))
    c = np.concatenate(c_all)
    a = np.concatenate(a_all)
    mask = np.isfinite(c) & np.isfinite(a) & (c >= 0)
    return c[mask], a[mask]


def equal_count_conflict_bins(
    conflict: np.ndarray,
    alpha: np.ndarray,
    n_bins: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Sort by conflict, split into n_bins equal-count slices, return per-bin alpha stats.

    Returns (c_lo, c_hi, mean_alpha, std_alpha, count) each shape (n_bins,).
    """
    c = np.asarray(conflict, dtype=float)
    a = np.asarray(alpha, dtype=float)
    order = np.argsort(c)
    c, a = c[order], a[order]
    n = c.size
    if n < n_bins:
        raise ValueError(f"Need at least n_bins={n_bins} points, got {n}")

    c_lo = np.empty(n_bins)
    c_hi = np.empty(n_bins)
    mean_a = np.empty(n_bins)
    std_a = np.empty(n_bins)
    cnt = np.empty(n_bins, dtype=int)

    for b in range(n_bins):
        lo = b * n // n_bins
        hi = (b + 1) * n // n_bins if b < n_bins - 1 else n
        cb = c[lo:hi]
        ab = a[lo:hi]
        c_lo[b] = cb[0]
        c_hi[b] = cb[-1]
        mean_a[b] = float(np.mean(ab))
        std_a[b] = float(np.std(ab, ddof=1)) if ab.size > 1 else 0.0
        cnt[b] = hi - lo

    return c_lo, c_hi, mean_a, std_a, cnt


def spearman_rho(conflict: np.ndarray, alpha: np.ndarray) -> float | None:
    try:
        from scipy import stats  # type: ignore[import-untyped]

        r, _ = stats.spearmanr(conflict, alpha)
        return float(r) if np.isfinite(r) else None
    except Exception:
        return None


def analyze_runs(
    paths: list[Path],
    *,
    n_bins: int = 5,
) -> ConflictAlphaBinResult:
    c, a = pool_conflict_alpha(paths)
    c_lo, c_hi, mean_a, std_a, cnt = equal_count_conflict_bins(c, a, n_bins=n_bins)
    rho = spearman_rho(c, a)
    return ConflictAlphaBinResult(
        n_bins=n_bins,
        n_points=int(c.size),
        n_runs=len(paths),
        conflict_lo=c_lo,
        conflict_hi=c_hi,
        mean_alpha=mean_a,
        std_alpha=std_a,
        count=cnt,
        spearman_rho=rho,
    )


def analyze_function_dir(
    runs_dir: Path,
    func_id: str,
    *,
    n_bins: int = 5,
    pattern: str = "{fn}_LLSO_final_run*.txt",
) -> ConflictAlphaBinResult:
    paths = glob_run_files(runs_dir, func_id, pattern=pattern)
    if len(paths) < 1:
        raise ValueError(f"No files for {func_id} under {runs_dir}")
    return analyze_runs(paths, n_bins=n_bins)
