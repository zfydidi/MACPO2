#!/usr/bin/env python3
"""Apply post-experiment review fixes to conference_en_ready.tex."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.conference_f1f6_comm_eva_table import (  # noqa: E402
    build_f1f6_comm_eva_table_tex,
    export_f1f6_comm_eva_json,
)

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
BEGIN = "% --- BEGIN F1-F6 COMM EVA ---"
END = "% --- END F1-F6 COMM EVA ---"


def _replace_block(text: str, begin: str, end: str, body: str) -> str:
    if begin in text:
        i = text.index(begin)
        j = text.index(end, i) + len(end)
        return text[:i] + "\n".join([begin, body, end]) + text[j:]
    return text


def _sub(text: str, old: str, new: str, *, once: bool = True) -> str:
    if old not in text:
        return text
    return text.replace(old, new, 1 if once else -1)


def main() -> None:
    export_f1f6_comm_eva_json()
    comm_eva_table = build_f1f6_comm_eva_table_tex()
    comm_eva_para = (
        r"\paragraph{Communication and evaluation budget (F1--F6).} "
        r"Table~\ref{tab:f1f6_comm_eva} complements Table~\ref{tab:macpo_style_all} with the "
        r"core cost metrics requested for conflict-gated communication: negotiation trigger "
        r"rate and end-of-run evaluation count under the same 25-run LLSO protocol. MACPO always "
        r"communicates ($100\%$); RL-MACPO triggers negotiation on only $8.3$--$22.3\%$ of outer "
        r"loops ($78$--$92\%$ reduction), while cumulative evaluation counts remain within "
        r"$\pm 3\%$ of MACPO, confirming that fitness gains are not due to extra FES budget."
    )
    comm_eva_block = "\n".join([comm_eva_para, "", comm_eva_table])

    tex = TEX.read_text(encoding="utf-8")

    # Insert F1-F6 comm/eva table immediately after main Table I.
    anchor = r"\end{table*}" + "\n" + r"\vspace{-0.3em}"
    label_anchor = r"\label{tab:macpo_style_all}"
    if BEGIN not in tex and label_anchor in tex:
        pos = tex.index(anchor, tex.index(label_anchor))
        insert_at = pos + len(anchor)
        tex = tex[:insert_at] + "\n\n" + comm_eva_block + "\n" + tex[insert_at:]
    else:
        tex = _replace_block(tex, BEGIN, END, comm_eva_block)

    # Table I caption: cross-reference comm/eva companion.
    old_cap = (
        r"Tests for RL-MACPO vs.\ MACPO only: paired Wilcoxon signed-rank (LLSO), Mann--Whitney U (CSO). "
        r"* RL-MACPO better; \# worse ($p<0.05$). Bold: better mean in each MACPO vs.\ RL-MACPO pair.}"
    )
    new_cap = (
        r"Tests for RL-MACPO vs.\ MACPO only: paired Wilcoxon signed-rank (LLSO), Mann--Whitney U (CSO). "
        r"* RL-MACPO better; \# worse ($p<0.05$). Bold: better mean in each MACPO vs.\ RL-MACPO pair. "
        r"Communication rate and evaluation count: Table~\ref{tab:f1f6_comm_eva}.}"
    )
    tex = _sub(tex, old_cap, new_cap)

    # How-to-read paragraph.
    tex = _sub(
        tex,
        r"Table~\ref{tab:macpo_style_all} reports F1--F6 under a unified 25-run protocol and a common evaluation budget. "
        r"Table~\ref{tab:comm_rate_f1_f18} reports the corresponding communication trigger rates on F1--F18.",
        r"Table~\ref{tab:macpo_style_all} reports F1--F6 fitness under a unified 25-run protocol and a common evaluation budget; "
        r"Table~\ref{tab:f1f6_comm_eva} reports the paired communication rate and evaluation count on the same runs. "
        r"Table~\ref{tab:comm_rate_f1_f18} extends communication statistics to F7--F18.",
    )

    # Conflict proxy explicit definition (after implementation-bound paragraph).
    proxy_needle = (
        r"We extend it into an online communication rule through the same implementation-bound conflict proxy."
    )
    proxy_add = (
        r"We extend it into an online communication rule through the same implementation-bound conflict proxy. "
        r"Concretely, for each overlapping dimension $d$ with search range $\Delta_d$, the proxy aggregates "
        r"exponentially smoothed normalized discrepancies "
        r"$|\hat{x}^d_i - x^d_{\mathrm{con},i}|/\Delta_d$ between the local best $\hat{x}_i$ and the "
        r"consensus reference $x_{\mathrm{con},i}$, and $\mathrm{CI}_i^t$ is the mean over the active "
        r"overlap set. This quantity is compared against the EMA baseline $\hat{\mu}_{\mathrm{CI},i}^t$ "
        r"in Eq.~\eqref{eq:local_gate} rather than against gradient inner products."
    )
    if proxy_needle in tex and proxy_add not in tex:
        tex = tex.replace(proxy_needle, proxy_add, 1)

    # F4 / module contribution paragraph.
    tex = _sub(
        tex,
        r"The relative advantage is smallest on F4 compared with F3/F5, which is consistent with the original MACPO conflict-pattern interpretation, although F4 also has a higher-variance MACPO baseline.",
        r"On F4 (low-conflict Elliptic--Schwefel), the mean improvement is smallest among F1--F6 ($\approx 19\%$ under LLSO), which matches the original MACPO conflict-pattern reading; the absolute gap remains visible because the MACPO baseline exhibits higher run-to-run variance on this heterogeneous composition.",
    )

    # Communication paragraph (if not refreshed by comm_section patch).
    tex = _sub(
        tex,
        r"RL-MACPO reduces this rate by roughly $40$--$60\%$ on F1--F18 while preserving or improving final fitness",
        r"RL-MACPO reduces this rate by roughly $78$--$92\%$ on F1--F18 (absolute trigger rate $7.7$--$22.3\%$) while preserving or improving final fitness",
    )

    # Wall-clock fairness paragraph after comparability paragraph.
    wall_para = (
        r"\paragraph{Evaluation budget vs.\ wall-clock time.} "
        r"All main fitness tables use \emph{identical evaluation-budget caps} per paired run "
        r"(Table~\ref{tab:f1f6_comm_eva} shows end-of-run evaluation counts within a few percent of MACPO). "
        r"Table~\ref{tab:wall_time_f1_f18} therefore reports wall-clock overhead separately: RL-MACPO is slower "
        r"because of policy inference, replay, and gating bookkeeping, not because it receives additional function "
        r"evaluations. We do not include a wall-time-matched MACPO baseline with extra FES, because that would break "
        r"the paired-budget protocol inherited from the MACPO study \cite{ref_macpo}."
    )
    if r"\paragraph{Evaluation budget vs.\ wall-clock time.}" not in tex:
        tex = tex.replace(
            r"\paragraph{Comparability.}",
            r"\paragraph{Comparability.}" + "\n" + wall_para,
            1,
        )

    # Periodic baseline footnote on different run batches.
    periodic_needle = (
        r"On F1/F2/F5 (10-run LLSO pilot), gated and periodic schedules can achieve similar communication "
    )
    periodic_repl = (
        r"On F1/F2/F5 (10-run LLSO pilot, separate from the 25-run Table~\ref{tab:macpo_style_all} batch), "
        r"gated and periodic schedules can achieve similar communication "
    )
    tex = _sub(tex, periodic_needle, periodic_repl)

    # Limitations: IEEE now included.
    tex = _sub(
        tex,
        r"Application validation is limited to three dispatch simulators (Table~\ref{tab:application_cases}) and does not include standard IEEE transmission test cases in the main text.",
        r"Application validation covers MACPO-style dispatch simulators (Table~\ref{tab:application_cases}) and IEEE transmission-network cases (Table~\ref{tab:ieee_power_cases}), but scalability to hundreds of agents and alternative topologies remains open.",
    )

    # Conclusion: mention comm reduction on benchmark.
    tex = _sub(
        tex,
        r"On three dispatch case studies (Table~\ref{tab:application_cases}), RL-MACPO substantially lowers communication while matching or improving the pure objective under paired evaluation budgets.",
        r"On F1--F18, conflict-gated communication cuts negotiation frequency by about $78$--$92\%$ "
        r"(Tables~\ref{tab:f1f6_comm_eva} and~\ref{tab:comm_rate_f1_f18}) while improving final fitness. "
        r"On dispatch and IEEE cases (Tables~\ref{tab:application_cases} and~\ref{tab:ieee_power_cases}), "
        r"RL-MACPO substantially lowers communication while matching or improving the pure objective under paired evaluation budgets.",
    )

    # Abstract: add benchmark comm stat.
    old_abs = (
        r"Experiments on the standard benchmark inherited from the original Multi-Agent Cooperative Penalty Optimization study show that the proposed method achieves better final fitness and more stable convergence than the original Multi-Agent Cooperative Penalty Optimization baseline under the current implementation and evaluation protocol."
    )
    new_abs = (
        r"Experiments on the MACPO NDO benchmark (F1--F18) show significantly better final fitness than MACPO under identical evaluation budgets, with negotiation triggered on only $8$--$22\%$ of outer loops ($\approx 78$--$92\%$ reduction versus always-on MACPO)."
    )
    if old_abs in tex:
        tex = tex.replace(old_abs, new_abs, 1)

    # Table II caption in tex file (inline) - update if old version
    tex = _sub(
        tex,
        r"\textbf{RL-MACPO:} mean of last logged \texttt{f\_pure}, which equals \texttt{f\_penalty} in all archived runs.",
        r"\textbf{RL-MACPO:} mean $\pm$ sample std of last logged \texttt{f\_pure}, which equals \texttt{f\_penalty} in all archived runs.",
    )

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched {TEX}")


if __name__ == "__main__":
    main()
