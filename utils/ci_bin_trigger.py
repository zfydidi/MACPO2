"""
Bin-wise P(communication | conflict) from RL-MACPO run logs.

Typical use: equal-count quantile bins on pooled logged conflict, then mean gate_comm
per bin as empirical trigger probability.

Also supports parsing per-run ``# CI_BIN_TRIGGER`` footer lines (same statistic as C++).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from utils.conflict_alpha_bins import equal_count_conflict_bins, spearman_rho
from utils.rl_macpo_metrics_agg import glob_run_files
from utils.rl_macpo_runlog import column_dict, load_llso_final_txt

_CI_BIN_TRIGGER_RE = re.compile(r"bin(\d)_n=(\d+) bin\1_p=([\d.]+)")


@dataclass(frozen=True)
class CiBinTriggerResult:
    """Equal-count quantile bins on conflict, then gate_comm stats within each bin."""

    n_bins: int
    n_points: int
    n_runs: int
    conflict_lo: np.ndarray  # shape (n_bins,)
    conflict_hi: np.ndarray
    trigger_prob: np.ndarray  # mean gate_comm
    std_trigger: np.ndarray
    count: np.ndarray
    spearman_rho: float | None  # conflict vs gate_comm


def pool_conflict_gate_comm(
    paths: list[Path],
    *,
    exclude_iter0: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate (conflict, gate_comm) over all iteration rows and all runs."""
    c_all: list[np.ndarray] = []
    g_all: list[np.ndarray] = []
    for p in paths:
        parsed = load_llso_final_txt(p)
        cd = column_dict(parsed)
        if "conflict" not in cd:
            raise ValueError(f"Missing 'conflict' in {p}")
        if "gate_comm" not in cd:
            raise ValueError(f"Missing 'gate_comm' in {p}")
        c = np.asarray(cd["conflict"], dtype=float)
        g = np.asarray(cd["gate_comm"], dtype=float)
        if exclude_iter0 and "iter" in cd:
            mask0 = cd["iter"].astype(int) > 0
            c = c[mask0]
            g = g[mask0]
        c_all.append(c)
        g_all.append(g)
    c = np.concatenate(c_all)
    g = np.concatenate(g_all)
    mask = np.isfinite(c) & np.isfinite(g) & (c >= 0)
    return c[mask], g[mask]


def parse_ci_bin_trigger_line(line: str) -> list[tuple[int, int, float]] | None:
    """Parse one ``# CI_BIN_TRIGGER ...`` footer line."""
    if not line.lstrip().startswith("# CI_BIN_TRIGGER"):
        return None
    out: list[tuple[int, int, float]] = []
    for m in _CI_BIN_TRIGGER_RE.finditer(line):
        out.append((int(m.group(1)), int(m.group(2)), float(m.group(3))))
    return out or None


def aggregate_ci_bin_trigger_meta(paths: list[Path]) -> CiBinTriggerResult:
    """Pool ``# CI_BIN_TRIGGER`` counts across runs (low-CI bin = bin0)."""
    agg_n = np.zeros(5, dtype=int)
    agg_hit = np.zeros(5, dtype=float)
    n_runs = 0
    for p in paths:
        parsed = None
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            bins = parse_ci_bin_trigger_line(line)
            if bins is None:
                continue
            parsed = bins
        if parsed is None:
            continue
        n_runs += 1
        for b, n, prob in parsed:
            if 0 <= b < 5 and n > 0:
                agg_n[b] += n
                agg_hit[b] += prob * n
    if n_runs == 0:
        raise ValueError(f"No CI_BIN_TRIGGER footer in {len(paths)} files")
    trigger = np.array(
        [agg_hit[b] / agg_n[b] if agg_n[b] else 0.0 for b in range(5)],
        dtype=float,
    )
    return CiBinTriggerResult(
        n_bins=5,
        n_points=int(agg_n.sum()),
        n_runs=n_runs,
        conflict_lo=np.full(5, np.nan),
        conflict_hi=np.full(5, np.nan),
        trigger_prob=trigger,
        std_trigger=np.zeros(5),
        count=agg_n,
        spearman_rho=None,
    )


def analyze_runs(
    paths: list[Path],
    *,
    n_bins: int = 5,
    exclude_iter0: bool = False,
) -> CiBinTriggerResult:
    c, g = pool_conflict_gate_comm(paths, exclude_iter0=exclude_iter0)
    c_lo, c_hi, mean_g, std_g, cnt = equal_count_conflict_bins(c, g, n_bins=n_bins)
    rho = spearman_rho(c, g)
    return CiBinTriggerResult(
        n_bins=n_bins,
        n_points=int(c.size),
        n_runs=len(paths),
        conflict_lo=c_lo,
        conflict_hi=c_hi,
        trigger_prob=mean_g,
        std_trigger=std_g,
        count=cnt,
        spearman_rho=rho,
    )


def analyze_function_dir(
    runs_dir: Path,
    func_id: str,
    *,
    n_bins: int = 5,
    pattern: str = "{fn}_LLSO_final_run*.txt",
    source: str = "trajectory",
    exclude_iter0: bool = False,
) -> CiBinTriggerResult:
    paths = glob_run_files(runs_dir, func_id, pattern=pattern)
    if len(paths) < 1:
        raise ValueError(f"No files for {func_id} under {runs_dir}")
    if source == "meta":
        return aggregate_ci_bin_trigger_meta(paths)
    if source == "trajectory":
        return analyze_runs(paths, n_bins=n_bins, exclude_iter0=exclude_iter0)
    raise ValueError(f"Unknown source={source!r}; use 'trajectory' or 'meta'")
