"""
Load RL-MACPO LLSO trajectory files (*_LLSO_final_*.txt) written by MACPO_simplified.

Format:
  - Lines starting with '#' are comments; a line '# COLUMNS(tab): ...' lists tab-separated names.
  - Data rows: tab-separated floats/ints, one row per outer iteration.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np


def _parse_columns_line(line: str) -> list[str] | None:
    m = re.search(r"#\s*COLUMNS\s*\([^)]*\)\s*:\s*(.+)", line, re.I)
    if not m:
        return None
    return [c.strip() for c in m.group(1).split() if c.strip()]


def load_llso_final_txt(path: str | Path) -> dict[str, Any]:
    """
    Parse trajectory log. Returns dict with:
      - 'columns': list of column names
      - 'data': np.ndarray shape (n_rows, n_cols), float64 (gate_comm kept as float for simplicity)
      - 'meta': list of comment lines (without trailing newlines)
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    columns: list[str] | None = None
    meta: list[str] = []
    data_lines: list[str] = []

    for line in lines:
        if line.startswith("#"):
            meta.append(line)
            cols = _parse_columns_line(line)
            if cols:
                columns = cols
            continue
        s = line.strip()
        if not s:
            continue
        parts = s.split()
        # Legacy human-readable header row: starts with "iter" and "eval"
        if (
            len(parts) >= 2
            and parts[0].lower() == "iter"
            and parts[1].lower() == "eval"
            and columns is None
        ):
            columns = [p.strip() for p in parts]
            continue
        data_lines.append(s)

    if not data_lines:
        raise ValueError(f"No data rows in {path}")

    rows = []
    for s in data_lines:
        parts = s.split()
        if not parts:
            continue
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            # Skip summary blocks like stray tokens
            continue

    data = np.asarray(rows, dtype=np.float64)
    n = data.shape[1]

    if columns is None:
        # Legacy 13-column layout (before gate/rho/base_alpha/bsf)
        legacy13 = [
            "iter",
            "eval",
            "f_penalty",
            "f_pure",
            "penalty",
            "improvement",
            "reward",
            "conflict",
            "sum_alpha",
            "avg_alpha",
            "alpha_rank0",
            "alpha_min",
            "alpha_max",
        ]
        legacy20 = legacy13 + [
            "gate_comm",
            "base_alpha_avg",
            "rho_avg",
            "rho_r0",
            "rho_min",
            "rho_max",
            "f_pure_bsf",
        ]
        if n == len(legacy13):
            columns = legacy13
        elif n == len(legacy20):
            columns = legacy20
        else:
            columns = [f"col_{i}" for i in range(n)]
    elif len(columns) != n:
        # Column header may not match if file was hand-edited; trust width
        columns = [f"col_{i}" for i in range(n)]

    return {"columns": columns, "data": data, "meta": meta, "path": str(path.resolve())}


def column_dict(parsed: dict[str, Any]) -> dict[str, np.ndarray]:
    """Map column name -> 1d array."""
    cols: list[str] = parsed["columns"]
    data: np.ndarray = parsed["data"]
    return {cols[i]: data[:, i] for i in range(len(cols))}
