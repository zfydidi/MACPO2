"""Build F1--F6 LLSO communication-rate and evaluation-count companion table for the paper."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from utils.conference_comm_table import load_comm_json
from utils.ndo_run_stats import FUNCS_F1_F6, final_eva_from_trajectory, summarize_runs

_REPO = Path(__file__).resolve().parents[1]
MACPO_LLSO = _REPO / "MACPO_original_output" / "LLSO_25runs"
RL_LLSO = (
    _REPO
    / "ablation_experiments"
    / "Exp4_Variable_Selection"
    / "MACPO2_WithSelection_0.9_0.7_0.5"
    / "output"
)


def _load_eva_series(directory: Path, func: str, pattern: str) -> np.ndarray:
    tag = func.upper()
    vals: list[int] = []
    for i in range(1, 26):
        if pattern == "run":
            p = directory / f"{tag}_LLSO_run{i:02d}.txt"
        else:
            p = directory / f"{tag}_LLSO_run{i:02d}.txt"
            if not p.is_file():
                p = directory / f"{tag}_exp{i:02d}.txt"
        if not p.is_file():
            raise FileNotFoundError(f"Missing trajectory for eva count: {p}")
        vals.append(final_eva_from_trajectory(p))
    return np.asarray(vals, dtype=np.float64)


def load_f1f6_comm_eva_stats(
    comm_json: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    comm = load_comm_json(comm_json)
    out: dict[str, dict[str, Any]] = {}
    for fn in FUNCS_F1_F6:
        macpo_eva = summarize_runs(_load_eva_series(MACPO_LLSO, fn, "run"))
        rl_eva = summarize_runs(_load_eva_series(RL_LLSO, fn, "exp"))
        row = comm.get(fn, {})
        out[fn] = {
            "macpo_comm_rate": float(row.get("macpo_comm_rate", 1.0)),
            "rl_comm_rate_mean": float(row.get("rl_comm_rate_mean", 0.0)),
            "rl_comm_rate_std": float(row.get("rl_comm_rate_std", 0.0) or 0.0),
            "comm_reduction_pct": float(row.get("comm_reduction_pct", 0.0)),
            "macpo_eva_mean": macpo_eva["mean"],
            "macpo_eva_std": macpo_eva["std"],
            "rl_eva_mean": rl_eva["mean"],
            "rl_eva_std": rl_eva["std"],
        }
    return out


def _fmt_comm(rate: float, std: float | None = None) -> str:
    if std and std > 0:
        return f"{rate * 100:.1f}{{\\scriptsize $\\pm${std * 100:.1f}}}"
    return f"{rate * 100:.1f}"


def _fmt_eva(mean: float, std: float) -> str:
    mean_i = int(round(mean))
    if std > 0:
        return f"{mean_i}{{\\scriptsize $\\pm${int(round(std))}}}"
    return str(mean_i)


def build_f1f6_comm_eva_table_tex(stats: dict[str, dict[str, Any]] | None = None) -> str:
    stats = stats or load_f1f6_comm_eva_stats()
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\caption{Communication and evaluation budget on F1--F6 (LLSO, 25 runs): MACPO vs.\ "
        r"RL-MACPO (\emph{Full} with variable selection). Comm.\ rate: fraction of outer loops "
        r"entering negotiation. Eva.\ count: cumulative black-box evaluations at run end "
        r"(mean $\pm$ sample std). MACPO negotiates every round ($100\%$).}",
        r"\label{tab:f1f6_comm_eva}",
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"\textbf{Func.} & \textbf{MACPO comm.} & \textbf{RL comm.} & \textbf{Comm.\ drop} & "
        r"\textbf{MACPO eva.} & \textbf{RL eva.} & \textbf{$\Delta$ eva.} \\",
        r"\midrule",
    ]
    for fn in FUNCS_F1_F6:
        r = stats[fn]
        drop = float(r["comm_reduction_pct"])
        m_eva = float(r["macpo_eva_mean"])
        rl_eva = float(r["rl_eva_mean"])
        delta_pct = (rl_eva - m_eva) / m_eva * 100.0 if m_eva else 0.0
        rl_comm = _fmt_comm(float(r["rl_comm_rate_mean"]), float(r.get("rl_comm_rate_std") or 0))
        rl_comm = f"\\textbf{{{rl_comm}\\%}}" if float(r["rl_comm_rate_mean"]) < 1.0 else f"{rl_comm}\\%"
        lines.append(
            f"{fn} & 100.0\\% & {rl_comm} & {drop:.1f}\\% & "
            f"{_fmt_eva(m_eva, float(r['macpo_eva_std']))} & "
            f"{_fmt_eva(rl_eva, float(r['rl_eva_std']))} & "
            f"{delta_pct:+.1f}\\% \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def export_f1f6_comm_eva_json(out_path: Path | str | None = None) -> Path:
    stats = load_f1f6_comm_eva_stats()
    p = Path(out_path or _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "f1f6_comm_eva.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return p
