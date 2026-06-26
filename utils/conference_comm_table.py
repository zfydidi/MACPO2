"""Build LaTeX for F1--F18 communication-rate table (MACPO vs RL-MACPO)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.ndo_run_stats import FUNCS_F1_F6, FUNCS_F7_F18

_REPO = Path(__file__).resolve().parents[1]
_DEFAULT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_rate_f1_f18.json"


def _fmt_pct(x: float | None, std: float | None = None) -> str:
    if x is None:
        return "---"
    if std is not None and std > 0:
        return f"{x * 100:.1f}{{\\scriptsize $\\pm${std * 100:.1f}}}"
    return f"{x * 100:.1f}"


def build_comm_rate_table_tex(rows: dict[str, Any]) -> str:
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Communication trigger rate on F1--F18 (LLSO, 25 runs per function): fraction of outer loops "
        r"that enter neighbor negotiation. MACPO always negotiates ($100\%$). RL-MACPO uses conflict-gated "
        r"communication with relative threshold and fail-safe (same \emph{Full} gate as F7--F18; "
        r"F1--F6 use \texttt{Selection\_0.9\_0.7\_0.5} with the same gate defaults). "
        r"Comm.\ reduction is relative to MACPO.}",
        r"\label{tab:comm_rate_f1_f18}",
        r"\begin{tabular}{@{}lccc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{MACPO comm.} & \textbf{RL-MACPO comm.} & \textbf{Reduction} \\",
        r"\midrule",
    ]
    for fn in list(FUNCS_F1_F6) + list(FUNCS_F7_F18):
        r = rows.get(fn, {})
        m = float(r.get("macpo_comm_rate", 1.0))
        rl_m = r.get("rl_comm_rate_mean")
        rl_s = r.get("rl_comm_rate_std")
        red = r.get("comm_reduction_pct")
        red_s = f"{red:.1f}\\%" if red is not None else "---"
        rl_cell = _fmt_pct(rl_m, rl_s)
        if rl_m is not None and m > 0 and rl_m < m:
            rl_cell = f"\\textbf{{{rl_cell}}}"
        lines.append(f"{fn} & {_fmt_pct(m)} & {rl_cell} & {red_s} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def build_periodic_baseline_table_tex(rows: list[dict[str, Any]]) -> str:
    """Rows: func, method, comm_rate_mean, comm_rate_std, final_fitness_mean, final_fitness_std."""
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Conflict-gated RL-MACPO (\emph{Full}) vs.\ fixed-interval communication baselines "
        r"on F1, F2, and F5 (LLSO, 10-run pilot, separate from the 25-run main table). "
        r"\emph{Periodic-$K$}: negotiate every $K$ outer loops (RL penalty on, CI gate off). "
        r"Lower final $F$ is better. See Table~\ref{tab:comm_efficiency_f125} for joint "
        r"fitness--communication scoring; no fitness bolding here because raw fitness alone "
        r"favors higher-communication periodic rules on some functions.}",
        r"\label{tab:periodic_baseline}",
        r"\begin{tabular}{@{}llcc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{Method} & \textbf{Comm.\ rate} & \textbf{Final $F$ (mean $\pm$ std)} \\",
        r"\midrule",
    ]
    order = ["Full", "PeriodicK2", "PeriodicK3", "PeriodicK5"]
    labels = {
        "Full": "RL-MACPO (gated)",
        "PeriodicK2": "Periodic-2",
        "PeriodicK3": "Periodic-3",
        "PeriodicK5": "Periodic-5",
    }
    by_func: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_func.setdefault(r["func"], []).append(r)
    for func in ("F1", "F2", "F5"):
        group = {r["method"]: r for r in by_func.get(func, [])}
        for m in order:
            r = group.get(m)
            if not r:
                continue
            comm = _fmt_pct(r.get("comm_rate_mean"), r.get("comm_rate_std"))
            fm = r.get("final_fitness_mean")
            fs = r.get("final_fitness_std")
            if fm is None:
                f_cell = "---"
            else:
                from utils.ndo_run_stats import fmt_sci_tex

                f_cell = fmt_sci_tex(float(fm))
                if fs is not None and float(fs) > 0:
                    f_cell += f"{{\\scriptsize $\\pm${fmt_sci_tex(float(fs))}}}"
            lines.append(f"{func} & {labels.get(m, m)} & {comm} & {f_cell} \\\\")
        if func != "F5":
            lines.append(r"\midrule")
    lines.append(r"\bottomrule")
    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def load_comm_json(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path or _DEFAULT_JSON)
    return json.loads(p.read_text(encoding="utf-8"))
