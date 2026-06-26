#!/usr/bin/env python3
"""Insert or refresh the application-case subsection in conference_en_ready.tex."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.application_experiment_table import build_full_application_section_tex  # noqa: E402

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
BEGIN = "% --- BEGIN APPLICATION CASES ---"
END = "% --- END APPLICATION CASES ---"


def main() -> None:
    section = build_full_application_section_tex()
    block = f"{BEGIN}\n{section}\n{END}\n"
    tex = TEX.read_text(encoding="utf-8")

    if BEGIN in tex and END in tex:
        i0 = tex.index(BEGIN)
        i1 = tex.index(END, i0) + len(END)
        if i1 < len(tex) and tex[i1] == "\n":
            i1 += 1
        tex = tex[:i0] + block + tex[i1:]
    else:
        anchor = r"\section{Complexity and Cost Analysis}\label{sec:complexity}"
        if anchor not in tex:
            raise SystemExit("Anchor for application section not found")
        tex = tex.replace(anchor, block + "\n" + anchor, 1)

    # Abstract: mention application validation once
    old_abs_tail = (
        "under the current implementation and evaluation protocol."
    )
    new_abs_tail = (
        "under the current implementation and evaluation protocol. "
        "On three networked dispatch case studies---multi-area economic dispatch, "
        "resource-constrained scheduling, and EV charging coordination---RL-MACPO "
        "reduces negotiation frequency by about 80--89\\% while preserving or "
        "improving the pure objective under the same evaluation budget."
    )
    if old_abs_tail in tex and new_abs_tail not in tex:
        tex = tex.replace(old_abs_tail, new_abs_tail, 1)

    # Experiments setup: cross-reference
    setup_needle = (
        r"In all main results, RL-MACPO is evaluated under the default \emph{Full} configuration"
    )
    setup_add = (
        r"Application-case results on engineering dispatch simulators are reported separately in "
        r"Section~\ref{sec:applications}. "
    )
    if setup_needle in tex and setup_add not in tex:
        tex = tex.replace(setup_needle, setup_add + setup_needle, 1)

    # Conclusion
    old_conc = (
        r"with gate-mechanism ablations supporting the communication design."
    )
    new_conc = (
        r"with gate-mechanism ablations supporting the communication design. "
        r"On three dispatch case studies (Table~\ref{tab:application_cases}), RL-MACPO "
        r"substantially lowers communication while matching or improving the pure objective "
        r"under paired evaluation budgets."
    )
    if old_conc in tex and new_conc not in tex:
        tex = tex.replace(old_conc, new_conc, 1)

    # Limitations: note application scope
    lim_needle = (
        r"The present experiments are also based mostly on standard LLSO and CSO functions"
    )
    lim_repl = (
        r"Application validation is limited to three dispatch simulators (Table~\ref{tab:application_cases}) "
        r"and does not include standard IEEE transmission test cases in the main text. "
        r"The synthetic benchmark experiments are based mostly on standard LLSO and CSO functions"
    )
    if lim_needle in tex and "Application validation is limited" not in tex:
        tex = tex.replace(lim_needle, lim_repl, 1)

    TEX.write_text(tex, encoding="utf-8")
    print(f"Updated {TEX}")


if __name__ == "__main__":
    main()
