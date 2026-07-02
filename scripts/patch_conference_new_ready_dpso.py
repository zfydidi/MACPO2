#!/usr/bin/env python3
"""Patch Table I LLSO DPSO$^{dagger}$ cells in conference_new_ready.tex from unified 25-run batch."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.ndo_run_stats import fmt_sci_tex  # noqa: E402

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_new_ready.tex"
SUMMARY = (
    _REPO
    / "ablation_experiments"
    / "results"
    / "external_baselines_25runs_unified"
    / "summary.json"
)
OUT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "dpso_f1_f6_25runs.json"

# mean/median/std rows: col 3 (1-based) is LLSO DPSO after GFPDO.
_DPSO_LLSO_COL = 3
_METRICS = ("mean", "median", "std")


def load_dpso_llso() -> dict[str, tuple[float, float, float]]:
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    out: dict[str, tuple[float, float, float]] = {}
    for fn in [f"F{i}" for i in range(1, 7)]:
        s = data["summary"]["DPSO"][fn]
        out[fn] = (s["mean"], s["median"], s["std"])
    return out


def _replace_dpso_cell(line: str, new_val: str) -> str:
    parts = line.split("&")
    if len(parts) <= _DPSO_LLSO_COL:
        raise ValueError(f"Unexpected table row ({len(parts)} columns): {line[:80]!r}")
    parts[_DPSO_LLSO_COL] = f" {new_val} "
    return "&".join(parts)


def patch_block(tex: str, fn: str, mean: str, median: str, std: str) -> str:
    values = {"mean": mean, "median": median, "std": std}
    block_re = re.compile(
        r"\\multirow\{4\}\{\*\}\{" + re.escape(fn) + r"\}\n(.*?)(\\midrule)",
        re.DOTALL,
    )
    m = block_re.search(tex)
    if not m:
        raise SystemExit(f"Could not locate {fn} block in {TEX}")

    body_lines: list[str] = []
    for line in m.group(1).splitlines():
        stripped = line.lstrip()
        for metric in _METRICS:
            if stripped.startswith(f"& {metric}") or stripped.startswith(f"{metric}"):
                line = _replace_dpso_cell(line, values[metric])
                break
        body_lines.append(line)

    new_block = "\\multirow{4}{*}{" + fn + "}\n" + "\n".join(body_lines) + "\n" + m.group(2)
    return tex[: m.start()] + new_block + tex[m.end() :]


def main() -> None:
    if not SUMMARY.is_file():
        raise SystemExit(f"Missing DPSO summary: {SUMMARY}")

    dpso = load_dpso_llso()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"source": str(SUMMARY), "LLSO": {k: list(v) for k, v in dpso.items()}}, indent=2),
        encoding="utf-8",
    )

    tex = TEX.read_text(encoding="utf-8")
    for fn, (mean_v, med_v, std_v) in dpso.items():
        tex = patch_block(tex, fn, fmt_sci_tex(mean_v), fmt_sci_tex(med_v), fmt_sci_tex(std_v))

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched LLSO DPSO in {TEX}")
    print(f"Wrote {OUT_JSON}")
    for fn, (mean_v, med_v, std_v) in dpso.items():
        print(f"  {fn}: mean={fmt_sci_tex(mean_v)} median={fmt_sci_tex(med_v)} std={fmt_sci_tex(std_v)}")


if __name__ == "__main__":
    main()
