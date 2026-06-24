#!/usr/bin/env python3
"""Clarify GFPDO/DPSO literature columns in Table I (keep columns; fix misleading p-values)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.external_baselines import EXTERNAL_REF_PVALUE  # noqa: E402

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"

NEW_CAPTION = (
    r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F1--F6: "
    r"mean, median, standard deviation, and $p$-value over 25 independent runs, for LLSO (left five columns) "
    r"and CSO (right five columns). \textbf{MACPO} and \textbf{RL-MACPO} use logged \texttt{f\_pure} "
    r"(last row per run) from archived trajectories. "
    r"\textbf{GFPDO$^{\dagger}$} and \textbf{DPSO$^{\dagger}$} are transcribed from \cite{ref_macpo} "
    r"(not re-run here; $p$-values and w/t/l omitted). "
    r"Tests for RL-MACPO vs.\ MACPO only: paired Wilcoxon signed-rank (LLSO), Mann--Whitney U (CSO). "
    r"* RL-MACPO better; \# worse ($p<0.05$). Bold: better mean in each MACPO vs.\ RL-MACPO pair.}"
)

EXT_PARA = (
    r"\paragraph{External reference columns (GFPDO$^{\dagger}$/DPSO$^{\dagger}$).} "
    r"Following the MACPO paper layout \cite{ref_macpo}, Table~\ref{tab:macpo_style_all} keeps "
    r"GFPDO \cite{ref_gfpdo} and DPSO \cite{ref_dpso} in the main table for cross-method scale context. "
    r"Their mean/median/std entries are \emph{literature anchors} transcribed from \cite{ref_macpo}; "
    r"we did not re-execute those baselines under the present RL-MACPO evaluation protocol. "
    r"Accordingly, no significance symbols are attached to GFPDO/DPSO cells, and all statistical tests "
    r"in the table apply only to the aligned MACPO-family trio (\textbf{MACPO}, \textbf{RL Only}, "
    r"\textbf{RL-MACPO}). Readers should treat GFPDO/DPSO as order-of-magnitude references, not as "
    r"paired competitors in our 25-run study."
)

OLD_GFPDO_PARA = (
    r"By contrast, \textbf{GFPDO} \cite{ref_gfpdo} and \textbf{DPSO} \cite{ref_dpso} are literature-reported "
    r"values from the MACPO paper and are \emph{not} re-run under our aligned budget; they are shown for "
    r"scale context only and should not be read as a fully aligned external baseline comparison."
)


def main() -> None:
    tex = TEX.read_text(encoding="utf-8")

    tex = re.sub(
        r"& \\textbf\{GFPDO\} & \\textbf\{DPSO\}",
        r"& \\textbf{GFPDO$^{\\dagger}$} & \\textbf{DPSO$^{\\dagger}$}",
        tex,
        count=2,
    )

    tex = re.sub(
        r"& p-value & 5\.46e-06\\# & 9\.13e-05\\# & -",
        f"& p-value & {EXTERNAL_REF_PVALUE} & {EXTERNAL_REF_PVALUE} & -",
        tex,
    )
    tex = re.sub(
        r"\\midrule\n\\multicolumn\{2\}\{c\}\{w/t/l\} & 0/0/6 & 0/0/6 & -",
        r"\\midrule\n\\multicolumn{2}{c}{w/t/l} & --- & --- & -",
        tex,
        count=1,
    )

    cap_start = r"\caption{Final global objective $F$ (Eq.~\protect\eqref{eq:global_objective}) on F1--F6"
    cap_label = r"\label{tab:macpo_style_all}"
    c0 = tex.index(cap_start)
    c1 = tex.index(cap_label, c0)
    tex = tex[:c0] + NEW_CAPTION + "\n" + tex[c1:]

    if OLD_GFPDO_PARA in tex:
        tex = tex.replace(OLD_GFPDO_PARA, EXT_PARA, 1)
    elif EXT_PARA not in tex:
        anchor = r"Within each optimizer block, the three MACPO-family columns"
        if anchor in tex:
            tex = tex.replace(anchor, EXT_PARA + "\n\n" + anchor, 1)

    TEX.write_text(tex, encoding="utf-8")
    print(f"Updated GFPDO/DPSO presentation in {TEX}")


if __name__ == "__main__":
    main()
