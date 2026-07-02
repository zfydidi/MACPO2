"""GFPDO / DPSO anchors for Table I (F1--F6).

GFPDO: single-run pilot under MACPO_sourcecode/output_baselines_gfpdo_1run.
DPSO LLSO: prefer ablation_experiments/results/external_baselines_25runs_unified/summary.json.
DPSO CSO: 25-run batch under MACPO_sourcecode/output_baselines_dpso_25runs.
Falls back to MACPO paper Table I when logs are missing.
"""
from __future__ import annotations

import json
from pathlib import Path

from utils.baseline_log_stats import load_baseline_series_optional, summarize

_REPO = Path(__file__).resolve().parents[1]
GFPDO_DIR = _REPO / "MACPO_sourcecode" / "output_baselines_gfpdo_1run"
DPSO_DIR = _REPO / "MACPO_sourcecode" / "output_baselines_dpso_25runs"
DPSO_UNIFIED_SUMMARY = (
    _REPO
    / "ablation_experiments"
    / "results"
    / "external_baselines_25runs_unified"
    / "summary.json"
)

# Literature fallback (ref_macpo Table I).
_GFPDO_LLSO_FALLBACK: dict[str, tuple[float, float, float]] = {
    "F1": (8.46e8, 8.29e8, 8.46e7),
    "F2": (9.43e6, 9.26e6, 4.13e6),
    "F3": (5.86e10, 5.83e10, 4.22e9),
    "F4": (4.53e8, 4.67e8, 6.74e7),
    "F5": (2.11e10, 2.05e10, 2.24e9),
    "F6": (4.00e10, 3.93e10, 4.31e9),
}
_DPSO_LLSO_FALLBACK: dict[str, tuple[float, float, float]] = {
    "F1": (2.25e10, 2.23e10, 2.66e9),
    "F2": (5.61e10, 1.34e10, 9.39e10),
    "F3": (3.86e10, 3.87e10, 5.62e8),
    "F4": (1.68e10, 1.67e10, 2.33e9),
    "F5": (2.65e10, 2.68e10, 1.87e9),
    "F6": (2.72e10, 2.71e10, 2.87e9),
}
_GFPDO_CSO_FALLBACK: dict[str, tuple[float, float, float]] = {
    "F1": (2.06e10, 2.06e10, 3.15e9),
    "F2": (2.37e9, 7.07e8, 4.34e9),
    "F3": (1.04e11, 1.03e11, 3.92e9),
    "F4": (8.62e9, 7.43e9, 3.16e9),
    "F5": (5.60e10, 5.57e10, 3.77e9),
    "F6": (5.23e10, 5.22e10, 4.16e9),
}
_DPSO_CSO_FALLBACK: dict[str, tuple[float, float, float]] = {
    "F1": (3.65e10, 3.72e10, 4.15e9),
    "F2": (2.69e10, 5.56e9, 6.51e10),
    "F3": (3.99e10, 3.97e10, 1.12e9),
    "F4": (1.89e10, 1.82e10, 4.13e9),
    "F5": (4.30e10, 4.31e10, 4.11e9),
    "F6": (4.00e10, 3.27e10, 2.24e10),
}

EXTERNAL_REF_PVALUE = "---"


def _tuple_from_unified_dpso_llso(
    fallback: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]] | None:
    if not DPSO_UNIFIED_SUMMARY.is_file():
        return None
    try:
        data = json.loads(DPSO_UNIFIED_SUMMARY.read_text(encoding="utf-8"))
        summary = data.get("summary", {}).get("DPSO", {})
    except (OSError, json.JSONDecodeError, KeyError):
        return None
    out: dict[str, tuple[float, float, float]] = {}
    for i in range(1, 7):
        fn = f"F{i}"
        entry = summary.get(fn)
        if not entry or entry.get("runs", 0) < 25:
            return None
        out[fn] = (entry["mean"], entry["median"], entry["std"])
    return out


def _tuple_from_dir(
    out_dir: Path,
    method: str,
    embedded: str,
    runs: int,
    fallback: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    out: dict[str, tuple[float, float, float]] = {}
    for i in range(1, 7):
        fn = f"F{i}"
        vals, _ = load_baseline_series_optional(out_dir, method, fn, embedded, runs)
        if len(vals):
            s = summarize(vals)
            out[fn] = (s["mean"], s["median"], s["std"])
        else:
            out[fn] = fallback[fn]
    return out


def _load_all() -> tuple[
    dict[str, tuple[float, float, float]],
    dict[str, tuple[float, float, float]],
    dict[str, tuple[float, float, float]],
    dict[str, tuple[float, float, float]],
]:
    gfpdo_llso = _tuple_from_dir(GFPDO_DIR, "GFPDO", "LLSO", 1, _GFPDO_LLSO_FALLBACK)
    gfpdo_cso = _tuple_from_dir(GFPDO_DIR, "GFPDO", "CSO", 1, _GFPDO_CSO_FALLBACK)
    dpso_llso = _tuple_from_unified_dpso_llso(_DPSO_LLSO_FALLBACK) or _tuple_from_dir(
        DPSO_DIR, "DPSO1", "LLSO", 25, _DPSO_LLSO_FALLBACK
    )
    dpso_cso = _tuple_from_dir(DPSO_DIR, "DPSO1", "CSO", 25, _DPSO_CSO_FALLBACK)
    return gfpdo_llso, dpso_llso, gfpdo_cso, dpso_cso


GFPDO_LLSO, DPSO_LLSO, GFPDO_CSO, DPSO_CSO = _load_all()
