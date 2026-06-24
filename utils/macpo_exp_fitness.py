"""
Load per-run summary logs (MACPO / MACPO-style experiments) that report:

    Final Fitness: <float>

Supports multiple directory layouts used in this repository.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np

_FINAL_RE = re.compile(r"Final Fitness:\s*([0-9.eE+-]+)", re.MULTILINE)
_FINAL_LOG_RE = re.compile(r"final fitness=([0-9.eE+-]+)", re.IGNORECASE | re.MULTILINE)
_EXP_RE = re.compile(r"_exp(\d+)")


def parse_final_fitness(text: str) -> float | None:
    m = _FINAL_RE.search(text)
    if not m:
        return None
    return float(m.group(1))


def parse_final_fitness_from_log(text: str) -> float | None:
    m = _FINAL_LOG_RE.search(text)
    if not m:
        return None
    return float(m.group(1))


def iter_final_fitness_files(
    function_tag: str,
    embedded: str,
    exp_low: int,
    exp_high: int,
    roots: Iterable[Path | str],
) -> list[tuple[int, Path, float]]:
    """
    Collect Final Fitness values for Fk_{embedded}_expXX.txt under roots.

    Each ``root`` should be a directory that *contains* the function folder
    (e.g. ``.../MACPO_original_log/LLSO`` which contains ``F7/F7_LLSO_exp01.txt``).
    Returns sorted list of (exp_id, path, fitness).
    """
    out: list[tuple[int, Path, float]] = []
    tag = function_tag.upper()
    emb = embedded.upper()
    pattern = f"{tag}_{emb}_exp*.txt"
    for root in roots:
        r = Path(root)
        func_dir = r / tag
        if not func_dir.is_dir():
            continue
        for p in sorted(func_dir.glob(pattern)):
            m = _EXP_RE.search(p.name)
            if not m:
                continue
            eid = int(m.group(1))
            if not (exp_low <= eid <= exp_high):
                continue
            fit = parse_final_fitness(p.read_text(encoding="utf-8", errors="replace"))
            if fit is None:
                continue
            out.append((eid, p.resolve(), fit))
    out.sort(key=lambda x: x[0])
    return out


def stats25(
    function_tag: str,
    embedded: str,
    exp_low: int = 1,
    exp_high: int = 25,
) -> tuple[np.ndarray, float, float]:
    """
    Mean and sample std (ddof=1) over exp01..exp25 for MACPO logs in repo defaults.
    """
    repo = Path(__file__).resolve().parents[1]
    emb = embedded.upper()
    # Each root is a parent that contains ``F7/``, ``F18/``, etc.
    roots = [
        repo / "MACPO_original_output" / "MACPO_original_log" / emb,
        repo / "MACPO_original_output" / emb,
    ]
    rows = iter_final_fitness_files(function_tag, embedded, exp_low, exp_high, roots)
    if not rows:
        raise FileNotFoundError(
            f"No logs for {function_tag} {embedded} exp{exp_low}-{exp_high} under {roots}"
        )
    vals = np.array([r[2] for r in rows], dtype=np.float64)
    return vals, float(np.mean(vals)), float(np.std(vals, ddof=1))


def load_macpo_final_fitness_series(
    function_tag: str,
    embedded: str,
    exp_low: int = 1,
    exp_high: int = 25,
    repo: Path | None = None,
) -> np.ndarray:
    """
    Per-run archived MACPO penalized ``final fitness`` for F7--F18.

    Prefers completion ``.log`` files under ``MACPO_original_output/{LLSO|CSO}/{Fn}/``;
    falls back to ``MACPO_original_log`` summary ``Final Fitness`` files.
    """
    root = repo or Path(__file__).resolve().parents[1]
    tag = function_tag.upper()
    emb = embedded.upper()
    vals: list[float] = []

    log_dir = root / "MACPO_original_output" / emb / tag
    summary_roots = [
        root / "MACPO_original_output" / "MACPO_original_log" / emb,
        root / "MACPO_original_output" / emb,
    ]
    for i in range(exp_low, exp_high + 1):
        log_path = log_dir / f"{emb}_{tag}_exp{i:02d}.log"
        if log_path.is_file():
            fit = parse_final_fitness_from_log(
                log_path.read_text(encoding="utf-8", errors="replace")
            )
            if fit is not None:
                vals.append(fit)
                continue
        for sroot in summary_roots:
            rows = iter_final_fitness_files(tag, embedded, i, i, [sroot])
            if rows:
                vals.append(rows[0][2])
                break
        else:
            direct = log_dir / f"{tag}_{emb}_exp{i:02d}.txt"
            if direct.is_file():
                fit = parse_final_fitness(direct.read_text(encoding="utf-8", errors="replace"))
                if fit is not None:
                    vals.append(fit)
                    continue
            raise FileNotFoundError(
                f"No MACPO final fitness for {tag} {emb} exp{i:02d}"
            )

    return np.asarray(vals, dtype=np.float64)
