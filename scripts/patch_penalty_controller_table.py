#!/usr/bin/env python3
"""Patch Table penalty_controller_f3_f5 rows from media/penalty_controller_f3_f5.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
JSON_PATH = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "penalty_controller_f3_f5.json"

CONTROLLERS = [
    ("MACPO", "MACPO (static)"),
    ("FixedSchedule", "Fixed schedule"),
    ("EMA_Penalty", "EMA penalty"),
    ("RL", "RL (\\emph{Full})"),
]


def _sci(mean: float, std: float) -> str:
    import math

    def _one(x: float) -> str:
        if x == 0:
            return "0"
        exp = int(math.floor(math.log10(abs(x))))
        mant = x / (10**exp)
        return f"{mant:.2f}E{exp:+d}"

    return f"{_one(mean)}{{\\scriptsize $\\pm${_one(std)}}}"


def _best_gated_keys(by_ctrl: dict, func: str) -> set[str]:
    keys = ["FixedSchedule", "EMA_Penalty", "RL"]
    means = []
    for k in keys:
        rec = by_ctrl.get((func, k))
        if rec and rec["fitness"]["mean"] is not None:
            means.append((rec["fitness"]["mean"], k))
    if not means:
        return set()
    best = min(m for m, _ in means)
    return {k for m, k in means if abs(m - best) <= 1e-9 * max(best, 1.0)}


def _pct(rate: float | None) -> str:
    if rate is None:
        return "---"
    return f"{100.0 * rate:.1f}\\%"


def _row_cells(func: str, by_ctrl: dict) -> str:
    parts: list[str] = []
    for key, _label in CONTROLLERS:
        rec = by_ctrl.get((func, key))
        if not rec or rec["fitness"]["mean"] is None:
            parts.extend(["\\textit{pending}", "---", "---"])
            continue
        m = rec["fitness"]["mean"]
        s = rec["fitness"]["std"] or 0.0
        n = int(rec["fitness"]["n"])
        comm = rec["comm_rate"]["mean"]
        parts.append(_sci(m, s))
        parts.append(_pct(comm))
        parts.append(str(n))
    return " & ".join(parts)


def main() -> None:
    if not JSON_PATH.is_file():
        raise SystemExit(f"Missing {JSON_PATH}; run scripts/run_penalty_controller_f3_f5.sh first.")
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    by_ctrl: dict[tuple[str, str], dict] = {}
    for row in payload["rows"]:
        by_ctrl[(row["function"], row["controller"])] = row

    lines: list[str] = []
    best_f3 = _best_gated_keys(by_ctrl, "F3")
    best_f5 = _best_gated_keys(by_ctrl, "F5")
    for key, label in CONTROLLERS:
        f3 = by_ctrl.get(("F3", key))
        f5 = by_ctrl.get(("F5", key))
        cells_f3: list[str] = []
        cells_f5: list[str] = []
        for func, rec, best_set, cells in (
            ("F3", f3, best_f3, cells_f3),
            ("F5", f5, best_f5, cells_f5),
        ):
            if not rec or rec["fitness"]["mean"] is None:
                cells.extend(["\\textit{pending}", "---", "---"])
            else:
                m = rec["fitness"]["mean"]
                s = rec["fitness"]["std"] or 0.0
                n = int(rec["fitness"]["n"])
                comm = rec["comm_rate"]["mean"]
                val = _sci(m, s)
                if key in best_set:
                    val = f"\\textbf{{{val}}}"
                cells.extend([val, _pct(comm), str(n)])
        line = f"{label} & {' & '.join(cells_f3)} & {' & '.join(cells_f5)} \\\\"
        lines.append(line)

    body = "\\midrule\n" + "\n".join(lines) + "\n\\bottomrule"
    tex = TEX.read_text(encoding="utf-8")
    marker = "\\midrule\nMACPO (static)"
    start = tex.index(marker)
    end = tex.index("\\bottomrule", start)
    new_tex = tex[:start] + body + tex[end + len("\\bottomrule") :]
    TEX.write_text(new_tex, encoding="utf-8")
    print(f"Patched {TEX}")


if __name__ == "__main__":
    main()
