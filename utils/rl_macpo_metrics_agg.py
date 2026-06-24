"""
Aggregate per-run RL-MACPO trajectory logs onto a common evaluation (FES) grid.

Used for mean ± std plots over multiple independent runs (e.g. 25 seeds).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from utils.rl_macpo_runlog import column_dict, load_llso_final_txt


def resolve_column(paths: list[str | Path], *candidates: str) -> str:
    """
    Pick the first column name that exists in the first run file.

    New 20-col logs use avg_alpha; legacy 13-col logs use alpha_avg.
    """
    if not paths:
        raise ValueError("paths is empty")
    parsed = load_llso_final_txt(paths[0])
    cd = column_dict(parsed)
    for c in candidates:
        if c in cd:
            return c
    avail = list(cd.keys())
    raise ValueError(
        f"None of {list(candidates)} in {paths[0]}; columns: {avail}"
    )


def aggregate_by_eval(
    paths: list[str | Path],
    column: str,
    *,
    eval_key: str = "eval",
    n_grid: int = 256,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """
    Interpolate each run onto linspace(eval_min, eval_max, n_grid), then mean/std.

    Returns (eval_grid, mean_y, std_y, n_used). Skips files missing columns.
    """
    series: list[tuple[np.ndarray, np.ndarray]] = []
    for p in paths:
        try:
            parsed = load_llso_final_txt(p)
            cd = column_dict(parsed)
        except (OSError, ValueError):
            continue
        if column not in cd or eval_key not in cd:
            continue
        e = np.asarray(cd[eval_key], dtype=float)
        y = np.asarray(cd[column], dtype=float)
        if e.size < 2:
            continue
        order = np.argsort(e)
        e = e[order]
        y = y[order]
        # Deduplicate eval (rare)
        ue, inv = np.unique(e, return_inverse=True)
        if len(ue) < len(e):
            yb = np.zeros_like(ue)
            cnt = np.zeros_like(ue)
            for i, idx in enumerate(inv):
                yb[idx] += y[i]
                cnt[idx] += 1
            y = yb / np.maximum(cnt, 1)
            e = ue
        series.append((e, y))

    if not series:
        raise ValueError(f"No valid series for column {column!r}")

    emin = min(float(np.min(s[0])) for s in series)
    emax = max(float(np.max(s[0])) for s in series)
    if emax <= emin:
        raise ValueError("Empty or degenerate eval range")
    eval_grid = np.linspace(emin, emax, n_grid)
    rows: list[np.ndarray] = []
    for e, y in series:
        rows.append(np.interp(eval_grid, e, y))
    mat = np.vstack(rows)
    return eval_grid, np.nanmean(mat, axis=0), np.nanstd(mat, axis=0), mat.shape[0]


def glob_run_files(runs_dir: Path, func_id: str, pattern: str = "{fn}_LLSO_final_run*.txt") -> list[Path]:
    """Sorted list of run logs for one benchmark (e.g. F3_LLSO_final_run01.txt …)."""
    pat = pattern.format(fn=func_id)
    files = sorted(runs_dir.glob(pat))
    return [p for p in files if p.is_file()]
