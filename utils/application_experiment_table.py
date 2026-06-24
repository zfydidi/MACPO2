"""
Build LaTeX fragments for application-case experiments (MAED13, RESOURCE, EVDISPATCH).

Data source: patent_supplement/paired_experiment_data.json (paired MACPO vs RL-MACPO).
Per-run std is computed from the summary JSON paths referenced in that file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from utils.ndo_run_stats import fmt_sci_tex

# Paper-facing scenario order and labels (MAED2 excluded).
APPLICATION_SCENARIOS: tuple[tuple[str, str], ...] = (
    ("MAED13", "Multi-area economic dispatch (13 generators, 1800\\,MW)"),
    ("RESOURCE", "Resource-constrained distributed scheduling"),
    ("EVDISPATCH", "Electric-vehicle charging/discharging coordination"),
)


def load_application_data(json_path: Path | str | None = None) -> dict[str, Any]:
    path = Path(json_path or Path(__file__).resolve().parents[1] / "patent_supplement/paired_experiment_data.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for key, _ in APPLICATION_SCENARIOS:
        if key not in raw:
            continue
        row = dict(raw[key])
        stats = _stats_from_summary(row.get("source"))
        if stats:
            row.update(stats)
        out[key] = row
    return out


def _stats_from_summary(source: str | None) -> dict[str, float] | None:
    if not source:
        return None
    repo = Path(__file__).resolve().parents[1]
    p = repo / source
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for algo in ("MACPO", "RL-MACPO"):
        vals = [
            float(r["best_f_pure"])
            for r in data.get("rows", [])
            if r.get("algorithm") == algo and "best_f_pure" in r
        ]
        if not vals:
            continue
        arr = np.asarray(vals, dtype=np.float64)
        out[f"macpo_best_f_pure_std" if algo == "MACPO" else "rl_best_f_pure_std"] = float(
            np.std(arr, ddof=1) if len(arr) > 1 else 0.0
        )
    return out or None


def _fmt_sci_mant(x: float, mant_decimals: int) -> str:
    if x == 0 or not np.isfinite(x):
        return "0"
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10**exp)
    sign = "+" if exp >= 0 else ""
    return f"{mant:.{mant_decimals}f}E{sign}{exp}"


def _error_sig_digits(err: float) -> int:
    """1 sig digit for error; 2 when the leading digit is 1 or 2."""
    if err <= 0 or not np.isfinite(err):
        return 1
    exp = int(np.floor(np.log10(abs(err))))
    lead = int(round(err / (10**exp)))
    if lead >= 10:
        lead = 1
    return 2 if lead in (1, 2) else 1


def _round_to_sigfig(x: float, sig: int) -> float:
    if x == 0 or not np.isfinite(x):
        return 0.0
    exp = int(np.floor(np.log10(abs(x))))
    scale = 10 ** (exp - sig + 1)
    return round(x / scale) * scale


def _fmt_error_sci(err: float) -> str:
    rounded = _round_to_sigfig(err, _error_sig_digits(err))
    return _fmt_sci_mant(rounded, 1)


def _fmt_error_decimal(err: float) -> str:
    if 0 < abs(err) < 0.1:
        # Match mean display scale (e.g. -3.0767 ± 0.037).
        return f"{err:.3f}".rstrip("0").rstrip(".")
    rounded = _round_to_sigfig(err, _error_sig_digits(err))
    if rounded >= 1:
        decimals = max(0, -int(np.floor(np.log10(abs(rounded)))) + (_error_sig_digits(err) - 1))
    else:
        decimals = max(0, -int(np.floor(np.log10(abs(rounded)))) + (_error_sig_digits(err) - 1))
    s = f"{rounded:.{decimals}f}"
    return s.rstrip("0").rstrip(".")


def _use_scientific(mean: float) -> bool:
    return abs(mean) >= 1000 or (0 < abs(mean) < 0.01)


def _fmt_mean_std(mean: float, std: float | None, *, extended: bool = False) -> str:
    if std is None or std <= 0 or not np.isfinite(std):
        if _use_scientific(mean):
            mant_dec = 4 if extended else 2
            return _fmt_sci_mant(mean, mant_dec)
        return f"{mean:.4f}".rstrip("0").rstrip(".")

    if _use_scientific(mean):
        mant_dec = 4 if extended else 2
        mean_s = _fmt_sci_mant(mean, mant_dec)
        err_s = _fmt_error_sci(float(std))
    else:
        mean_s = f"{mean:.4f}".rstrip("0").rstrip(".")
        err_s = _fmt_error_decimal(float(std))
    return f"{mean_s}{{\\scriptsize $\\pm${err_s}}}"


def _rl_objective_better(key: str, macpo_val: float, rl_val: float) -> bool:
    # Lower f_pure is better; EV dispatch uses more-negative-as-better (still lower).
    return rl_val < macpo_val


def _means_collide_at_default_precision(macpo_val: float, rl_val: float) -> bool:
    if _use_scientific(macpo_val):
        return fmt_sci_tex(macpo_val) == fmt_sci_tex(rl_val)
    m = f"{macpo_val:.4f}".rstrip("0").rstrip(".")
    r = f"{rl_val:.4f}".rstrip("0").rstrip(".")
    return m == r


def _fmt_pct(x: float) -> str:
    if abs(x) < 0.05:
        return f"{x:.2f}"
    return f"{x:.1f}"


def _fmt_comm(rate: float) -> str:
    return f"{rate * 100:.1f}\\%"


def build_application_table_tex(data: dict[str, Any] | None = None) -> str:
    data = data or load_application_data()
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\caption{Paired application-case comparison (10 runs per scenario): MACPO vs.\ RL-MACPO. "
        r"Comm.\ rate is the fraction of outer loops that trigger negotiation. "
        r"$f_{\mathrm{pure}}$: mean $\pm$ sample std of per-run best pure objective over 10 runs; "
        r"lower is better except EV dispatch ($\uparrow$: more negative net benefit is better). "
        r"Both methods share the same evaluation-budget cap and paired random seeds.}",
        r"\label{tab:application_cases}",
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"\textbf{Scenario} & \textbf{Runs} & \textbf{MACPO comm.} & \textbf{RL comm.} & "
        r"\textbf{MACPO $f_{\mathrm{pure}}$} & \textbf{RL $f_{\mathrm{pure}}$} & \textbf{$\Delta$ / comm.\ drop} \\",
        r"\midrule",
    ]
    for key, label in APPLICATION_SCENARIOS:
        row = data[key]
        imp = float(row["best_f_pure_improvement_pct"])
        comm_drop = float(row["comm_reduction_pct"])
        m_fp = float(row["macpo_best_f_pure"])
        r_fp = float(row["rl_best_f_pure"])
        m_std = row.get("macpo_best_f_pure_std")
        r_std = row.get("rl_best_f_pure_std")
        extended = _means_collide_at_default_precision(m_fp, r_fp)
        m_cell = _fmt_mean_std(m_fp, float(m_std) if m_std is not None else None, extended=extended)
        r_cell = _fmt_mean_std(r_fp, float(r_std) if r_std is not None else None, extended=extended)
        rl_better = _rl_objective_better(key, m_fp, r_fp)
        if key == "EVDISPATCH":
            delta = f"{_fmt_pct(imp)}\\% $\\uparrow$; comm.\\ $-${_fmt_pct(comm_drop)}\\%"
            if rl_better:
                r_cell = f"\\textbf{{{r_cell}$^{{\\uparrow}}$}}"
        else:
            delta = f"{_fmt_pct(imp)}\\%; comm.\\ $-${_fmt_pct(comm_drop)}\\%"
            if rl_better:
                r_cell = f"\\textbf{{{r_cell}}}"
        lines.append(
            f"\\makecell[l]{{{label}}} & {int(row['runs'])} & "
            f"{_fmt_comm(float(row['macpo_comm_rate']))} & {_fmt_comm(float(row['rl_comm_rate']))} & "
            f"{m_cell} & {r_cell} & {delta} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def build_application_section_tex(data: dict[str, Any] | None = None) -> str:
    data = data or load_application_data()
    table = build_application_table_tex(data)
    maed = data["MAED13"]
    res = data["RESOURCE"]
    ev = data["EVDISPATCH"]
    results_para = (
        r"\paragraph{Results.} Table~\ref{tab:application_cases} summarizes paired means $\pm$ sample std. "
        f"On MAED-13, RL-MACPO reduces communication from 100{chr(37)} to "
        f"{float(maed['rl_comm_rate']) * 100:.1f}{chr(37)} while changing the best pure cost by only "
        f"{float(maed['best_f_pure_improvement_pct']):.2f}{chr(37)}. "
        f"On resource scheduling, the pure objective improves by "
        f"{float(res['best_f_pure_improvement_pct']):.1f}{chr(37)} with an "
        f"{float(res['comm_reduction_pct']):.1f}{chr(37)} communication reduction. "
        f"On EV dispatch, the net benefit objective improves by "
        f"{float(ev['best_f_pure_improvement_pct']):.1f}{chr(37)} ($\\uparrow$ toward more negative "
        r"$f_{\mathrm{pure}}$) with an "
        f"{float(ev['comm_reduction_pct']):.1f}{chr(37)} communication reduction. "
        r"These results complement the F1--F18 benchmark: they show that gated communication "
        r"and adaptive penalties transfer to simulation-based dispatch objectives without "
        r"sacrificing solution quality under a fixed evaluation budget."
    )
    results_para = results_para.replace(chr(37), r"\%")
    return "\n".join(
        [
            r"\subsection{Application to Networked Dispatch Cases}\label{sec:applications}",
            r"Beyond the synthetic NDO benchmark F1--F18, we evaluate RL-MACPO on three "
            r"network-structured dispatch problems that follow the MACPO application line "
            r"\cite{ref_macpo}: multi-area valve-point economic dispatch, resource-constrained "
            r"distributed scheduling, and electric-vehicle (EV) charging/discharging coordination. "
            r"These cases retain the same NDO structure---private local decisions plus shared "
            r"boundary variables on a communication graph---but use simulation-based objectives "
            r"rather than the closed-form F1--F18 elementary functions.",
            r"",
            r"\paragraph{Scenarios and protocol.} "
            r"\emph{MAED-13} is a 13-generator, multi-area economic dispatch instance at "
            f"{float(maed['macpo_eva']):.0f} function evaluations per run (10 paired repetitions). "
            r"\emph{Resource scheduling} and \emph{EV dispatch} follow the large-scale networked "
            r"scheduling templates used in the MACPO study (Appendices V--VI), with "
            f"{float(res['macpo_eva']):.0f} evaluations per run in our implementation. "
            r"In all cases, MACPO and RL-MACPO (\emph{Full}) use identical seeds, the same "
            r"evaluation-budget cap, and the same MPI partition; they differ only in adaptive "
            r"penalty control and conflict-gated communication. The reported $f_{\mathrm{pure}}$ "
            r"is the assembled global pure objective; communication rate is the fraction of "
            r"outer loops in which cross-node negotiation is triggered.",
            r"",
            results_para,
            r"",
            r"\paragraph{Reproducibility.} Logs are produced by \texttt{power\_dispatch\_sim/} "
            r"(\texttt{run\_maed.sh}, \texttt{run\_paper\_scenarios.sh}); aggregated summaries match "
            r"\texttt{patent\_supplement/paired\_experiment\_data.json}. "
            r"Standard IEEE bus benchmarks were used only for internal engineering tests and are "
            r"\emph{not} included here.",
            r"",
            table,
        ]
    )
