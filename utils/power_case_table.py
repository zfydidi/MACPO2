"""Load paired MACPO vs RL-MACPO summaries for IEEE power-grid dispatch cases."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from utils.ndo_run_stats import fmt_sci_tex

_REPO = Path(__file__).resolve().parents[1]
_POWER_OUT = _REPO / "power_dispatch_sim" / "output"

IEEE_SCENARIOS: tuple[tuple[str, str], ...] = (
    ("IEEE30", "IEEE 30-bus regional power dispatch"),
    ("IEEE57", "IEEE 57-bus regional power dispatch"),
    ("IEEE118", "IEEE 118-bus regional power dispatch"),
)


def _fmt_comm(rate: float) -> str:
    return f"{rate * 100:.1f}\\%"


def _fmt_pct(x: float) -> str:
    if abs(x) < 0.05:
        return f"{x:.2f}"
    return f"{x:.1f}"


def _use_scientific(mean: float) -> bool:
    return abs(mean) >= 1000 or (0 < abs(mean) < 0.01)


def _fmt_mean_std(mean: float, std: float) -> str:
    if std <= 0 or not np.isfinite(std):
        return fmt_sci_tex(mean) if _use_scientific(mean) else f"{mean:.4f}".rstrip("0").rstrip(".")
    if _use_scientific(mean):
        return f"{fmt_sci_tex(mean)}{{\\scriptsize $\\pm${fmt_sci_tex(std)}}}"
    return f"{mean:.4f}".rstrip("0").rstrip(".") + f"{{\\scriptsize $\\pm${std:.3f}}}"


def _latest_summary(case: str) -> Path | None:
    prefix = f"power_{case}_"
    candidates = sorted(
        (p for p in _POWER_OUT.iterdir() if p.is_dir() and p.name.startswith(prefix)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for d in candidates:
        s = d / "summary.json"
        if s.is_file():
            return s
    return None


def _stats_from_rows(rows: list[dict[str, Any]], algo: str, field: str) -> dict[str, float]:
    vals = [float(r[field]) for r in rows if r.get("algorithm") == algo and field in r]
    if not vals:
        return {}
    arr = np.asarray(vals, dtype=np.float64)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0),
        "n": float(len(arr)),
    }


def load_ieee_power_data(manifest: Path | str | None = None) -> dict[str, Any]:
    manifest_path = Path(manifest or _REPO / "patent_supplement" / "ieee_power_data.json")
    pinned: dict[str, str] = {}
    if manifest_path.is_file():
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pinned = {k: v["source"] for k, v in raw_manifest.items() if isinstance(v, dict) and "source" in v}

    out: dict[str, Any] = {}
    for key, _ in IEEE_SCENARIOS:
        src = None
        if key in pinned:
            candidate = _REPO / pinned[key]
            if candidate.is_file():
                src = candidate
        if src is None:
            src = _latest_summary(key)
        if src is None:
            continue
        raw = json.loads(src.read_text(encoding="utf-8"))
        rows = raw.get("rows", [])
        m_best = _stats_from_rows(rows, "MACPO", "best_f_pure")
        r_best = _stats_from_rows(rows, "RL-MACPO", "best_f_pure")
        if not m_best or not r_best:
            continue
        macpo_comm = float(raw["MACPO"]["comm_rate_mean"])
        rl_comm = float(raw["RL-MACPO"]["comm_rate_mean"])
        comm_drop = (macpo_comm - rl_comm) / macpo_comm * 100.0 if macpo_comm else 0.0
        imp = (m_best["mean"] - r_best["mean"]) / m_best["mean"] * 100.0 if m_best["mean"] else 0.0
        out[key] = {
            "runs": int(raw.get("runs", m_best["n"])),
            "macpo_comm_rate": macpo_comm,
            "rl_comm_rate": rl_comm,
            "comm_reduction_pct": comm_drop,
            "macpo_best_f_pure": m_best["mean"],
            "macpo_best_f_pure_std": m_best["std"],
            "rl_best_f_pure": r_best["mean"],
            "rl_best_f_pure_std": r_best["std"],
            "best_f_pure_improvement_pct": imp,
            "macpo_eva": float(raw["MACPO"]["eva_count_mean"]),
            "rl_eva": float(raw["RL-MACPO"]["eva_count_mean"]),
            "source": str(src.relative_to(_REPO)),
        }
    return out


def build_ieee_power_table_tex(data: dict[str, Any] | None = None) -> str:
    data = data or load_ieee_power_data()
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\caption{Paired IEEE transmission-network dispatch (10 runs per case): MACPO vs.\ "
        r"RL-MACPO under \texttt{power\_dispatch\_sim/run\_power.sh}. "
        r"$f_{\mathrm{pure}}$: mean $\pm$ sample std of per-run best pure cost; lower is better. "
        r"Both methods share the same evaluation-budget cap and paired seeds.}",
        r"\label{tab:ieee_power_cases}",
        r"\begin{tabular}{@{}lcccccc@{}}",
        r"\toprule",
        r"\textbf{Case} & \textbf{Runs} & \textbf{MACPO comm.} & \textbf{RL comm.} & "
        r"\textbf{MACPO $f_{\mathrm{pure}}$} & \textbf{RL $f_{\mathrm{pure}}$} & \textbf{$\Delta$ / comm.\ drop} \\",
        r"\midrule",
    ]
    for key, label in IEEE_SCENARIOS:
        if key not in data:
            continue
        row = data[key]
        imp = float(row["best_f_pure_improvement_pct"])
        comm_drop = float(row["comm_reduction_pct"])
        m_fp = float(row["macpo_best_f_pure"])
        r_fp = float(row["rl_best_f_pure"])
        m_cell = _fmt_mean_std(m_fp, float(row["macpo_best_f_pure_std"]))
        r_cell = _fmt_mean_std(r_fp, float(row["rl_best_f_pure_std"]))
        tied = abs(m_fp - r_fp) / max(abs(m_fp), 1e-12) < 0.005
        if tied:
            m_cell = f"{m_cell}{{\\scriptsize $\\approx$}}"
            r_cell = f"{r_cell}{{\\scriptsize $\\approx$}}"
        rl_better = (not tied) and r_fp < m_fp and (m_fp - r_fp) / max(abs(m_fp), 1e-12) >= 0.005
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
