#!/usr/bin/env python3
"""Patch Q4 tables in conference_new_ready.tex from 25-run dispatch summaries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

_REPO = Path(__file__).resolve().parents[1]
TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_new_ready.tex"

IEEE_SOURCES = {
    "30": _REPO / "power_dispatch_sim/output/power_IEEE30_20260630_114805/summary.json",
    "57": _REPO / "power_dispatch_sim/output/power_IEEE57_20260630_114810/summary.json",
    "118": _REPO / "power_dispatch_sim/output/power_IEEE118_20260701_175246/summary.json",
}

APP_SOURCES = {
    "MAED": _REPO / "power_dispatch_sim/output/maed_20260701_175417/MAED13/summary.json",
    "RESOURCE": _REPO / "power_dispatch_sim/output/paper_20260701_175627/RESOURCE/summary.json",
    "EV": _REPO / "power_dispatch_sim/output/paper_20260701_175627/EVDISPATCH/summary.json",
}


def _sci(x: float, sig: int = 2) -> str:
    if x == 0:
        return "0"
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10**exp)
    return f"{mant:.{sig}f}E{'+' if exp >= 0 else ''}{exp}"


def _sci_pm(mean: float, std: float) -> str:
    return f"{_sci(mean)}{{ \\scriptsize $\\pm${_sci(std)} }}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}\\%"


def _app_row(label: str, summary_path: Path, *, ev: bool = False) -> str:
    j = json.loads(summary_path.read_text(encoding="utf-8"))
    r = j["RL-MACPO"]
    mb = [x["best_f_pure"] for x in j["rows"] if x.get("algorithm") == "MACPO"]
    rb = [x["best_f_pure"] for x in j["rows"] if x.get("algorithm") == "RL-MACPO"]
    m_mean, m_std = float(np.mean(mb)), float(np.std(mb, ddof=1))
    r_mean, r_std = float(np.mean(rb)), float(np.std(rb, ddof=1))
    imp = float(j.get("best_f_pure_improvement_pct", 0.0))
    comm_drop = float(j.get("comm_reduction_pct", 0.0))
    if ev:
        m_cell = f"{m_mean:.4f}{{ \\scriptsize $\\pm${m_std:.3f} }}"
        r_cell = f"\\textbf{{{r_mean:.4f}{{ \\scriptsize $\\pm${r_std:.3f} }}}}"
        delta = f"{imp:.1f}\\%; comm.\\ $-${comm_drop:.1f}\\%"
    else:
        m_cell = _sci_pm(m_mean, m_std)
        r_cell = _sci_pm(r_mean, r_std)
        if r_mean < m_mean:
            r_cell = f"\\textbf{{{r_cell}}}"
        delta = f"{imp:.2f}\\%; comm.\\ $-${comm_drop:.1f}\\%"
    return (
        f"\\makecell[l]{{{label}}} & {_pct(r['comm_rate_mean'])} & {m_cell} & {r_cell} & {delta} \\\\"
    )


def _ieee_row(label: str, summary_path: Path) -> str:
    j = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = j["rows"]
    m_best = np.array([x["best_f_pure"] for x in rows if x.get("algorithm") == "MACPO"])
    r_best = np.array([x["best_f_pure"] for x in rows if x.get("algorithm") == "RL-MACPO"])
    paired = (m_best - r_best) / np.abs(m_best) * 100.0
    succ = sum(1 for a, b in zip(m_best, r_best) if b <= 2.0 * abs(a))
    _, wp = stats.wilcoxon(r_best - m_best, zero_method="wilcox", alternative="two-sided")
    rl_comm = float(j["RL-MACPO"]["comm_rate_mean"])
    comm_drop = (1.0 - rl_comm) * 100.0
    med = float(np.median(paired))
    mean_d = float(np.mean(paired))
    med_s = f"{med:+.1f}\\%" if abs(med) >= 0.05 else "$-$0.0\\%"
    mean_s = f"{mean_d:+.0f}\\%" if abs(mean_d) >= 0.5 else f"{mean_d:+.1f}\\%"
    return (
        f"\\makecell[l]{{{label}}} & {succ}/25 & {_pct(rl_comm)} & "
        f"{_sci_pm(float(m_best.mean()), float(m_best.std(ddof=1)))} & "
        f"{_sci_pm(float(r_best.mean()), float(r_best.std(ddof=1)))} & "
        f"{med_s} & {wp:.2f} & {mean_s} & $-${comm_drop:.1f}\\% \\\\"
    )


def _replace_block(text: str, begin: str, end: str, body: str) -> str:
    if begin not in text or end not in text:
        raise SystemExit(f"Marker not found: {begin!r} / {end!r}")
    i = text.index(begin)
    j = text.index(end, i) + len(end)
    return text[:i] + body + text[j:]


def main() -> None:
    app_rows = "\n".join(
        [
            _app_row("Multi-area economic dispatch (13 generators, 1800\\,MW)", APP_SOURCES["MAED"]),
            _app_row("Resource-constrained distributed scheduling", APP_SOURCES["RESOURCE"]),
            _app_row("Electric-vehicle charging/discharging coordination", APP_SOURCES["EV"], ev=True),
        ]
    )
    app_table = f"""\\begin{{table*}}[!t]
\\centering
\\scriptsize
\\setlength{{\\tabcolsep}}{{4pt}}
\\caption{{Paired application-case comparison (25 paired runs per scenario; MACPO negotiates on every outer loop). Comm.\\ rate is the fraction of outer loops that trigger negotiation. $f_{{\\mathrm{{pure}}}}$: mean $\\pm$ sample std of per-run best pure objective; lower is better except EV dispatch, where a more negative value indicates higher net benefit. Both methods share the same evaluation-budget cap and paired random seeds.}}
\\label{{tab:application_cases}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{@{{}}lcccc@{{}}}}
\\toprule
\\textbf{{Scenario}} & \\textbf{{RL-MACPO comm.}} & \\textbf{{MACPO $f_{{\\mathrm{{pure}}}}$}} & \\textbf{{RL-MACPO $f_{{\\mathrm{{pure}}}}$}} & \\textbf{{$\\Delta$ / comm.\\ drop}} \\\\
\\midrule
{app_rows}
\\bottomrule
\\end{{tabular}}%
}}
\\end{{table*}}"""

    ieee_rows = "\n".join(
        [
            _ieee_row("IEEE 30-bus\\\\regional dispatch", IEEE_SOURCES["30"]),
            _ieee_row("IEEE 57-bus\\\\regional dispatch", IEEE_SOURCES["57"]),
            _ieee_row("IEEE 118-bus\\\\regional dispatch", IEEE_SOURCES["118"]),
        ]
    )
    ieee_table = f"""\\begin{{table*}}[!t]
\\centering
\\scriptsize
\\setlength{{\\tabcolsep}}{{3.5pt}}
\\caption{{Paired IEEE transmission-network dispatch (25 paired runs per case; MACPO negotiates on every outer loop). $f_{{\\mathrm{{pure}}}}$: mean $\\pm$ sample std of per-run best-so-far pure cost; lower is better. \\textbf{{Success}}: RL pure cost within twice the paired MACPO value (catastrophe flag, not a minor-variation tolerance; see text). $\\Delta=(\\mathrm{{MACPO}}-\\mathrm{{RL}})/|\\mathrm{{MACPO}}|\\times100\\%$ (positive values favor RL). \\textbf{{Median paired $\\Delta$}} is the primary cost statistic. \\textbf{{Wilcoxon}}: two-sided signed-rank test on paired differences. IEEE~30/57/118: fail-safe $K{{=}}2$.}}
\\label{{tab:ieee_power_cases}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{@{{}}lrcrrccrc@{{}}}}
\\toprule
\\textbf{{Case}} & \\textbf{{Succ.}} & \\textbf{{RL comm.}} & \\textbf{{MACPO $f_{{\\mathrm{{pure}}}}$}} & \\textbf{{RL $f_{{\\mathrm{{pure}}}}$}} & \\textbf{{Median $\\Delta$}} & \\textbf{{Wilcoxon $p$}} & \\textbf{{Mean $\\Delta$}} & \\textbf{{Comm.\\ drop}} \\\\
\\midrule
{ieee_rows}
\\bottomrule
\\multicolumn{{9}}{{@{{}}p{{0.98\\textwidth}}@{{}}}}{{\\footnotesize Pooled column-median cost gaps are near zero on IEEE~30, slightly worse on IEEE~57, and slightly worse on IEEE~118 (see table columns).}}
\\end{{tabular}}%
}}
\\end{{table*}}"""

    tex = TEX.read_text(encoding="utf-8")
    tex = tex.replace(
        "Table~\\ref{tab:application_cases}: MAED-13 (10 paired runs), resource scheduling, and EV dispatch "
        "under MACPO-style protocols; IEEE 30/57/118 (25 paired runs each) in Table~\\ref{tab:ieee_power_cases}.",
        "Table~\\ref{tab:application_cases}: MAED-13, resource scheduling, and EV dispatch (25 paired runs each); "
        "IEEE~30/57/118 (25 paired runs each) in Table~\\ref{tab:ieee_power_cases}.",
    )
    tex = _replace_block(tex, "\\begin{table*}[!t]\n\\centering\n\\scriptsize\n\\setlength{\\tabcolsep}{4pt}\n\\caption{Paired application-case", "\\end{table*}\n\n\\subsubsection{IEEE Transmission-Network Dispatch}", app_table + "\n\n\\subsubsection{IEEE Transmission-Network Dispatch}")
    tex = tex.replace(
        "IEEE 30/57/118 (25 paired runs; Table~\\ref{tab:ieee_power_cases}): median paired cost gaps are near zero on IEEE~30/57 with substantially lower communication; IEEE~118 shows a small detectable cost offset at much lower communication (statistically detectable difference, reflecting an accuracy--communication trade-off). Success 23/25 on IEEE~30 (two LLSO stagnation outliers, not lower communication rate).",
        "IEEE~30/57/118 (25 paired runs; Table~\\ref{tab:ieee_power_cases}): median paired cost gaps are near zero on IEEE~30/57 with substantially lower communication; IEEE~118 shows a small detectable cost offset at much lower communication (Wilcoxon $p{=}0.01$, reflecting an accuracy--communication trade-off). Success 23/25 on IEEE~30 (two LLSO stagnation outliers, not lower communication rate). All three cases use fail-safe $K{=}2$.",
    )
    tex = _replace_block(tex, "\\begin{table*}[!t]\n\\centering\n\\scriptsize\n\\setlength{\\tabcolsep}{3.5pt}\n\\caption{Paired IEEE transmission-network dispatch", "\\end{table*}\n\n\\paragraph{Q4 analysis", ieee_table + "\n\n\\paragraph{Q4 analysis")
    tex = tex.replace(
        "changing best $f_{\\mathrm{pure}}$ by at most about 1.8\\% (Table~\\ref{tab:application_cases})",
        "lowering communication by about 88\\% while improving or matching best $f_{\\mathrm{pure}}$ on all three dispatch simulators (Table~\\ref{tab:application_cases}; up to ${\\approx}11\\%$ improvement on resource scheduling)",
    )
    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched {TEX}")


if __name__ == "__main__":
    main()
