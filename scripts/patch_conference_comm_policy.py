#!/usr/bin/env python3
"""Patch conference_en_ready.tex: comm-policy narrative, scalability, threshold baselines."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.conference_comm_table import (  # noqa: E402
    build_periodic_baseline_table_tex,
    load_comm_json,
)
from utils.conference_periodic_analysis import (  # noqa: E402
    build_adaptation_table_tex,
    build_comm_efficiency_table_tex,
    build_threshold_baseline_table_tex,
)
from utils.conference_scalability_table import build_scalability_table_tex  # noqa: E402

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
PERIODIC_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "periodic_baseline_f125.json"

PBEGIN = "% --- BEGIN PERIODIC BASELINE ---"
PEND = "% --- END PERIODIC BASELINE ---"
ABEGIN = "% --- BEGIN COMM POLICY ANALYSIS ---"
AEND = "% --- END COMM POLICY ANALYSIS ---"
SBEGIN = "% --- BEGIN SCALABILITY TABLE ---"
SEND = "% --- END SCALABILITY TABLE ---"
TBEGIN = "% --- BEGIN THRESHOLD BASELINE ---"
TEND = "% --- END THRESHOLD BASELINE ---"


def _replace_block(text: str, begin: str, end: str, body: str) -> str:
    if begin not in text:
        return text
    i = text.index(begin)
    j = text.index(end, i) + len(end)
    return text[:i] + "\n".join([begin, body, end]) + text[j:]


def _insert_after(text: str, anchor: str, block: str) -> str:
    if block.strip() in text:
        return text
    pos = text.index(anchor) + len(anchor)
    return text[:pos] + "\n\n" + block + "\n" + text[pos:]


def main() -> None:
    import json

    periodic_rows = json.loads(PERIODIC_JSON.read_text(encoding="utf-8")) if PERIODIC_JSON.is_file() else []
    periodic_table = build_periodic_baseline_table_tex(periodic_rows)
    periodic_para = (
        r"\paragraph{Gated vs.\ periodic communication.} "
        r"Table~\ref{tab:periodic_baseline} reports a 10-run pilot on F1/F2/F5. "
        r"A fixed interval $K$ is \emph{problem-specific}: Periodic-5 is best on F1/F2, "
        r"Periodic-3 on F5 (Table~\ref{tab:comm_policy_adaptation}). "
        r"Raw fitness therefore does not uniformly favor RL gating or a single $K$. "
        r"The advantage of conflict-gated RL is \textbf{cross-heterogeneity without tuning}: "
        r"RL comm.\ rate shifts from $\approx 22\%$ on F1/F2 to $\approx 8\%$ on F3--F6 "
        r"(Table~\ref{tab:f1f6_comm_eva}) while maintaining best-in-paper fitness on all "
        r"six functions (Table~\ref{tab:macpo_style_all}). "
        r"Table~\ref{tab:comm_efficiency_f125} scores fitness and communication jointly "
        r"(25-run RL fitness + comm.; periodic pilot); RL gated achieves the best joint score "
        r"on F1, F2, and F5 under this metric."
    )
    periodic_block = "\n".join([periodic_para, "", periodic_table])

    analysis_block = "\n".join(
        [
            r"\paragraph{Cross-function communication adaptation.}",
            r"Table~\ref{tab:comm_policy_adaptation} contrasts theory conflict intensity, "
            r"RL trigger rate (25 runs), and the best fixed-$K$ pilot on F1/F2/F5. "
            r"No single periodic policy is optimal across functions.",
            "",
            build_adaptation_table_tex(periodic_rows),
            "",
            build_comm_efficiency_table_tex(periodic_rows),
        ]
    )

    scale_block = "\n".join(
        [
            r"\subsubsection{Benchmark-scale scalability}",
            r"Table~\ref{tab:scalability_chain} summarizes the MACPO benchmark tiers "
            r"(20/40/60 agents on F1/F7/F13). Communication reduction remains large at "
            r"moderate scale while final fitness stays favorable for RL-MACPO.",
            "",
            build_scalability_table_tex(),
        ]
    )

    threshold_block = "\n".join(
        [
            r"\paragraph{Threshold-triggered baselines.}",
            r"Table~\ref{tab:threshold_baseline} compares fixed- and relative-threshold "
            r"event-triggered rules (pilot; generate via \texttt{scripts/run\_comm\_baselines.py}).",
            "",
            build_threshold_baseline_table_tex(),
        ]
    )

    tex = TEX.read_text(encoding="utf-8")
    tex = _replace_block(tex, PBEGIN, PEND, periodic_block)
    tex = _replace_block(tex, ABEGIN, AEND, analysis_block) if ABEGIN in tex else _insert_after(
        tex, PEND, ABEGIN + "\n" + analysis_block + "\n" + AEND
    )
    tex = _replace_block(tex, SBEGIN, SEND, scale_block) if SBEGIN in tex else _insert_after(
        tex, AEND if AEND in tex else PEND,
        SBEGIN + "\n" + scale_block + "\n" + SEND,
    )
    tex = _replace_block(tex, TBEGIN, TEND, threshold_block) if TBEGIN in tex else _insert_after(
        tex, SEND if SEND in tex else AEND,
        TBEGIN + "\n" + threshold_block + "\n" + TEND,
    )

    # Limitations: scalability partially addressed
    old_lim = (
        r"Application validation covers MACPO-style dispatch simulators (Table~\ref{tab:application_cases}) "
        r"and IEEE transmission-network cases (Table~\ref{tab:ieee_power_cases}), but scalability to hundreds "
        r"of agents and alternative topologies remains open."
    )
    new_lim = (
        r"Application validation covers MACPO-style dispatch simulators (Table~\ref{tab:application_cases}) "
        r"and IEEE transmission-network cases (Table~\ref{tab:ieee_power_cases}). "
        r"Benchmark-scale growth to 60 agents is reported in Table~\ref{tab:scalability_chain}; "
        r"hundreds of agents, alternative topologies, and asynchronous links remain future work."
    )
    if old_lim in tex:
        tex = tex.replace(old_lim, new_lim, 1)

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched {TEX}")


if __name__ == "__main__":
    main()
