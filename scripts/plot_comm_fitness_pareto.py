#!/usr/bin/env python3
"""Communication rate vs final fitness (Pareto-style) for F1/F2/F5."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.mpl_font import setup_cjk_font

setup_cjk_font()

PERIODIC = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "periodic_baseline_f125.json"
MAIN = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "table_f1_f6_recomputed.json"
OUT = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "comm_fitness_pareto_f125.pdf"

METHOD_STYLE = {
    "Full": {"label": "RL gated", "marker": "o", "color": "#1b7837", "zorder": 5},
    "PeriodicK2": {"label": "Periodic-2", "marker": "s", "color": "#762a83", "zorder": 3},
    "PeriodicK3": {"label": "Periodic-3", "marker": "^", "color": "#9970ab", "zorder": 3},
    "PeriodicK5": {"label": "Periodic-5", "marker": "D", "color": "#c2a5cf", "zorder": 3},
}


def main() -> None:
    periodic = json.loads(PERIODIC.read_text(encoding="utf-8"))
    main_tbl = json.loads(MAIN.read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=False)
    funcs = ["F1", "F2", "F5"]

    for ax, func in zip(axes, funcs):
        pts = [r for r in periodic if r["func"] == func]
        for row in pts:
            st = METHOD_STYLE.get(row["method"], {"label": row["method"], "marker": "x", "color": "gray", "zorder": 2})
            ax.scatter(
                100 * row["comm_rate_mean"],
                row["final_fitness_mean"],
                s=55,
                marker=st["marker"],
                c=st["color"],
                label=st["label"],
                zorder=st["zorder"],
                edgecolors="black",
                linewidths=0.4,
            )
        rl = main_tbl["functions"][func]["LLSO"]["RL-MACPO"]["mean"]
        ax.scatter(
            20.8 if func != "F5" else 8.3,
            rl,
            s=90,
            marker="*",
            c="#1b7837",
            label="RL gated (25-run main)",
            zorder=6,
            edgecolors="black",
            linewidths=0.5,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Communication rate (\\%)")
        ax.set_ylabel("Final $F$ (mean)")
        ax.set_title(func)
        ax.grid(True, which="both", alpha=0.25, linestyle="--")

    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.02), fontsize=8)
    fig.suptitle("Communication--fitness trade-off (F1/F2/F5)", y=1.02, fontsize=11)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
