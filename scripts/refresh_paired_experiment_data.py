#!/usr/bin/env python3
"""Refresh patent_supplement/paired_experiment_data.json from latest 25-run summaries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

OUT = _REPO / "patent_supplement" / "paired_experiment_data.json"

SOURCES = {
    "MAED13": _REPO / "power_dispatch_sim/output/maed_20260701_175417/MAED13/summary.json",
    "RESOURCE": _REPO / "power_dispatch_sim/output/paper_20260701_175627/RESOURCE/summary.json",
    "EVDISPATCH": _REPO / "power_dispatch_sim/output/paper_20260701_175627/EVDISPATCH/summary.json",
}


def row_from_summary(key: str, path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    m, r = raw["MACPO"], raw["RL-MACPO"]
    return {
        "runs": int(raw.get("runs", m.get("n", 25))),
        "macpo_comm_rate": float(m["comm_rate_mean"]),
        "rl_comm_rate": float(r["comm_rate_mean"]),
        "comm_reduction_pct": float(raw.get("comm_reduction_pct", 0.0)),
        "macpo_best_f_pure": float(m["best_f_pure_mean"]),
        "rl_best_f_pure": float(r["best_f_pure_mean"]),
        "best_f_pure_improvement_pct": float(raw.get("best_f_pure_improvement_pct", 0.0)),
        "macpo_eva": float(m["eva_count_mean"]),
        "rl_eva": float(r["eva_count_mean"]),
        "macpo_outer_iters": float(m["outer_iters_mean"]),
        "rl_outer_iters": float(r["outer_iters_mean"]),
        "macpo_wall_ms": float(m["wall_ms_mean"]),
        "rl_wall_ms": float(r["wall_ms_mean"]),
        "source": str(path.relative_to(_REPO)),
    }


def main() -> None:
    payload = {k: row_from_summary(k, p) for k, p in SOURCES.items() if p.is_file()}
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(payload)} scenarios)")


if __name__ == "__main__":
    main()
