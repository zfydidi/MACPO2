#!/usr/bin/env python3
"""Export CI-bin trigger statistics to JSON for paper tables."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from utils.ci_bin_trigger import analyze_function_dir  # noqa: E402

DEFAULT_OUT = _REPO / "RL_MACPO_IEEE_English_with_images" / "media" / "ci_bin_trigger_F1_F6.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--runs-dir",
        type=Path,
        default=_REPO / "experiments/patent_paired_comparison/raw/RL-MACPO",
    )
    ap.add_argument("--functions", nargs="+", default=[f"F{i}" for i in range(1, 7)])
    ap.add_argument("--n-bins", type=int, default=5)
    ap.add_argument("--exclude-iter0", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload: dict = {
        "runs_dir": str(args.runs_dir.resolve()),
        "n_bins": args.n_bins,
        "exclude_iter0": args.exclude_iter0,
        "functions": {},
    }
    for fn in args.functions:
        res = analyze_function_dir(
            args.runs_dir,
            fn,
            n_bins=args.n_bins,
            exclude_iter0=args.exclude_iter0,
        )
        payload["functions"][fn] = {
            "n_runs": res.n_runs,
            "n_points": res.n_points,
            "spearman_rho": res.spearman_rho,
            "bins": [
                {
                    "quantile": f"Q{b + 1}",
                    "conflict_lo": None if not res.conflict_lo[b] == res.conflict_lo[b] else float(res.conflict_lo[b]),
                    "conflict_hi": None if not res.conflict_hi[b] == res.conflict_hi[b] else float(res.conflict_hi[b]),
                    "trigger_prob": float(res.trigger_prob[b]),
                    "trigger_std": float(res.std_trigger[b]),
                    "count": int(res.count[b]),
                }
                for b in range(res.n_bins)
            ],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
