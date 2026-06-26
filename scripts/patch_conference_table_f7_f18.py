#!/usr/bin/env python3
"""
Recompute Table II (F7--F18) from archived logs and patch conference_en_ready.tex.

MACPO: penalized ``final fitness`` from MACPO_original_output completion logs.
RL-MACPO: last logged ``f_pure`` (equals ``f_penalty`` at budget end in our archive).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.macpo_exp_fitness import load_macpo_final_fitness_series  # noqa: E402
from utils.ndo_run_stats import (  # noqa: E402
    FUNCS_F7_F18,
    fmt_macpo_cell,
    fmt_sci_tex,
    load_run_fpure_series_exp,
    summarize_runs,
)

RL_ROOT = _REPO / "MACPO2_deployment" / "output"
TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
OUT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f7_f18_recomputed.json"

NEW_CAPTION = (
    r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F7--F18 "
    r"over 25 independent runs: MACPO vs.\ RL-MACPO under LLSO and CSO. "
    r"Both methods report the same $F(\mathbf{X})$ at the budget endpoint. "
    r"\textbf{MACPO$^{\ddagger}$:} mean $\pm$ sample std of archived endpoint $F$ "
    r"(still penalized when overlap inconsistency remains). "
    r"\textbf{RL-MACPO:} mean $\pm$ sample std of last logged \texttt{f\_pure}, which equals \texttt{f\_penalty} "
    r"in all archived runs. Lower is better; \textbf{bold}: better mean within each pair. "
    r"Large gaps on F9/F15 reflect MACPO failing to eliminate constraint violation under "
    r"static penalties, not mixed metrics. Last row: w/t/l.}"
)

FOOTNOTE = (
    r"\paragraph{F7--F18 data sources and metrics.} "
    r"Table~\ref{tab:macpo_rl_mean_f1_f18} MACPO entries are recomputed from "
    r"\texttt{MACPO\_original\_output/\{LLSO,CSO\}/F*/} completion logs; RL-MACPO entries use "
    r"last-row \texttt{f\_pure} from \texttt{MACPO2\_deployment/output/}. "
    r"Both sides share the same 25-run evaluation-budget protocol and the same objective $F$ "
    r"in Eq.~\eqref{eq:global_objective}. RL-MACPO reaches "
    r"\texttt{f\_pure}$\approx$\texttt{f\_penalty} at the budget end; MACPO endpoints still "
    r"include residual overlap penalty when static negotiation does not converge. "
    r"We did not post-hoc re-evaluate MACPO $f_{\mathrm{pure}}$ on F7--F18 because the baseline "
    r"archive does not store final assembled solutions."
)


def _row(fn: str, llso_m: dict, llso_r: dict, cso_m: dict, cso_r: dict) -> str:
    rl_better_l = llso_r["mean"] < llso_m["mean"]
    rl_better_c = cso_r["mean"] < cso_m["mean"]
    rl_l = fmt_macpo_cell(llso_r["mean"], llso_r["std"])
    rl_c = fmt_macpo_cell(cso_r["mean"], cso_r["std"])
    if rl_better_l:
        rl_l = f"\\textbf{{{rl_l}}}"
    if rl_better_c:
        rl_c = f"\\textbf{{{rl_c}}}"
    return (
        f"{fn} & {fmt_macpo_cell(llso_m['mean'], llso_m['std'])} & {rl_l} & "
        f"{fmt_macpo_cell(cso_m['mean'], cso_m['std'])} & {rl_c} \\\\"
    )


def main() -> None:
    export: dict = {"sources": {}, "functions": {}, "metric_note": FOOTNOTE}
    llso_m, llso_r, cso_m, cso_r = {}, {}, {}, {}
    rows: list[str] = []

    for i, fn in enumerate(FUNCS_F7_F18):
        m_ll = load_macpo_final_fitness_series(fn, "LLSO")
        m_cs = load_macpo_final_fitness_series(fn, "CSO")
        r_ll = load_run_fpure_series_exp(RL_ROOT / "LLSO" / fn, fn)
        r_cs = load_run_fpure_series_exp(RL_ROOT / "CSO" / fn, fn)
        llso_m[fn] = summarize_runs(m_ll)
        llso_r[fn] = summarize_runs(r_ll)
        cso_m[fn] = summarize_runs(m_cs)
        cso_r[fn] = summarize_runs(r_cs)
        export["functions"][fn] = {
            "LLSO": {"MACPO_penalized": llso_m[fn], "RL-MACPO_f_pure": llso_r[fn]},
            "CSO": {"MACPO_penalized": cso_m[fn], "RL-MACPO_f_pure": cso_r[fn]},
        }
        rows.append(_row(fn, llso_m[fn], llso_r[fn], cso_m[fn], cso_r[fn]))
        if fn == "F12":
            rows.append("\\midrule")

    w_l = t_l = l_l = w_c = t_c = l_c = 0
    for fn in FUNCS_F7_F18:
        if llso_r[fn]["mean"] < llso_m[fn]["mean"]:
            w_l += 1
        elif llso_r[fn]["mean"] > llso_m[fn]["mean"]:
            l_l += 1
        else:
            t_l += 1
        if cso_r[fn]["mean"] < cso_m[fn]["mean"]:
            w_c += 1
        elif cso_r[fn]["mean"] > cso_m[fn]["mean"]:
            l_c += 1
        else:
            t_c += 1

    body = "\n".join(rows)
    body += (
        f"\n\\midrule\n\\multicolumn{{1}}{{c}}{{w/t/l}} & "
        f"\\multicolumn{{2}}{{c}}{{{w_l}/{t_l}/{l_l}}} & "
        f"\\multicolumn{{2}}{{c}}{{{w_c}/{t_c}/{l_c}}} \\\\"
    )

    export["sources"] = {
        "MACPO": str(_REPO / "MACPO_original_output"),
        "RL-MACPO": str(RL_ROOT),
        "MACPO_metric": "penalized final fitness (completion logs)",
        "RL_metric": "f_pure (last trajectory row; equals f_penalty at budget end)",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(export, indent=2), encoding="utf-8")

    tex = TEX.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(\\midrule\n)F7 & .*?(\\bottomrule)",
        re.DOTALL,
    )
    m = pattern.search(tex)
    if not m:
        raise SystemExit("Could not locate F7--F18 table body")
    tex = tex[: m.start(1)] + m.group(1) + body + "\n" + m.group(2) + tex[m.end(2) :]

    cap_start = r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F7--F18"
    cap_label = r"\label{tab:macpo_rl_mean_f1_f18}"
    c0 = tex.index(cap_start)
    c1 = tex.index(cap_label, c0)
    tex = tex[:c0] + NEW_CAPTION + "\n" + tex[c1:]

    anchor = r"\paragraph{F1--F6 data sources.}"
    if FOOTNOTE not in tex and anchor in tex:
        tex = tex.replace(anchor, FOOTNOTE + "\n\n" + anchor, 1)

    old_table2 = (
        r"Table~\ref{tab:macpo_rl_mean_f1_f18} reports F7--F18 for MACPO and RL-MACPO under LLSO and CSO. "
        r"MACPO$^{\ddagger}$ uses archived penalized \texttt{final fitness} (no \texttt{f\_pure} trace); "
        r"RL-MACPO uses last-row \texttt{f\_pure}, which matches \texttt{f\_penalty} at the evaluation budget "
        r"in our logs. Apparent multi-order-of-magnitude gaps on conflict-heavy functions (F9, F15) are "
        r"therefore not a logging inconsistency but MACPO failing to drive penalties down under the fixed "
        r"static-penalty setting."
    )
    new_table2 = (
        r"Table~\ref{tab:macpo_rl_mean_f1_f18} reports F7--F18 for MACPO and RL-MACPO under LLSO and CSO. "
        r"Both columns report the same global objective $F(\mathbf{X})$ in Eq.~\eqref{eq:global_objective} "
        r"at the evaluation-budget endpoint. In RL-MACPO logs, \texttt{f\_pure} and \texttt{f\_penalty} have "
        r"converged to equality at budget exhaustion (residual penalty $\rightarrow 0$). Under MACPO with "
        r"static penalties, the archived endpoint is the same $F$ but still carries a large overlap-penalty "
        r"term because negotiation fails to restore consistency on high-conflict instances (F9, F15); MACPO "
        r"therefore remains orders of magnitude worse while using the same objective definition, not a "
        r"different metric."
    )
    if old_table2 in tex:
        tex = tex.replace(old_table2, new_table2, 1)
    elif new_table2 not in tex:
        needle = r"Table~\ref{tab:macpo_rl_mean_f1_f18} reports F7--F18"
        if needle in tex:
            start = tex.index(needle)
            end = tex.index("Table~\\ref{tab:wall_time_f1_f18}", start)
            tex = tex[:start] + new_table2 + " " + tex[end:]

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched {TEX}")
    print(f"Wrote {OUT_JSON}")
    print(f"  w/t/l LLSO={w_l}/{t_l}/{l_l} CSO={w_c}/{t_c}/{l_c}")


if __name__ == "__main__":
    main()
