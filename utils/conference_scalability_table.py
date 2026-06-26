"""Build scalability table from archived comm-rate + fitness logs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.ndo_run_stats import fmt_sci_tex

_REPO = Path(__file__).resolve().parents[1]
COMM_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_rate_f1_f18.json"
F1F6_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f1_f6_recomputed.json"
F7F18_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f7_f18_recomputed.json"
SCALE_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "scalability_chain.json"

# MACPO benchmark chain-scale tiers (+ optional synthetic S50/S100 after codegen runs).
DEFAULT_TIERS: tuple[tuple[str, int, str, int], ...] = (
    ("F1", 20, 905, 20),
    ("F7", 40, 3400, 40),
    ("F13", 60, 10200, 60),
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}\\%"


def build_scalability_table_tex(
    comm: dict | None = None,
    f1f6: dict | None = None,
    f7f18: dict | None = None,
    scale_pilot: list | None = None,
) -> str:
    comm = comm or _load(COMM_JSON)
    f1f6 = f1f6 or _load(F1F6_JSON)
    f7f18 = f7f18 or _load(F7F18_JSON)
    scale_pilot = scale_pilot or (_load(SCALE_JSON) if SCALE_JSON.is_file() else [])

    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Scalability across MACPO chain-scale tiers (LLSO, 25 runs unless noted). "
        r"Agents / dimension follow the original MACPO benchmark \cite{ref_macpo}. "
        r"RL-MACPO (\emph{Full}) communication rate and final $F$ vs.\ always-on MACPO.}",
        r"\label{tab:scalability_chain}",
        r"\begin{tabular}{@{}lrrcccc@{}}",
        r"\toprule",
        r"\textbf{Tier} & \textbf{Agents} & \textbf{Dim.} & \textbf{MACPO comm.} & "
        r"\textbf{RL comm.} & \textbf{MACPO $F$} & \textbf{RL $F$} \\",
        r"\midrule",
    ]

    for func, agents, dim, np_ in DEFAULT_TIERS:
        c = comm.get(func, {})
        rl_comm = float(c.get("rl_comm_rate_mean", 0))
        comm_drop = float(c.get("comm_reduction_pct", 0))
        if func in f1f6.get("functions", {}):
            m = f1f6["functions"][func]["LLSO"]["MACPO"]["mean"]
            r = f1f6["functions"][func]["LLSO"]["RL-MACPO"]["mean"]
        elif func in f7f18.get("functions", {}):
            m = f7f18["functions"][func]["LLSO"]["MACPO_penalized"]["mean"]
            r = f7f18["functions"][func]["LLSO"]["RL-MACPO_f_pure"]["mean"]
        else:
            m, r = None, None
        m_cell = fmt_sci_tex(float(m)) if m is not None else "---"
        r_cell = fmt_sci_tex(float(r)) if r is not None else "---"
        if r is not None and m is not None and float(r) < float(m):
            r_cell = f"\\textbf{{{r_cell}}}"
        lines.append(
            f"{func} & {agents} & {dim} & 100.0\\% & {_fmt_pct(rl_comm)} "
            f"($-${comm_drop:.0f}\\%) & {m_cell} & {r_cell} \\\\"
        )

    if scale_pilot:
        lines.append(r"\midrule")
        lines.append(
            r"\multicolumn{7}{l}{\textit{Additional pilots (F1S50/F1S100): see "
            r"\texttt{scalability\_chain.json} after \texttt{run\_scalability\_experiments.py}}} \\"
        )

    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)
