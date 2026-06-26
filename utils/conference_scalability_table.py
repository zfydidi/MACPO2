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
        r"\caption{Scalability across MACPO chain-scale tiers (LLSO). "
        r"F1/F7/F13 and F1S50/F1S100: 5-run pilots. "
        r"RL-MACPO (\emph{Full}) communication rate and final $F$ vs.\ always-on MACPO.}",
        r"\label{tab:scalability_chain}",
        r"\begin{tabular}{@{}lrrcccc@{}}",
        r"\toprule",
        r"\textbf{Tier} & \textbf{Agents} & \textbf{Dim.} & \textbf{MACPO comm.} & "
        r"\textbf{RL comm.} & \textbf{MACPO $F$} & \textbf{RL $F$} \\",
        r"\midrule",
    ]

    scale_idx: dict[str, dict[str, dict]] = {}
    for row in scale_pilot:
        scale_idx.setdefault(row.get("benchmark", ""), {})[row.get("method", "")] = row

    for func, agents, dim, np_ in DEFAULT_TIERS:
        pilot_macpo = scale_idx.get(func, {}).get("MACPO", {})
        pilot_rl = scale_idx.get(func, {}).get("RL-MACPO", {})
        use_pilot = pilot_macpo.get("runs", 0) > 0 and pilot_rl.get("runs", 0) > 0

        if use_pilot:
            rl_comm = float(pilot_rl.get("comm_rate_mean", 0))
            comm_drop = (1.0 - rl_comm) * 100.0
            m = pilot_macpo.get("fitness_mean")
            r = pilot_rl.get("fitness_mean")
            run_note = f" ({int(pilot_macpo.get('runs', 0))}r)"
        else:
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
            run_note = ""

        m_cell = fmt_sci_tex(float(m)) if m is not None else "---"
        r_cell = fmt_sci_tex(float(r)) if r is not None else "---"
        if r is not None and m is not None and float(r) < float(m):
            r_cell = f"\\textbf{{{r_cell}}}"
        lines.append(
            f"{func}{run_note} & {agents} & {dim} & 100.0\\% & {_fmt_pct(rl_comm)} "
            f"($-${comm_drop:.0f}\\%) & {m_cell} & {r_cell} \\\\"
        )

    if scale_pilot:
        lines.append(r"\midrule")
        lines.append(
            r"\multicolumn{7}{l}{\textit{Additional chain-scale pilots (5 runs, LLSO):}} \\"
        )
        pilot_dims = {"F1S50": 2550, "F1S100": 5100}
        by_bench: dict[str, dict[str, dict]] = {}
        for row in scale_pilot:
            name = row.get("benchmark", "")
            if name not in pilot_dims:
                continue
            by_bench.setdefault(name, {})[row.get("method", "")] = row
        for name in ("F1S50", "F1S100"):
            pair = by_bench.get(name, {})
            macpo = pair.get("MACPO", {})
            rl = pair.get("RL-MACPO", {})
            agents = macpo.get("agents") or rl.get("agents") or "---"
            dim = pilot_dims[name]
            m_comm = _fmt_pct(1.0) if macpo.get("runs") else "---"
            r_comm = (
                _fmt_pct(float(rl["comm_rate_mean"]))
                if rl.get("comm_rate_mean") is not None
                else "---"
            )
            m_fit = (
                fmt_sci_tex(float(macpo["fitness_mean"]))
                if macpo.get("fitness_mean") is not None
                else "---"
            )
            r_fit = "---"
            if rl.get("fitness_mean") is not None:
                r_fit = fmt_sci_tex(float(rl["fitness_mean"]))
                if rl.get("fitness_std") and float(rl["fitness_std"]) > 0:
                    r_fit += (
                        f"{{\\scriptsize $\\pm${fmt_sci_tex(float(rl['fitness_std']))}}}"
                    )
            label = name
            if rl.get("runs", 0) == 0:
                label += "$^{*}$"
            lines.append(
                f"{label} & {agents} & {dim} & {m_comm} & {r_comm} & {m_fit} & {r_fit} \\\\"
            )

    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)
