#!/usr/bin/env python3
"""Patch Table I GFPDO$^{dagger}$ cells in conference_new_ready.tex from 25-run batch."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.external_baselines import GFPDO_CSO, GFPDO_LLSO  # noqa: E402
from utils.ndo_run_stats import fmt_sci_tex  # noqa: E402

TEX = _REPO / "RL_MACPO_IEEE_English_with_images" / "conference_new_ready.tex"
OUT_JSON = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "gfpdo_f1_f6_25runs.json"

_GFPDO_LLSO_COL = 2
_GFPDO_CSO_COL = 7
_METRICS = ("mean", "median", "std")


def _replace_cell(line: str, col: int, new_val: str) -> str:
    parts = line.split("&")
    if len(parts) <= col:
        raise ValueError(f"Unexpected table row ({len(parts)} columns): {line[:80]!r}")
    parts[col] = f" {new_val} "
    return "&".join(parts)


def patch_block(
    tex: str,
    fn: str,
    llso: tuple[str, str, str],
    cso: tuple[str, str, str],
) -> str:
    values_llso = dict(zip(_METRICS, llso))
    values_cso = dict(zip(_METRICS, cso))
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
                line = _replace_cell(line, _GFPDO_LLSO_COL, values_llso[metric])
                line = _replace_cell(line, _GFPDO_CSO_COL, values_cso[metric])
                break
        body_lines.append(line)

    new_block = "\\multirow{4}{*}{" + fn + "}\n" + "\n".join(body_lines) + "\n" + m.group(2)
    return tex[: m.start()] + new_block + tex[m.end() :]


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            {
                "source": str(_REPO / "MACPO_sourcecode" / "output_baselines_gfpdo_25runs"),
                "LLSO": {k: list(v) for k, v in GFPDO_LLSO.items()},
                "CSO": {k: list(v) for k, v in GFPDO_CSO.items()},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    tex = TEX.read_text(encoding="utf-8")
    for fn in [f"F{i}" for i in range(1, 7)]:
        lm, ld, ls = GFPDO_LLSO[fn]
        cm, cd, cs = GFPDO_CSO[fn]
        tex = patch_block(
            tex,
            fn,
            (fmt_sci_tex(lm), fmt_sci_tex(ld), fmt_sci_tex(ls)),
            (fmt_sci_tex(cm), fmt_sci_tex(cd), fmt_sci_tex(cs)),
        )

    tex = tex.replace(
        r"\textbf{GFPDO$^{\dagger}$}: one-run pilot per function under the MACPO GFPDO executable; ",
        r"\textbf{GFPDO$^{\dagger}$}: 25-run batch under the MACPO GFPDO executable (same evaluation budget); ",
    )

    TEX.write_text(tex, encoding="utf-8")
    print(f"Patched GFPDO in {TEX}")
    print(f"Wrote {OUT_JSON}")
    for fn in [f"F{i}" for i in range(1, 7)]:
        m, med, s = GFPDO_LLSO[fn]
        print(f"  {fn} LLSO: mean={fmt_sci_tex(m)} median={fmt_sci_tex(med)} std={fmt_sci_tex(s)}")


if __name__ == "__main__":
    main()
