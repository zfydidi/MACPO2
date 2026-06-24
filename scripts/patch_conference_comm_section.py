#!/usr/bin/env python3
"""Insert communication-rate table + periodic baseline into conference_en_ready.tex."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.conference_comm_table import (  # noqa: E402
    build_comm_rate_table_tex,
    build_periodic_baseline_table_tex,
    load_comm_json,
)

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_en_ready.tex"
COMM_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_rate_f1_f18.json"
PERIODIC_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "periodic_baseline_f125.json"

BEGIN = "% --- BEGIN COMM RATE F1-F18 ---"
END = "% --- END COMM RATE F1-F18 ---"
PBEGIN = "% --- BEGIN PERIODIC BASELINE ---"
PEND = "% --- END PERIODIC BASELINE ---"


def _replace_block(text: str, begin: str, end: str, body: str) -> str:
    if begin not in text:
        raise SystemExit(f"Marker not found: {begin}")
    i = text.index(begin)
    j = text.index(end, i) + len(end)
    return text[:i] + "\n".join([begin, body, end]) + text[j:]


def main() -> None:
    comm_rows = load_comm_json(COMM_JSON)
    comm_table = build_comm_rate_table_tex(comm_rows)
    comm_para = (
        r"\paragraph{Communication on the NDO benchmark.} "
        r"Table~\ref{tab:comm_rate_f1_f18} reports the fraction of outer loops that trigger "
        r"neighbor negotiation under the same 25-run LLSO protocol as the main fitness tables. "
        r"MACPO negotiates every round ($100\%$). RL-MACPO reduces this rate by roughly "
        r"$40$--$60\%$ on F1--F18 while preserving or improving final fitness "
        r"(Tables~\ref{tab:macpo_style_all} and~\ref{tab:macpo_rl_mean_f1_f18})."
    )
    comm_block = "\n".join([comm_para, "", comm_table])

    text = TEX.read_text(encoding="utf-8")
    text = _replace_block(text, BEGIN, END, comm_block)

    if PERIODIC_JSON.is_file():
        periodic_rows = json.loads(PERIODIC_JSON.read_text(encoding="utf-8"))
        periodic_table = build_periodic_baseline_table_tex(periodic_rows)
        periodic_para = (
        r"\paragraph{Gated vs.\ periodic communication.} "
        r"Table~\ref{tab:periodic_baseline} compares conflict-gated RL-MACPO (\emph{Full}) against "
        r"fixed-interval baselines (\emph{Periodic-$K$}: negotiate every $K$ outer loops with RL penalty on "
        r"and CI gating disabled). Periodic rules induce deterministic communication rates ($\approx 1/K$). "
        r"On F1/F2/F5 (10-run LLSO pilot), gated and periodic schedules can achieve similar communication "
        r"frequencies with overlapping fitness variance; on F5, overly sparse gating may under-communicate "
        r"relative to periodic-$K$ at matched budgets. The comparison motivates conflict-adaptive triggering "
        r"across heterogeneous benchmark classes rather than a single static interval."
        )
        periodic_block = "\n".join([periodic_para, "", periodic_table])
        text = _replace_block(text, PBEGIN, PEND, periodic_block)

    TEX.write_text(text, encoding="utf-8")
    print(f"Updated {TEX}")


if __name__ == "__main__":
    main()
