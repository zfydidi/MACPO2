"""
Build LaTeX tables for communication-policy comparison (Periodic / Threshold vs RL gating).

Narrative goal: fixed-K periodic rules are problem-specific; RL gating adapts comm rate
across heterogeneous conflict patterns without per-function tuning.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.ndo_run_stats import FUNCS_F1_F6, fmt_sci_tex

_REPO = Path(__file__).resolve().parents[1]
PERIODIC_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "periodic_baseline_f125.json"
COMM_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_rate_f1_f18.json"
F1F6_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f1_f6_recomputed.json"
COMM_BASELINE_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_baselines_f1_f6.json"

# MACPO paper average theoretical CI on F1--F6.
THEORY_CI: dict[str, float] = {
    "F1": 0.228,
    "F2": 0.049,
    "F3": 0.846,
    "F4": 0.051,
    "F5": 0.497,
    "F6": 0.268,
}
CONFLICT_CLASS: dict[str, str] = {
    "F1": "mid",
    "F2": "low",
    "F3": "high",
    "F4": "low",
    "F5": "high",
    "F6": "mid",
}

PERIODIC_METHODS = ("PeriodicK2", "PeriodicK3", "PeriodicK5")
PERIODIC_LABEL = {"PeriodicK2": "P-2", "PeriodicK3": "P-3", "PeriodicK5": "P-5"}


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _index_periodic(rows: list[dict]) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for r in rows:
        out.setdefault(r["func"], {})[r["method"]] = r
    return out


def _index_comm_baseline(rows: list[dict]) -> dict[str, dict[str, dict]]:
    return _index_periodic(rows)


def _best_periodic(per_func: dict[str, dict]) -> tuple[str | None, dict | None]:
    best_m, best_r = None, None
    for m in PERIODIC_METHODS:
        r = per_func.get(m)
        if not r or r.get("final_fitness_mean") is None:
            continue
        v = float(r["final_fitness_mean"])
        if best_r is None or v < float(best_r["final_fitness_mean"]):
            best_m, best_r = m, r
    return best_m, best_r


def _fmt_pct(x: float | None) -> str:
    if x is None:
        return "---"
    return f"{x * 100:.1f}\\%"


def _fitness_cell(mean: float | None, std: float | None = None) -> str:
    if mean is None:
        return "---"
    s = fmt_sci_tex(float(mean))
    if std is not None and float(std) > 0:
        s += f"{{\\scriptsize $\\pm${fmt_sci_tex(float(std))}}}"
    return s


def build_adaptation_table_tex(
    periodic_rows: list[dict] | None = None,
    comm_rows: dict | None = None,
    f1f6: dict | None = None,
) -> str:
    periodic_rows = periodic_rows or _load_json(PERIODIC_JSON) or []
    comm_rows = comm_rows or _load_json(COMM_JSON) or {}
    f1f6 = f1f6 or _load_json(F1F6_JSON) or {}
    per_idx = _index_periodic(periodic_rows)

    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\caption{Conflict-heterogeneous communication adaptation on F1--F6 (LLSO). "
        r"Theory CI: MACPO \cite{ref_macpo}. RL comm.: 25-run gated \emph{Full}. "
        r"Best fixed-$K$: lowest-mean fitness among Periodic-2/3/5 on the 10-run pilot "
        r"(F1/F2/F5 only). RL fitness: 25-run \emph{Full} main table. "
        r"No single $K$ is optimal across functions; RL comm.\ rate shifts with conflict class "
        r"without manual per-function tuning.}",
        r"\label{tab:comm_policy_adaptation}",
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{Conflict} & \textbf{Theory CI} & \textbf{RL comm.} & "
        r"\textbf{Best fixed-$K$} & \textbf{$K$ comm.} & \textbf{RL fitness (25r)} \\",
        r"\midrule",
    ]

    best_k_counts: dict[str, int] = {}
    for fn in FUNCS_F1_F6:
        rl_comm = comm_rows.get(fn, {}).get("rl_comm_rate_mean")
        rl_fit = None
        if fn in f1f6.get("functions", {}):
            rl_fit = f1f6["functions"][fn]["LLSO"]["RL-MACPO"]["mean"]
        pilot = per_idx.get(fn, {})
        best_m, best_r = _best_periodic(pilot)
        if best_m:
            best_k_counts[best_m] = best_k_counts.get(best_m, 0) + 1
        k_comm = best_r.get("comm_rate_mean") if best_r else None
        lines.append(
            f"{fn} & {CONFLICT_CLASS[fn]} & {THEORY_CI[fn]:.3f} & {_fmt_pct(rl_comm)} & "
            f"{PERIODIC_LABEL.get(best_m or '', '---')} & {_fmt_pct(k_comm)} & "
            f"{_fitness_cell(rl_fit)} \\\\"
        )

    lines.extend(
        [
            r"\midrule",
            r"\multicolumn{7}{l}{\textit{Pilot best-$K$ winners on F1/F2/F5:} "
            + ", ".join(f"{PERIODIC_LABEL[k]} ({v})" for k, v in sorted(best_k_counts.items()))
            + r"} \\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines)


def build_comm_efficiency_table_tex(
    periodic_rows: list[dict] | None = None,
    f1f6: dict | None = None,
) -> str:
    """Fitness per unit communication (lower fitness is better; lower comm is better)."""
    periodic_rows = periodic_rows or _load_json(PERIODIC_JSON) or []
    f1f6 = f1f6 or _load_json(F1F6_JSON) or {}
    per_idx = _index_periodic(periodic_rows)
    comm_main = _load_json(COMM_JSON) or {}
    methods = ("Full",) + PERIODIC_METHODS
    labels = {"Full": "RL gated", **{k: PERIODIC_LABEL[k] for k in PERIODIC_METHODS}}

    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Communication--fitness joint efficiency on F1/F2/F5. "
        r"RL gated uses 25-run fitness from Table~\ref{tab:macpo_style_all} and comm.\ "
        r"from Table~\ref{tab:f1f6_comm_eva}; periodic rules use the 10-run pilot. "
        r"Score $= \log_{10}(F) + 2\log_{10}(\mathrm{comm.\ rate})$ (lower is better). "
        r"Bold: best score per function.}",
        r"\label{tab:comm_efficiency_f125}",
        r"\begin{tabular}{@{}lcccc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{Method} & \textbf{Comm.} & \textbf{Final $F$} & \textbf{Joint score} \\",
        r"\midrule",
    ]

    import math

    for fn in ("F1", "F2", "F5"):
        group = per_idx.get(fn, {})
        scores: list[tuple[str, float]] = []
        row_cells: list[str] = []

        for m in methods:
            if m == "Full":
                comm = comm_main.get(fn, {}).get("rl_comm_rate_mean")
                fit = None
                fs = None
                if fn in f1f6.get("functions", {}):
                    fit = f1f6["functions"][fn]["LLSO"]["RL-MACPO"]["mean"]
                    fs = f1f6["functions"][fn]["LLSO"]["RL-MACPO"]["std"]
            else:
                r = group.get(m)
                if not r:
                    continue
                comm = r.get("comm_rate_mean")
                fit = r.get("final_fitness_mean")
                fs = r.get("final_fitness_std")
            if comm is None or fit is None or float(comm) <= 0 or float(fit) <= 0:
                continue
            score = math.log10(float(fit)) + 2.0 * math.log10(float(comm))
            scores.append((m, score))
            f_cell = _fitness_cell(float(fit), float(fs) if fs else None)
            row_cells.append((m, comm, f_cell, score))

        best_score = min(s[1] for s in scores) if scores else None
        for m, comm, f_cell, score in row_cells:
            sc_cell = f"{score:.2f}"
            if best_score is not None and abs(score - best_score) < 1e-9:
                sc_cell = f"\\textbf{{{sc_cell}}}"
            lines.append(
                f"{fn} & {labels[m]} & {_fmt_pct(float(comm))} & {f_cell} & {sc_cell} \\\\"
            )
        if fn != "F5":
            lines.append(r"\midrule")

    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def build_threshold_baseline_table_tex(rows: list[dict] | None = None) -> str:
    rows = rows or _load_json(COMM_BASELINE_JSON)
    if not rows:
        return (
            r"% Threshold baseline table pending: run scripts/run_comm_baselines.py "
            r"--methods FixedThreshold,FixedThresholdNoFailSafe,RelativeThresholdFailSafe"
        )
    idx = _index_comm_baseline(rows)
    methods = ("Full", "FixedThreshold", "FixedThresholdNoFailSafe", "RelativeThresholdFailSafe")
    labels = {
        "Full": "RL gated (Full)",
        "FixedThreshold": "Fixed threshold",
        "FixedThresholdNoFailSafe": "Fixed thresh.\ (no fail-safe)",
        "RelativeThresholdFailSafe": "Relative + fail-safe",
    }
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\caption{Event-triggered / threshold communication baselines on F1--F6 (LLSO pilot). "
        r"Fixed absolute thresholds without fail-safe can collapse communication; "
        r"relative threshold + fail-safe matches the production gate.}",
        r"\label{tab:threshold_baseline}",
        r"\begin{tabular}{@{}lccccc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{Method} & \textbf{Comm.} & \textbf{Final $F$} \\",
        r"\midrule",
    ]
    for fn in FUNCS_F1_F6:
        group = idx.get(fn, {})
        first = True
        for m in methods:
            r = group.get(m)
            if not r:
                continue
            prefix = fn if first else ""
            first = False
            lines.append(
                f"{prefix} & {labels[m]} & {_fmt_pct(r.get('comm_rate_mean'))} & "
                f"{_fitness_cell(r.get('final_fitness_mean'), r.get('final_fitness_std'))} \\\\"
            )
        if not first:
            lines.append(r"\midrule")
    if lines and lines[-1] == r"\midrule":
        lines[-1] = r"\bottomrule"
    else:
        lines.append(r"\bottomrule")
    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)
