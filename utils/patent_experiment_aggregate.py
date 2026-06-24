#!/usr/bin/env python3
"""聚合专利配对仿真实验结果（MACPO baseline vs RL-MACPO Full）。

读取 experiments/patent_paired_comparison/raw/ 下的运行日志，输出 summary.json / summary.csv。
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXP_DIR = ROOT / "experiments" / "patent_paired_comparison"


def parse_macpo_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = [ln.split() for ln in text.splitlines() if ln and not ln.startswith("#")]
    if not rows:
        raise ValueError(f"no data rows: {path}")
    last = rows[-1]
    done = re.search(
        r"# Completed \[MACPO_LLSO\]: iterations=(\d+), evals=([0-9.eE+-]+), "
        r"final fitness=([0-9.eE+-]+), total time=([0-9.eE+-]+)s",
        text,
    )
    return {
        "algorithm": "MACPO",
        "f_pure": float(last[3]),
        "f_penalty": float(last[2]),
        "conflict": float(last[7]),
        "wall_s": float(done.group(4)) if done else None,
        "total_evals": int(float(done.group(2))) if done else None,
        "comm_rate": 1.0,
        "avg_nego_dims": None,
        "rl_updates": 0,
        "enter_negotiation_count": None,
        "fail_safe_fire_count": None,
        "ok": done is not None,
    }


def _parse_cost_stats(text: str) -> dict[str, Any] | None:
    if "# COST_STATS" not in text:
        return None

    def grab(key: str) -> float | None:
        m = re.search(rf"{key}=([0-9.eE+-]+)", text)
        return float(m.group(1)) if m else None

    comm_rate = grab("comm_rate")
    if comm_rate is None:
        return None
    return {
        "comm_rate": comm_rate,
        "avg_nego_dims": grab("avg_nego_dims"),
        "rl_updates": grab("rl_updates"),
        "wall_s": grab("total_time_ms") / 1000.0 if grab("total_time_ms") is not None else None,
        "enter_negotiation_count": int(grab("enter_negotiation_count"))
        if grab("enter_negotiation_count") is not None
        else None,
        "fail_safe_fire_count": int(grab("fail_safe_fire_count"))
        if grab("fail_safe_fire_count") is not None
        else None,
    }


def parse_rl_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = [ln.split("\t") for ln in text.splitlines() if ln and not ln.startswith("#") and "\t" in ln]
    if not rows:
        raise ValueError(f"no tab data rows: {path}")
    last = rows[-1]
    cost = _parse_cost_stats(text)
    done = re.search(r"Completed \[LLSO\]:.*?evals=([0-9.eE+-]+)", text)
    # 使用全程最优纯目标 f_pure_bsf（最后一列），若无则退化为末行 f_pure
    f_pure = float(last[-1]) if len(last) >= 19 else float(last[3])
    return {
        "algorithm": "RL-MACPO",
        "f_pure": f_pure,
        "f_penalty": float(last[2]),
        "conflict": float(last[7]),
        "wall_s": cost["wall_s"] if cost else None,
        "total_evals": int(float(done.group(1))) if done else int(float(last[1])),
        "comm_rate": cost["comm_rate"] if cost else None,
        "avg_nego_dims": cost["avg_nego_dims"] if cost else None,
        "rl_updates": cost["rl_updates"] if cost else None,
        "enter_negotiation_count": cost["enter_negotiation_count"] if cost else None,
        "fail_safe_fire_count": cost["fail_safe_fire_count"] if cost else None,
        "ok": cost is not None,
    }


def mean_std(xs: list[float]) -> tuple[float | None, float | None]:
    if not xs:
        return None, None
    if len(xs) == 1:
        return xs[0], 0.0
    return statistics.mean(xs), statistics.pstdev(xs)


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("ok")]
    keys = ["f_pure", "f_penalty", "conflict", "wall_s", "comm_rate", "avg_nego_dims", "total_evals"]
    out: dict[str, Any] = {"n": len(ok_rows), "n_total": len(rows)}
    for k in keys:
        vals = [float(r[k]) for r in ok_rows if r.get(k) is not None]
        m, s = mean_std(vals)
        out[f"{k}_mean"] = m
        out[f"{k}_std"] = s
    return out


def load_experiment(exp_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = exp_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    raw = exp_dir / "raw"
    rows: list[dict[str, Any]] = []

    for algo, parser in [("MACPO", parse_macpo_log), ("RL-MACPO", parse_rl_log)]:
        algo_dir = raw / algo
        if not algo_dir.exists():
            continue
        for path in sorted(algo_dir.glob("*.txt")):
            m = re.match(r"^(F\d+)_run(\d+)\.txt$", path.name)
            if not m:
                continue
            func, run_id = m.group(1), int(m.group(2))
            row: dict[str, Any] = {
                "func": func,
                "run_id": run_id,
                "file": str(path.relative_to(ROOT)),
            }
            try:
                row.update(parser(path))
            except (ValueError, IndexError) as e:
                row.update({"algorithm": algo, "ok": False, "error": str(e)})
            rows.append(row)

    by_func: dict[str, Any] = {}
    for func in sorted({r["func"] for r in rows}):
        macpo = [r for r in rows if r["func"] == func and r.get("algorithm") == "MACPO"]
        rl = [r for r in rows if r["func"] == func and r.get("algorithm") == "RL-MACPO"]
        m_agg = aggregate_rows(macpo)
        r_agg = aggregate_rows(rl)
        imp = None
        if m_agg.get("f_pure_mean") and r_agg.get("f_pure_mean") and m_agg["f_pure_mean"] > 0:
            imp = (m_agg["f_pure_mean"] - r_agg["f_pure_mean"]) / m_agg["f_pure_mean"] * 100.0
        comm_red = None
        if m_agg.get("comm_rate_mean") is not None and r_agg.get("comm_rate_mean") is not None:
            base = m_agg["comm_rate_mean"]
            comm_red = (base - r_agg["comm_rate_mean"]) / base * 100.0 if base > 0 else None
        wall_red = None
        if m_agg.get("wall_s_mean") and r_agg.get("wall_s_mean") and m_agg["wall_s_mean"] > 0:
            wall_red = (m_agg["wall_s_mean"] - r_agg["wall_s_mean"]) / m_agg["wall_s_mean"] * 100.0
        by_func[func] = {
            "MACPO": m_agg,
            "RL-MACPO": r_agg,
            "f_pure_improvement_pct": imp,
            "comm_reduction_pct": comm_red,
            "wall_time_reduction_pct": wall_red,
        }

    overall = {
        "MACPO": aggregate_rows([r for r in rows if r.get("algorithm") == "MACPO"]),
        "RL-MACPO": aggregate_rows([r for r in rows if r.get("algorithm") == "RL-MACPO"]),
    }
    if overall["MACPO"].get("comm_rate_mean") is not None and overall["RL-MACPO"].get("comm_rate_mean") is not None:
        base = overall["MACPO"]["comm_rate_mean"]
        overall["comm_reduction_pct"] = (
            (base - overall["RL-MACPO"]["comm_rate_mean"]) / base * 100.0 if base > 0 else None
        )
    if overall["MACPO"].get("wall_s_mean") and overall["RL-MACPO"].get("wall_s_mean"):
        overall["wall_time_reduction_pct"] = (
            (overall["MACPO"]["wall_s_mean"] - overall["RL-MACPO"]["wall_s_mean"])
            / overall["MACPO"]["wall_s_mean"]
            * 100.0
        )
    if overall["MACPO"].get("f_pure_mean") and overall["RL-MACPO"].get("f_pure_mean"):
        overall["f_pure_improvement_pct"] = (
            (overall["MACPO"]["f_pure_mean"] - overall["RL-MACPO"]["f_pure_mean"])
            / overall["MACPO"]["f_pure_mean"]
            * 100.0
        )

    summary = {"manifest": manifest, "by_function": by_func, "overall": overall, "rows": rows}
    return rows, summary


def write_summary(exp_dir: Path, summary: dict[str, Any]) -> None:
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    csv_path = exp_dir / "summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "func",
                "macpo_f_pure_mean",
                "rl_f_pure_mean",
                "f_pure_improvement_pct",
                "macpo_comm_rate",
                "rl_comm_rate",
                "comm_reduction_pct",
                "macpo_wall_s",
                "rl_wall_s",
                "wall_reduction_pct",
            ]
        )
        for func, data in summary["by_function"].items():
            m = data["MACPO"]
            r = data["RL-MACPO"]
            w.writerow(
                [
                    func,
                    m.get("f_pure_mean"),
                    r.get("f_pure_mean"),
                    data.get("f_pure_improvement_pct"),
                    m.get("comm_rate_mean"),
                    r.get("comm_rate_mean"),
                    data.get("comm_reduction_pct"),
                    m.get("wall_s_mean"),
                    r.get("wall_s_mean"),
                    data.get("wall_time_reduction_pct"),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="聚合专利配对仿真实验")
    parser.add_argument("--exp-dir", type=Path, default=DEFAULT_EXP_DIR)
    args = parser.parse_args()
    _, summary = load_experiment(args.exp_dir)
    write_summary(args.exp_dir, summary)
    print(json.dumps(summary["overall"], indent=2, ensure_ascii=False))
    print(f"[OK] 写入 {args.exp_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
