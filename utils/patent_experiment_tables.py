#!/usr/bin/env python3
"""专利说明书表格数据：从配对实验 json 与消融 csv 加载（不含 IEEE 算例）。"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAIRED_JSON = ROOT / "patent_supplement" / "paired_experiment_data.json"
GATE_CSV = (
    ROOT
    / "ablation_experiments"
    / "results"
    / "gate_mechanism_minimal"
    / "gate_mechanism_minimal_10runs_summary.csv"
)
FITNESS_CSV = ROOT / "ablation_experiments" / "results" / "补做实验_25runs" / "fitness_summary.csv"

# 写入专利正文及意见陈述的配对场景（不含 IEEE；MAED2 仅作研发参考，不写入专利）
PATENT_SCENARIOS: list[tuple[str, str]] = [
    ("MAED13", "多区域阀点经济调度(13机,1800MW)"),
    ("RESOURCE", "资源约束型分布式调度"),
    ("EVDISPATCH", "电动汽车充放电协同调度"),
]

GATE_LABELS = {
    "V0_AlwaysOn": "每轮必通信（基线）",
    "V1_FixedThreshold": "仅固定阈值（无fail-safe）",
    "V2_RelativeThreshold": "相对阈值",
    "V3_RelativeThresholdFailSafe": "相对阈值+fail-safe（本发明）",
}

COMPONENT_PICK = [
    ("MACPO_baseline", "原始MACPO基线"),
    ("MACPO2_Layer1", "仅加RL惩罚调节"),
    ("MACPO2_Layer1_2", "+自适应阈值门控"),
    ("MACPO2_Full_S5", "三层门控全开"),
    ("MACPO2_NoSelection", "关闭变量筛选"),
    ("MACPO2_WithSelection_0.9_0.7_0.5", "Top-R筛选(0.9/0.7/0.5)"),
]


def fmt_pct(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}%"


def fmt_pure_target_change_pct(imp: float | None) -> str:
    """纯目标变化（RL 相对 MACPO 改善%）：|变化|<1% 保留两位小数，否则一位小数。"""
    if imp is None:
        return "—"
    if abs(imp) < 1.0:
        return f"{imp:.2f}%"
    return f"{imp:.1f}%"

def fmt_num(v: float | None) -> str:
    if v is None:
        return "—"
    av = abs(v)
    if av >= 1e6 or (0 < av < 0.01 and v != 0):
        return f"{v:.4e}"
    if av >= 100:
        return f"{v:.2f}"
    return f"{v:.4f}"


def load_paired_json() -> dict[str, Any]:
    if not PAIRED_JSON.exists():
        raise FileNotFoundError(f"缺少配对数据：{PAIRED_JSON}，请先运行 utils/patent_reply_materials.py")
    return json.loads(PAIRED_JSON.read_text(encoding="utf-8"))


def paired_table_rows() -> tuple[list[str], list[list[str]]]:
    data = load_paired_json()
    headers = [
        "场景",
        "重复次数",
        "MACPO通信率",
        "本发明通信率",
        "通信降幅",
        "MACPO最优纯目标",
        "本发明最优纯目标",
        "纯目标变化",
        "评估次数",
    ]
    rows: list[list[str]] = []
    for key, label in PATENT_SCENARIOS:
        if key not in data:
            continue
        s = data[key]
        imp = s.get("best_f_pure_improvement_pct")
        imp_s = fmt_pure_target_change_pct(imp)
        rows.append(
            [
                label,
                str(s.get("runs", "—")),
                fmt_pct((s.get("macpo_comm_rate") or 0) * 100),
                fmt_pct((s.get("rl_comm_rate") or 0) * 100),
                fmt_pct(s.get("comm_reduction_pct")),
                fmt_num(s.get("macpo_best_f_pure")),
                fmt_num(s.get("rl_best_f_pure")),
                imp_s,
                fmt_num(s.get("macpo_eva")),
            ]
        )
    return headers, rows


def gate_table_rows() -> tuple[list[str], list[list[str]]]:
    if not GATE_CSV.exists():
        return [], []
    headers = ["门控配置", "通信率", "通信降幅", "F5适应度均值", "零通信运行数"]
    rows: list[list[str]] = []
    with GATE_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ver = row["version"]
            rows.append(
                [
                    GATE_LABELS.get(ver, ver),
                    fmt_pct(float(row["comm_rate_mean"]) * 100),
                    fmt_pct(float(row["comm_reduction_pct"])),
                    fmt_num(float(row["final_fitness_mean"])),
                    row["zero_comm_runs"],
                ]
            )
    return headers, rows


def component_table_rows() -> tuple[list[str], list[list[str]]]:
    if not FITNESS_CSV.exists():
        return [], []
    by_name: dict[str, dict[str, str]] = {}
    with FITNESS_CSV.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            by_name[row["配置名"]] = row
    headers = ["配置", "F5纯目标均值", "F5标准差"]
    rows: list[list[str]] = []
    for key, label in COMPONENT_PICK:
        if key not in by_name:
            continue
        r = by_name[key]
        rows.append([label, fmt_num(float(r["F5_mean"])), fmt_num(float(r["F5_std"]))])
    return headers, rows


def table_rows_to_text(headers: list[str], rows: list[list[str]]) -> str:
    """将表格内容转为正文段落备份（防止仅读取段落时表体缺失）。"""
    lines = ["表头：" + "；".join(headers)]
    for i, row in enumerate(rows, 1):
        cells = [f"{h}={v}" for h, v in zip(headers, row)]
        lines.append(f"第{i}行：" + "；".join(cells))
    return "\n".join(lines)
