#!/usr/bin/env python3
"""从 MATPOWER case*.m 生成 IEEE 区域互联经济调度 C++ 数据头文件。

变量编码（与 PowerGridBenchmarks 一致）:
  dim 0..G-1       — 各发电机有功出力 P_G
  dim G..G+T-1     — 区域间联络线功率 P_tie（共享维）

分区策略: 按母线 area 字段聚合为 K 个区域（可指定 K），割边为联络线。
"""
from __future__ import annotations

import re
import textwrap
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "power_dispatch_sim" / "scenarios" / "power_grid" / "generated"

MATPOWER_RAW = "https://raw.githubusercontent.com/MATPOWER/matpower/master/data/{name}.m"

# IEEE14 沿用项目既有 4 区划分（与 ieee14bus_data.h 一致）
IEEE14_MANUAL = {
    "n_regions": 4,
    "region_buses": [
        [1, 2, 5],
        [3, 4],
        [6, 11, 12, 13],
        [7, 8, 9, 10, 14],
    ],
    "tie_pairs": [(0, 1), (0, 2), (1, 3), (2, 3)],
}


def fetch_case(name: str) -> str:
    url = MATPOWER_RAW.format(name=name)
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse_matrix_block(text: str, field: str) -> list[list[float]]:
    pat = re.compile(rf"mpc\.{field}\s*=\s*\[", re.MULTILINE)
    m = pat.search(text)
    if not m:
        raise ValueError(f"Cannot find mpc.{field}")
    start = m.end()
    rows: list[list[float]] = []
    buf: list[str] = []
    for line in text[start:].splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        if s.endswith("];"):
            buf.append(s[:-2].strip())
            if buf:
                row = [float(x) for x in " ".join(buf).replace(";", " ").split()]
                if row:
                    rows.append(row)
            break
        if ";" in s:
            parts = s.split(";")
            for p in parts[:-1]:
                p = p.strip()
                if p:
                    row = [float(x) for x in p.split()]
                    if row:
                        rows.append(row)
            tail = parts[-1].strip()
            if tail and not tail.startswith("]"):
                buf = [tail]
            else:
                buf = []
        else:
            buf.append(s)
    return rows


def parse_gencost_quad(text: str, n_gen: int) -> list[tuple[float, float, float]]:
    """返回 (a, b, c) 二次成本系数；无 gencost 时用默认."""
    try:
        rows = parse_matrix_block(text, "gencost")
    except ValueError:
        return [(0.01, 40.0, 0.0)] * n_gen
    out = []
    for i, row in enumerate(rows[:n_gen]):
        if not row:
            out.append((0.01, 40.0, 0.0))
            continue
        if int(row[0]) == 2 and len(row) >= 7:
            # model 2: n, c(n-1)...c0 → 二次 n=3 → c2,c1,c0
            c2, c1, c0 = row[-3], row[-2], row[-1]
            out.append((c2, c1, c0))
        else:
            out.append((0.01, 40.0, 0.0))
    while len(out) < n_gen:
        out.append((0.01, 40.0, 0.0))
    return out


def build_adj(branches: list[list[float]], n_bus: int) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = {i: set() for i in range(1, n_bus + 1)}
    for br in branches:
        if br[10] <= 0:
            continue
        f, t = int(br[0]), int(br[1])
        adj[f].add(t)
        adj[t].add(f)
    return adj


def _bfs_dist(adj: dict[int, set[int]], src: int) -> dict[int, int]:
    dist = {src: 0}
    q = [src]
    for u in q:
        for v in adj.get(u, ()):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def partition_graph(
    buses: list[list[float]],
    branches: list[list[float]],
    gens: list[list[float]],
    n_regions: int,
) -> dict[int, int]:
    """K 路图划分：以发电机母线为种子，多源 BFS 赋区域，再按负荷微调."""
    n_bus = len(buses)
    adj = build_adj(branches, n_bus)

    gen_buses = sorted({int(g[0]) for g in gens if g[7] > 0})
    if not gen_buses:
        gen_buses = [int(buses[0][0])]

    # 选种子：贪心最大化种子间最短路径距离
    seeds = [gen_buses[0]]
    while len(seeds) < n_regions and len(seeds) < len(gen_buses):
        best_b, best_score = None, -1
        for b in gen_buses:
            if b in seeds:
                continue
            d = _bfs_dist(adj, b)
            score = min(d.get(s, 10**9) for s in seeds)
            if score > best_score:
                best_score, best_b = score, b
        if best_b is None:
            break
        seeds.append(best_b)
    while len(seeds) < n_regions:
        seeds.append(gen_buses[len(seeds) % len(gen_buses)])

    # 多源 BFS：每个母线归属最近种子
    bus_region: dict[int, int] = {}
    all_buses = [int(b[0]) for b in buses]
    for bus_i in all_buses:
        best_r, best_d = 0, 10**9
        for r, s in enumerate(seeds):
            d = _bfs_dist(adj, s).get(bus_i, 10**9)
            if d < best_d:
                best_d, best_r = d, r
        bus_region[bus_i] = best_r

    # 负荷平衡：尝试将边界母线换到邻区以降低不平衡
    demand = {int(b[0]): b[2] for b in buses}
    region_load = [0.0] * n_regions
    for bus_i, r in bus_region.items():
        region_load[r] += demand.get(bus_i, 0.0)

    for _ in range(3 * n_bus):
        moved = False
        for bus_i in all_buses:
            r = bus_region[bus_i]
            load_r = region_load[r]
            target = max(range(n_regions), key=lambda x: region_load[x])
            if target == r:
                continue
            if load_r + 1e-6 < region_load[target]:
                continue
            # 仅当与目标区域有邻接时才迁移
            neighbors = adj.get(bus_i, set())
            neighbor_regions = {bus_region.get(nb) for nb in neighbors}
            if target not in neighbor_regions:
                continue
            d = demand.get(bus_i, 0.0)
            if region_load[r] - d >= region_load[target] + d:
                bus_region[bus_i] = target
                region_load[r] -= d
                region_load[target] += d
                moved = True
        if not moved:
            break
    return bus_region


def partition_by_area(buses: list[list[float]], n_regions: int) -> dict[int, int]:
    """母线 bus_i -> region_id，按 area 聚合再合并到 n_regions."""
    bus_area = {int(b[0]): int(b[6]) for b in buses}
    areas = sorted(set(bus_area.values()))
    area_to_region: dict[int, int] = {}
    if len(areas) <= n_regions:
        for i, a in enumerate(areas):
            area_to_region[a] = i
        # 空区域用最后一个 area 填充
        next_r = len(areas)
        for a in areas:
            pass
        while next_r < n_regions:
            area_to_region[areas[next_r % len(areas)]] = next_r
            next_r += 1
    else:
        # 合并相邻 area 编号
        chunk = max(1, len(areas) // n_regions)
        for i, a in enumerate(areas):
            area_to_region[a] = min(i // chunk, n_regions - 1)
    bus_region: dict[int, int] = {}
    for bus_i, area in bus_area.items():
        bus_region[bus_i] = area_to_region.get(area, 0)
    return bus_region


def partition_manual(region_buses: list[list[int]]) -> dict[int, int]:
    bus_region: dict[int, int] = {}
    for r, buses in enumerate(region_buses):
        for b in buses:
            bus_region[b] = r
    return bus_region


def ensure_regions_have_generators(
    bus_region: dict[int, int],
    buses: list[list[float]],
    branches: list[list[float]],
    gens: list[list[float]],
    n_regions: int,
) -> dict[int, int]:
    """将无发电机区域中的母线并入邻区，避免出现空 MPI 分区与虚假平衡罚。"""
    n_bus = len(buses)
    adj = build_adj(branches, n_bus)

    def gen_count_by_region() -> list[int]:
        counts = [0] * n_regions
        for g in gens:
            if g[7] <= 0:
                continue
            bus_i = int(g[0])
            counts[bus_region.get(bus_i, 0)] += 1
        return counts

    changed = True
    while changed:
        changed = False
        counts = gen_count_by_region()
        for r in range(n_regions):
            if counts[r] > 0:
                continue
            buses_in_r = [int(b[0]) for b in buses if bus_region.get(int(b[0])) == r]
            if not buses_in_r:
                continue
            target = None
            for bus_i in buses_in_r:
                for nb in adj.get(bus_i, ()):
                    tr = bus_region.get(nb)
                    if tr is not None and tr != r and counts[tr] > 0:
                        target = tr
                        break
                if target is not None:
                    break
            if target is None:
                for tr in range(n_regions):
                    if tr != r and counts[tr] > 0:
                        target = tr
                        break
            if target is None:
                continue
            for bus_i in buses_in_r:
                bus_region[bus_i] = target
            changed = True
    return bus_region


def compact_empty_regions(layout: dict) -> dict:
    """删除仍无本地变量的区域并重编号（防御性）。"""
    n_regions = layout["n_regions"]
    region_dims = layout["region_dims"]
    empty = [r for r in range(n_regions) if len(region_dims[r]) == 0]
    if not empty:
        return layout

    keep = [r for r in range(n_regions) if r not in empty]
    remap = {old: new for new, old in enumerate(keep)}
    new_n = len(keep)

    def remap_region(r: int) -> int:
        return remap.get(r, keep[0])

    new_gens = []
    for g in layout["gens"]:
        ng = dict(g)
        ng["region"] = remap_region(g["region"])
        new_gens.append(ng)

    new_ties = []
    for t in layout["ties"]:
        new_ties.append({
            "global_dim": t["global_dim"],
            "from": remap_region(t["from"]),
            "to": remap_region(t["to"]),
            "pmax": t.get("pmax", 200.0),
        })

    new_region_dims: list[list[int]] = [[] for _ in range(new_n)]
    for g in new_gens:
        new_region_dims[g["region"]].append(g["idx"])
    for t in new_ties:
        new_region_dims[t["from"]].append(t["global_dim"])
        new_region_dims[t["to"]].append(t["global_dim"])

    new_region_demand = [0.0] * new_n
    for old_r, new_r in remap.items():
        new_region_demand[new_r] += layout["region_demand"][old_r]

    new_overlap: list[list[int]] = [[] for _ in range(new_n)]
    for t in new_ties:
        a, b = t["from"], t["to"]
        if b not in new_overlap[a]:
            new_overlap[a].append(b)
        if a not in new_overlap[b]:
            new_overlap[b].append(a)

    layout = dict(layout)
    layout.update({
        "n_regions": new_n,
        "gens": new_gens,
        "ties": new_ties,
        "region_dims": new_region_dims,
        "region_demand": new_region_demand,
        "overlap_groups": new_overlap,
    })
    return layout


def compute_layout(
    case_name: str,
    buses: list[list[float]],
    gens: list[list[float]],
    branches: list[list[float]],
    costs: list[tuple[float, float, float]],
    n_regions: int,
    manual: dict | None = None,
) -> dict:
    n_bus = len(buses)
    if manual:
        bus_region = partition_manual(manual["region_buses"])
        n_regions = manual["n_regions"]
        tie_pairs = manual.get("tie_pairs")
    else:
        areas = set(int(b[6]) for b in buses)
        if len(areas) >= n_regions:
            bus_region = partition_by_area(buses, n_regions)
        else:
            bus_region = partition_graph(buses, branches, gens, n_regions)
        tie_pairs = None

    bus_region = ensure_regions_have_generators(
        bus_region, buses, branches, gens, n_regions
    )

    active_gens = []
    for i, g in enumerate(gens):
        if g[7] <= 0:
            continue
        bus_i = int(g[0])
        active_gens.append({
            "idx": len(active_gens),
            "bus_id": bus_i,
            "pmax": g[8],
            "pmin": g[9],
            "a": costs[i][0],
            "b": costs[i][1],
            "c": costs[i][2],
            "region": bus_region.get(bus_i, 0),
        })

    region_demand = [0.0] * n_regions
    for b in buses:
        bus_i = int(b[0])
        r = bus_region.get(bus_i, 0)
        region_demand[r] += b[2]

    # 区域对之间的联络线（割边聚合）及额定容量
    pair_edges: dict[tuple[int, int], int] = defaultdict(int)
    pair_capacity: dict[tuple[int, int], float] = defaultdict(float)
    for br in branches:
        if br[10] <= 0:
            continue
        f, t = int(br[0]), int(br[1])
        rf, rt = bus_region.get(f, 0), bus_region.get(t, 0)
        if rf == rt:
            continue
        key = (min(rf, rt), max(rf, rt))
        pair_edges[key] += 1
        rate_a = br[5] if len(br) > 5 and br[5] > 0 else 0.0
        if rate_a <= 0:
            rate_a = 100.0
        pair_capacity[key] += rate_a

    if tie_pairs is not None:
        tie_list = [{"from": a, "to": b} for a, b in tie_pairs]
    else:
        tie_list = [{"from": k[0], "to": k[1]} for k in sorted(pair_edges)]

    n_gens = len(active_gens)
    n_ties = len(tie_list)
    total_dim = n_gens + n_ties

    # 区域本地维: 发电机 dim + 联络线 dim
    region_dims: list[list[int]] = [[] for _ in range(n_regions)]
    for g in active_gens:
        region_dims[g["region"]].append(g["idx"])

    tie_global: list[dict] = []
    for t_i, tl in enumerate(tie_list):
        gdim = n_gens + t_i
        key = (min(tl["from"], tl["to"]), max(tl["from"], tl["to"]))
        cap = pair_capacity.get(key, 0.0)
        if cap <= 0:
            cap = 200.0
        tie_global.append({
            "global_dim": gdim,
            "from": tl["from"],
            "to": tl["to"],
            "pmax": cap,
        })
        region_dims[tl["from"]].append(gdim)
        region_dims[tl["to"]].append(gdim)

    overlap_groups: list[list[int]] = [[] for _ in range(n_regions)]
    for t in tie_global:
        a, b = t["from"], t["to"]
        if b not in overlap_groups[a]:
            overlap_groups[a].append(b)
        if a not in overlap_groups[b]:
            overlap_groups[b].append(a)

    pmax_all = max((g["pmax"] for g in active_gens), default=100.0)
    tie_cap_default = 200.0
    tie_max = max((t.get("pmax", tie_cap_default) for t in tie_global), default=tie_cap_default)
    layout = {
        "case_name": case_name,
        "n_bus": n_bus,
        "n_regions": n_regions,
        "n_gens": n_gens,
        "n_ties": n_ties,
        "total_dim": total_dim,
        "gens": active_gens,
        "ties": tie_global,
        "region_demand": region_demand,
        "region_dims": region_dims,
        "overlap_groups": overlap_groups,
        "min_x": -max(tie_cap_default, tie_max),
        "max_x": pmax_all,
        "total_demand": sum(region_demand),
    }
    return compact_empty_regions(layout)


def validate_layout(layout: dict) -> None:
    """每个 MPI 分区至少拥有一台发电机决策维，避免空 rank 导致 globalBest 报告退化。"""
    n_gens = layout["n_gens"]
    for r, dims in enumerate(layout["region_dims"]):
        gen_dims = [d for d in dims if d < n_gens]
        if not gen_dims:
            raise ValueError(
                f"{layout['case_name']}: region {r} has no generator dims (dims={dims})"
            )


def emit_header(layout: dict, guard: str) -> str:
    cn = layout["case_name"]
    prefix = cn.lower().replace("-", "")
    lines = [
        f"// AUTO-GENERATED by utils/ieee_grid_codegen.py — {cn}",
        f"// MATPOWER standard case; regional economic dispatch (continuous ED, not UC).",
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        '#include "../ieee_grid_types.h"',
        "",
        f"#define {prefix.upper()}_NUM_BUSES {layout['n_bus']}",
        f"#define {prefix.upper()}_NUM_REGIONS {layout['n_regions']}",
        f"#define {prefix.upper()}_NUM_GENERATORS {layout['n_gens']}",
        f"#define {prefix.upper()}_NUM_TIELINES {layout['n_ties']}",
        f"#define {prefix.upper()}_TOTAL_DIM {layout['total_dim']}",
        f"static const double {prefix}_total_demand = {layout['total_demand']:.6f};",
        "",
        f"static const GenData {prefix}_generators[{prefix.upper()}_NUM_GENERATORS] = {{",
    ]
    for g in layout["gens"]:
        lines.append(
            f"    {{{g['bus_id']}, {g['pmax']:.6g}, {g['pmin']:.6g}, "
            f"{g['a']:.6g}, {g['b']:.6g}, {g['c']:.6g}}},"
        )
    lines.append("};")
    lines.append("")
    lines.append(f"static const double {prefix}_region_demand[{prefix.upper()}_NUM_REGIONS] = {{")
    lines.append("    " + ", ".join(f"{d:.6g}" for d in layout["region_demand"]))
    lines.append("};")
    lines.append("")
    max_local = max((len(d) for d in layout["region_dims"]), default=1)
    lines.append(f"static const int {prefix}_region_dim_sizes[{prefix.upper()}_NUM_REGIONS] = {{")
    lines.append("    " + ", ".join(str(len(d)) for d in layout["region_dims"]))
    lines.append("};")
    lines.append("")
    lines.append(
        f"static const int {prefix}_region_dims[{prefix.upper()}_NUM_REGIONS][{max_local}] = {{"
    )
    for dims in layout["region_dims"]:
        padded = dims + [-1] * (max_local - len(dims))
        lines.append("    {" + ", ".join(str(x) for x in padded) + "},")
    lines.append("};")
    lines.append("")
    lines.append(f"static const TieLine {prefix}_tielines[{prefix.upper()}_NUM_TIELINES] = {{")
    for t in layout["ties"]:
        lines.append(
            f"    {{{t['from']}, {t['to']}, {t['global_dim']}, {t['pmax']:.6g}}},"
        )
    lines.append("};")
    lines.append("")
    max_og = max((len(og) for og in layout["overlap_groups"]), default=1)
    lines.append(
        f"static const int {prefix}_overlap_groups[{prefix.upper()}_NUM_REGIONS][{max_og + 1}] = {{"
    )
    for og in layout["overlap_groups"]:
        padded = og + [-1] * (max_og + 1 - len(og))
        lines.append("    {" + ", ".join(str(x) for x in padded) + "},")
    lines.append("};")
    lines.append("")
    lines.append(f"static const int {prefix}_gen_region[{prefix.upper()}_NUM_GENERATORS] = {{")
    lines.append("    " + ", ".join(str(g["region"]) for g in layout["gens"]))
    lines.append("};")
    lines.append("")
    lines.append(f"static const double {prefix}_min_x = {layout['min_x']:.6g};")
    lines.append(f"static const double {prefix}_max_x = {layout['max_x']:.6g};")
    lines.append("")
    lines.append(f"#endif // {guard}")
    lines.append("")
    return "\n".join(lines)


CASES = [
    ("case14", "IEEE14", 4, IEEE14_MANUAL),
    ("case30", "IEEE30", 4, None),
    ("case57", "IEEE57", 4, None),
    ("case118", "IEEE118", 8, None),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry_entries = []
    for mat_name, label, n_regions, manual in CASES:
        print(f"[gen] {label} from {mat_name}.m ...")
        text = fetch_case(mat_name)
        buses = parse_matrix_block(text, "bus")
        gens = parse_matrix_block(text, "gen")
        branches = parse_matrix_block(text, "branch")
        costs = parse_gencost_quad(text, len(gens))
        layout = compute_layout(label, buses, gens, branches, costs, n_regions, manual)
        validate_layout(layout)
        guard = f"{label.upper()}BUS_DATA_H"
        fname = f"{label.lower()}bus_data.h"
        header = emit_header(layout, guard)
        (OUT_DIR / fname).write_text(header, encoding="utf-8")
        registry_entries.append((label, fname, layout))
        print(
            f"  -> {layout['n_regions']} regions, {layout['n_gens']} gens, "
            f"{layout['n_ties']} ties, dim={layout['total_dim']}"
        )

    # registry header
    reg_lines = [
        "// AUTO-GENERATED registry",
        '#include <cstring>',
        "",
        "#ifndef IEEE_GRID_REGISTRY_H",
        "#define IEEE_GRID_REGISTRY_H",
        "",
        '#include "ieee_grid_types.h"',
        '#include "generated/ieee14bus_data.h"',
        '#include "generated/ieee30bus_data.h"',
        '#include "generated/ieee57bus_data.h"',
        '#include "generated/ieee118bus_data.h"',
        "",
        "enum class IeeeGridCaseId { IEEE14, IEEE30, IEEE57, IEEE118, UNKNOWN };",
        "",
        "struct IeeeGridCaseDesc {",
        "    IeeeGridCaseId id;",
        "    const char* name;",
        "    const char* label;",
        "    int n_regions;",
        "    int n_gens;",
        "    int n_ties;",
        "    int total_dim;",
        "    const GenData* generators;",
        "    const double* region_demand;",
        "    const int* region_dim_sizes;",
        "    const int* region_dims;      // flat [n_regions * max_local]",
        "    int region_dims_stride;",
        "    const TieLine* tielines;",
        "    const int* overlap_groups;   // flat [n_regions * overlap_stride]",
        "    int overlap_stride;",
        "    const int* gen_region;",
        "    double min_x;",
        "    double max_x;",
        "};",
        "",
    ]

    case_specs = [
        ("IEEE14", "ieee14", "IEEE14", "IEEE 14-bus Economic Dispatch"),
        ("IEEE30", "ieee30", "IEEE30", "IEEE 30-bus Economic Dispatch"),
        ("IEEE57", "ieee57", "IEEE57", "IEEE 57-bus Economic Dispatch"),
        ("IEEE118", "ieee118", "IEEE118", "IEEE 118-bus Economic Dispatch"),
    ]
    for eid, pfx, name, label in case_specs:
        layout = next(x for x in registry_entries if x[0] == name)[2]
        ml = max(len(d) for d in layout["region_dims"])
        og = max(len(og) for og in layout["overlap_groups"]) + 1
        reg_lines.append(f"static const IeeeGridCaseDesc kCase_{name} = {{")
        reg_lines.append(f"    IeeeGridCaseId::{name},")
        reg_lines.append(f'    "{name}",')
        reg_lines.append(f'    "{label}",')
        reg_lines.append(f"    {pfx.upper()}_NUM_REGIONS,")
        reg_lines.append(f"    {pfx.upper()}_NUM_GENERATORS,")
        reg_lines.append(f"    {pfx.upper()}_NUM_TIELINES,")
        reg_lines.append(f"    {pfx.upper()}_TOTAL_DIM,")
        reg_lines.append(f"    {pfx}_generators,")
        reg_lines.append(f"    {pfx}_region_demand,")
        reg_lines.append(f"    {pfx}_region_dim_sizes,")
        reg_lines.append(f"    &{pfx}_region_dims[0][0],")
        reg_lines.append(f"    {ml},")
        reg_lines.append(f"    {pfx}_tielines,")
        reg_lines.append(f"    &{pfx}_overlap_groups[0][0],")
        reg_lines.append(f"    {og},")
        reg_lines.append(f"    {pfx}_gen_region,")
        reg_lines.append(f"    {pfx}_min_x,")
        reg_lines.append(f"    {pfx}_max_x,")
        reg_lines.append("};")
        reg_lines.append("")

    reg_lines.extend([
        "inline IeeeGridCaseId parse_ieee_grid_case(const char* s) {",
        '    if (!s) return IeeeGridCaseId::UNKNOWN;',
        '    if (strcmp(s, "IEEE14") == 0 || strcmp(s, "POWER14") == 0) return IeeeGridCaseId::IEEE14;',
        '    if (strcmp(s, "IEEE30") == 0 || strcmp(s, "POWER30") == 0) return IeeeGridCaseId::IEEE30;',
        '    if (strcmp(s, "IEEE57") == 0 || strcmp(s, "POWER57") == 0) return IeeeGridCaseId::IEEE57;',
        '    if (strcmp(s, "IEEE118") == 0 || strcmp(s, "POWER118") == 0) return IeeeGridCaseId::IEEE118;',
        "    return IeeeGridCaseId::UNKNOWN;",
        "}",
        "",
        "inline const IeeeGridCaseDesc* ieee_grid_case_desc(IeeeGridCaseId id) {",
        "    switch (id) {",
        "    case IeeeGridCaseId::IEEE14: return &kCase_IEEE14;",
        "    case IeeeGridCaseId::IEEE30: return &kCase_IEEE30;",
        "    case IeeeGridCaseId::IEEE57: return &kCase_IEEE57;",
        "    case IeeeGridCaseId::IEEE118: return &kCase_IEEE118;",
        "    default: return nullptr;",
        "    }",
        "}",
        "",
        "#endif",
    ])
    (OUT_DIR.parent / "ieee_grid_registry.h").write_text("\n".join(reg_lines), encoding="utf-8")
    print(f"[OK] headers -> {OUT_DIR}")


if __name__ == "__main__":
    main()
