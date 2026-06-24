"""
Load NDO benchmark (F1–F18) per-run final f_pure from MACPO/RL-MACPO trajectory logs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import stats

from utils.fes_plot import load_trajectory

FUNCS_F1_F6 = ("F1", "F2", "F3", "F4", "F5", "F6")
FUNCS_F7_F18 = tuple(f"F{i}" for i in range(7, 19))


def final_fpure_from_trajectory(path: Path | str) -> float:
    """Last logged f_pure in a whitespace-separated iter/eval/f_penalty/f_pure log."""
    ev, fp = load_trajectory(str(path))
    if len(fp) == 0:
        raise ValueError(f"No f_pure rows in {path}")
    return float(fp[-1])


def final_eva_from_trajectory(path: Path | str) -> int:
    ev, _ = load_trajectory(str(path))
    if len(ev) == 0:
        raise ValueError(f"No eval rows in {path}")
    return int(ev[-1])


def load_run_fpure_series(
    directory: Path | str,
    func: str,
    embedded: str = "LLSO",
    run_low: int = 1,
    run_high: int = 25,
) -> np.ndarray:
    """Load f_pure final values for run01..run25 from ``{Fn}_{emb}_run{i:02d}.txt``."""
    d = Path(directory)
    tag = func.upper()
    emb = embedded.upper()
    vals: list[float] = []
    for i in range(run_low, run_high + 1):
        p = d / f"{tag}_{emb}_run{i:02d}.txt"
        if not p.is_file():
            raise FileNotFoundError(f"Missing run log: {p}")
        vals.append(final_fpure_from_trajectory(p))
    return np.asarray(vals, dtype=np.float64)


def load_run_fpure_series_exp(
    func_dir: Path | str,
    func: str,
    exp_low: int = 1,
    exp_high: int = 25,
) -> np.ndarray:
    """Load f_pure finals from ``{Fn}_exp{i:02d}.txt`` under a per-function directory."""
    d = Path(func_dir)
    tag = func.upper()
    vals: list[float] = []
    for i in range(exp_low, exp_high + 1):
        p = d / f"{tag}_exp{i:02d}.txt"
        if not p.is_file():
            raise FileNotFoundError(f"Missing run log: {p}")
        vals.append(final_fpure_from_trajectory(p))
    return np.asarray(vals, dtype=np.float64)


def fmt_macpo_cell(mean: float, std: float) -> str:
    """Table II cell: mean with std on second line."""
    return (
        f"\\makecell{{{fmt_sci_tex(mean)}\\\\{{\\scriptsize $\\pm${fmt_sci_tex(std)}}}}}"
    )


def summarize_runs(vals: np.ndarray) -> dict[str, float]:
    if len(vals) == 0:
        raise ValueError("empty run series")
    return {
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
        "n": float(len(vals)),
    }


def wilcoxon_less_p(baseline: np.ndarray, other: np.ndarray) -> float:
    """Paired Wilcoxon one-sided: H1 other < baseline."""
    if len(baseline) != len(other) or len(baseline) < 5:
        return float("nan")
    try:
        res = stats.wilcoxon(other, baseline, alternative="less", zero_method="wilcox")
        return float(res.pvalue)
    except ValueError:
        return float("nan")


def mannwhitney_less_p(baseline: np.ndarray, other: np.ndarray) -> float:
    """Unpaired Mann–Whitney one-sided: H1 other < baseline."""
    if len(baseline) < 5 or len(other) < 5:
        return float("nan")
    res = stats.mannwhitneyu(other, baseline, alternative="less")
    return float(res.pvalue)


def fmt_sci_tex(x: float) -> str:
    if x == 0 or not np.isfinite(x):
        return "0"
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10**exp)
    sign = "+" if exp >= 0 else ""
    return f"{mant:.2f}E{sign}{exp}"


def fmt_pvalue_tex(p: float, rl_better: bool, rl_worse: bool) -> str:
    if not np.isfinite(p):
        return "-"
    s = f"{p:.2e}"
    if rl_better and p < 0.05:
        s += "*"
    elif rl_worse and p < 0.05:
        s += "\\#"
    return s


def wtl_counts(baseline: np.ndarray, other: np.ndarray) -> tuple[int, int, int]:
    w = t = l = 0
    for b, o in zip(baseline, other):
        if o < b:
            w += 1
        elif o > b:
            l += 1
        else:
            t += 1
    return w, t, l
