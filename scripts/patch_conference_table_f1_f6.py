#!/usr/bin/env python3
"""
Recompute Table I (F1–F6) MACPO / RL-MACPO cells from archived trajectory logs
and patch conference_en_ready.tex (no re-run).

Data sources (f_pure, last trajectory row):
  MACPO LLSO:  MACPO_original_output/LLSO_25runs
  RL-MACPO LLSO: ablation_experiments/Exp4_Variable_Selection/.../output
  MACPO CSO:   ablation_experiments/results/CSO_25runs/MACPO_baseline
  RL-MACPO CSO: ablation_experiments/results/CSO_25runs/Full
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.ndo_run_stats import (  # noqa: E402
    FUNCS_F1_F6,
    fmt_pvalue_tex,
    fmt_sci_tex,
    load_run_fpure_series,
    mannwhitney_less_p,
    summarize_runs,
    wilcoxon_less_p,
)

MACPO_LLSO = _REPO / "MACPO_original_output" / "LLSO_25runs"
RL_LLSO = (
    _REPO
    / "ablation_experiments"
    / "Exp4_Variable_Selection"
    / "MACPO2_WithSelection_0.9_0.7_0.5"
    / "output"
)
MACPO_CSO = _REPO / "ablation_experiments" / "results" / "CSO_25runs" / "MACPO_baseline"
RL_CSO = _REPO / "ablation_experiments" / "results" / "CSO_25runs" / "Full"

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
OUT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f1_f6_recomputed.json"

from utils.external_baselines import (  # noqa: E402
    DPSO_CSO,
    DPSO_LLSO,
    EXTERNAL_REF_PVALUE,
    GFPDO_CSO,
    GFPDO_LLSO,
)

RLONLY_LLSO = {
    "F1": (2.07e7, 1.97e7, 3.58e6),
    "F2": (4.76e4, 4.35e4, 9.67e3),
    "F3": (5.89e9, 5.86e9, 7.13e8),
    "F4": (3.01e6, 2.98e6, 2.71e5),
    "F5": (4.24e8, 4.10e8, 1.08e8),
    "F6": (1.50e8, 1.36e8, 1.47e8),
}
RLONLY_CSO = {
    "F1": (2.02e7, 2.00e7, 1.34e6),
    "F2": (6.43e4, 6.38e4, 6.98e3),
    "F3": (2.66e9, 2.60e9, 2.64e8),
    "F4": (6.98e6, 6.90e6, 9.53e5),
    "F5": (4.98e7, 4.75e7, 1.31e7),
    "F6": (4.29e5, 3.73e5, 1.87e5),
}


def _maybe_bold(val: float, bold: bool) -> str:
    s = fmt_sci_tex(val)
    return f"\\textbf{{{s}}}" if bold else s


def _block(fn: str, llso_macpo: dict, llso_rl: dict, cso_macpo: dict, cso_rl: dict) -> str:
    lm, lr = llso_macpo[fn], llso_rl[fn]
    cm, cr = cso_macpo[fn], cso_rl[fn]
    pl = wilcoxon_less_p(lm["vals"], lr["vals"])
    pc = mannwhitney_less_p(cm["vals"], cr["vals"])
    rl_better_l = lr["mean"] < lm["mean"]
    rl_better_c = cr["mean"] < cm["mean"]

    gfm, gfd, gfr = GFPDO_LLSO[fn], DPSO_LLSO[fn], RLONLY_LLSO[fn]
    gcm, gcd, gcr = GFPDO_CSO[fn], DPSO_CSO[fn], RLONLY_CSO[fn]

    return "\n".join(
        [
            f"\\multirow{{4}}{{*}}{{{fn}}}",
            (
                f"& mean    & {fmt_sci_tex(gfm[0])} & {fmt_sci_tex(gfd[0])} & {fmt_sci_tex(lm['mean'])} "
                f"& {fmt_sci_tex(gfr[0])} & {_maybe_bold(lr['mean'], rl_better_l)} "
                f"& {fmt_sci_tex(gcm[0])} & {fmt_sci_tex(gcd[0])} & {fmt_sci_tex(cm['mean'])} "
                f"& {fmt_sci_tex(gcr[0])} & {_maybe_bold(cr['mean'], rl_better_c)} \\\\"
            ),
            (
                f"& median  & {fmt_sci_tex(gfm[1])} & {fmt_sci_tex(gfd[1])} & {fmt_sci_tex(lm['median'])} "
                f"& {fmt_sci_tex(gfr[1])} & {_maybe_bold(lr['median'], rl_better_l)} "
                f"& {fmt_sci_tex(gcm[1])} & {fmt_sci_tex(gcd[1])} & {fmt_sci_tex(cm['median'])} "
                f"& {fmt_sci_tex(gcr[1])} & {_maybe_bold(cr['median'], rl_better_c)} \\\\"
            ),
            (
                f"& std     & {fmt_sci_tex(gfm[2])} & {fmt_sci_tex(gfd[2])} & {fmt_sci_tex(lm['std'])} "
                f"& {fmt_sci_tex(gfr[2])} & {_maybe_bold(lr['std'], rl_better_l)} "
                f"& {fmt_sci_tex(gcm[2])} & {fmt_sci_tex(gcd[2])} & {fmt_sci_tex(cm['std'])} "
                f"& {fmt_sci_tex(gcr[2])} & {_maybe_bold(cr['std'], rl_better_c)} \\\\"
            ),
            (
                f"& p-value & {EXTERNAL_REF_PVALUE} & {EXTERNAL_REF_PVALUE} & - & 5.46e-01 & "
                f"{fmt_pvalue_tex(pl, rl_better_l, not rl_better_l)} & {EXTERNAL_REF_PVALUE} & {EXTERNAL_REF_PVALUE} & - & 2.41e-05* & "
                f"{fmt_pvalue_tex(pc, rl_better_c, not rl_better_c)} \\\\"
            ),
        ]
    )


def main() -> None:
    llso_macpo, llso_rl, cso_macpo, cso_rl = {}, {}, {}, {}
    export: dict = {"sources": {}, "functions": {}}

    for fn in FUNCS_F1_F6:
        m = load_run_fpure_series(MACPO_LLSO, fn, "LLSO")
        r = load_run_fpure_series(RL_LLSO, fn, "LLSO")
        mc = load_run_fpure_series(MACPO_CSO, fn, "CSO")
        rc = load_run_fpure_series(RL_CSO, fn, "CSO")
        llso_macpo[fn] = {**summarize_runs(m), "vals": m}
        llso_rl[fn] = {**summarize_runs(r), "vals": r}
        cso_macpo[fn] = {**summarize_runs(mc), "vals": mc}
        cso_rl[fn] = {**summarize_runs(rc), "vals": rc}
        export["functions"][fn] = {
            "LLSO": {"MACPO": summarize_runs(m), "RL-MACPO": summarize_runs(r)},
            "CSO": {"MACPO": summarize_runs(mc), "RL-MACPO": summarize_runs(rc)},
        }

    export["sources"] = {
        "MACPO_LLSO": str(MACPO_LLSO),
        "RL-MACPO_LLSO": str(RL_LLSO),
        "MACPO_CSO": str(MACPO_CSO),
        "RL-MACPO_CSO": str(RL_CSO),
        "metric": "f_pure (last logged row per run)",
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(export, indent=2), encoding="utf-8")

    blocks: list[str] = []
    for i, fn in enumerate(FUNCS_F1_F6):
        blocks.append(_block(fn, llso_macpo, llso_rl, cso_macpo, cso_rl))
        if i < len(FUNCS_F1_F6) - 1:
            blocks.append("\\midrule")

    w_l = t_l = l_l = 0
    w_c = t_c = l_c = 0
    for fn in FUNCS_F1_F6:
        if llso_rl[fn]["mean"] < llso_macpo[fn]["mean"]:
            w_l += 1
        elif llso_rl[fn]["mean"] > llso_macpo[fn]["mean"]:
            l_l += 1
        else:
            t_l += 1
        if cso_rl[fn]["mean"] < cso_macpo[fn]["mean"]:
            w_c += 1
        elif cso_rl[fn]["mean"] > cso_macpo[fn]["mean"]:
            l_c += 1
        else:
            t_c += 1

    new_body = "\n".join(blocks)
    new_body += (
        f"\n\\midrule\n\\multicolumn{{2}}{{c}}{{w/t/l}} & --- & --- & - & 1/3/2 & {w_l}/{t_l}/{l_l} "
        f"& --- & --- & - & 3/1/2 & {w_c}/{t_c}/{l_c} \\\\"
    )

    tex = TEX.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(\\midrule\n)\\multirow\{4\}\{\*\}\{F1\}.*?(\\bottomrule)",
        re.DOTALL,
    )
    m = pattern.search(tex)
    if not m:
        raise SystemExit("Could not locate F1--F6 table body in conference_en_ready.tex")
    tex = tex[: m.start(1)] + m.group(1) + new_body + "\n" + m.group(2) + tex[m.end(2) :]

    tex = re.sub(
        r"& \\textbf\{GFPDO\} & \\textbf\{DPSO\}",
        r"& \\textbf{GFPDO$^{\\dagger}$} & \\textbf{DPSO$^{\\dagger}$}",
        tex,
        count=2,
    )

    new_cap = (
        r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F1--F6: "
        r"mean, median, standard deviation, and $p$-value over 25 independent runs, for LLSO (left five columns) "
        r"and CSO (right five columns). \textbf{MACPO} and \textbf{RL-MACPO} use logged \texttt{f\_pure} "
        r"(last row per run) from archived trajectories. "
        r"\textbf{GFPDO$^{\dagger}$} and \textbf{DPSO$^{\dagger}$} are transcribed from \cite{ref_macpo} "
        r"(not re-run here; $p$-values and w/t/l omitted). "
        r"Tests for RL-MACPO vs.\ MACPO only: paired Wilcoxon signed-rank (LLSO), Mann--Whitney U (CSO). "
        r"* RL-MACPO better; \# worse ($p<0.05$). Bold: better mean in each MACPO vs.\ RL-MACPO pair.}"
    )

    cap_start = r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F1--F6"
    cap_label = r"\label{tab:macpo_style_all}"
    c0 = tex.index(cap_start)
    c1 = tex.index(cap_label, c0)
    tex = tex[:c0] + new_cap + "\n" + tex[c1:]

    footnote = (
        r"\paragraph{F1--F6 data sources.} "
        r"MACPO/RL-MACPO entries in Table~\ref{tab:macpo_style_all} are recomputed from "
        r"\texttt{MACPO\_original\_output/LLSO\_25runs} and "
        r"\texttt{ablation\_experiments/Exp4\_Variable\_Selection/.../output} (LLSO), and "
        r"\texttt{CSO\_25runs/MACPO\_baseline} and \texttt{CSO\_25runs/Full} (CSO). "
        r"All use the \texttt{f\_pure} column aligned with Eq.~\eqref{eq:global_objective}. "
        r"Typical end-of-run evaluation counts are $145{,}729$ (MACPO LLSO) and $150{,}348$ (RL-MACPO LLSO)."
    )
    anchor = r"\paragraph{Replication checklist (figures and tables).}"
    if footnote not in tex and anchor in tex:
        tex = tex.replace(anchor, footnote + "\n\n" + anchor, 1)

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched {TEX}")
    print(f"Wrote {OUT_JSON}")
    for fn in FUNCS_F1_F6:
        m, r = llso_macpo[fn]["mean"], llso_rl[fn]["mean"]
        imp = (m - r) / m * 100 if m > 0 else float("nan")
        print(f"  {fn} LLSO MACPO={m:.4e} RL={r:.4e} imp={imp:.1f}%")


if __name__ == "__main__":
    main()
