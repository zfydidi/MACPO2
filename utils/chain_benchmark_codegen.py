"""
Generate F1-style homogeneous elliptic chain benchmarks for arbitrary agent counts.

Global dimension for chain with N agents, 50 private dims each, overlap 5:
  D = 50*N - 5*(N-1) = 45*N + 5

C++ Benchmarks ctor also needs ./Benchmarks/data/group_*.txt, xopt_*.txt, R50_*.txt.
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = _REPO / "RL-MACPO" / "Benchmarks" / "default_config.json"
DATA_DIR = _REPO / "RL-MACPO" / "Benchmarks" / "data"
PRIVATE_DIM = 50
OVERLAP = 5

# Paper-facing aliases: reuse MACPO tiers + synthetic chain scales.
SCALABILITY_BENCHMARKS: tuple[tuple[str, int, str], ...] = (
    ("F1", 20, "F1"),
    ("F7", 40, "F7"),
    ("F13", 60, "F13"),
    ("F1S50", 50, "F1S50"),
    ("F1S100", 100, "F1S100"),
)


def chain_overlap_row(n: int, agent_idx: int, overlap: int = OVERLAP) -> list[int]:
    row = [0] * n
    if agent_idx > 0:
        row[agent_idx - 1] = overlap
    if agent_idx < n - 1:
        row[agent_idx + 1] = overlap
    return row


def global_dimension(n_agents: int, private_dim: int = PRIVATE_DIM, overlap: int = OVERLAP) -> int:
    return private_dim * n_agents - overlap * (n_agents - 1)


def chain_group_row(
    n_agents: int,
    agent_idx: int,
    *,
    private_dim: int = PRIVATE_DIM,
    overlap: int = OVERLAP,
    seed: int,
) -> list[int]:
    """One line of group_{ID}.txt: 1-indexed global variable indices (C++ subtracts 1)."""
    start = agent_idx * (private_dim - overlap)
    indices = [start + j for j in range(private_dim)]
    rng = random.Random(seed + agent_idx)
    rng.shuffle(indices)
    return [i + 1 for i in indices]


def benchmark_data_paths(name: str) -> tuple[Path, Path, Path]:
    return (
        DATA_DIR / f"group_{name}.txt",
        DATA_DIR / f"xopt_{name}.txt",
        DATA_DIR / f"R{PRIVATE_DIM}_{name}.txt",
    )


def benchmark_data_complete(name: str) -> bool:
    g, x, r = benchmark_data_paths(name)
    return g.is_file() and x.is_file() and r.is_file()


def is_synthetic_scalability_benchmark(name: str) -> bool:
    """仅 F1S50/F1S100 由 chain_benchmark_codegen 生成 data；F1/F7/F13 用 CEC 自带数据。"""
    return name in ("F1S50", "F1S100")


def write_benchmark_data_files(name: str, n_agents: int, *, seed: int | None = None) -> list[str]:
    """Write group/xopt/R50 data files for a chain benchmark. Returns paths written."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    seed_base = seed if seed is not None else sum(ord(c) for c in name) * 1009
    written: list[str] = []

    group_path, xopt_path, rot_path = benchmark_data_paths(name)
    if not group_path.is_file():
        lines = []
        for agent in range(n_agents):
            row = chain_group_row(n_agents, agent, seed=seed_base)
            lines.append(" ".join(str(v) for v in row))
        group_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(str(group_path))

    if not xopt_path.is_file():
        rng = random.Random(seed_base + 17)
        lines = []
        for _ in range(n_agents):
            row = [rng.uniform(-90.0, 90.0) for _ in range(PRIVATE_DIM)]
            lines.append(" ".join(f"{v:.14g}" for v in row))
        xopt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(str(xopt_path))

    if not rot_path.is_file():
        src = DATA_DIR / f"R{PRIVATE_DIM}_F1.txt"
        if not src.is_file():
            raise FileNotFoundError(f"缺少旋转矩阵模板 {src}，无法生成 {rot_path}")
        shutil.copy2(src, rot_path)
        written.append(str(rot_path))

    return written


def build_chain_benchmark(name: str, n_agents: int, base_function: str = "elliptic") -> dict[str, Any]:
    if n_agents < 2:
        raise ValueError("n_agents must be >= 2")
    dim = global_dimension(n_agents)
    subproblems = [
        {
            "base_function": base_function,
            "dimension": PRIVATE_DIM,
            "overlap": chain_overlap_row(n_agents, i),
        }
        for i in range(n_agents)
    ]
    return {
        "group_num": n_agents,
        "dimension": dim,
        "conforming": False,
        "upper_bound": 100,
        "lower_bound": -100,
        "subproblems": subproblems,
    }


def merge_into_default_config(
    entries: dict[str, dict[str, Any]],
    config_path: Path | str | None = None,
) -> Path:
    path = Path(config_path or DEFAULT_CONFIG)
    data = json.loads(path.read_text(encoding="utf-8"))
    benchmarks = data.setdefault("benchmarks", {})
    for name, spec in entries.items():
        benchmarks[name] = spec
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return path


def ensure_scalability_benchmarks(config_path: Path | str | None = None) -> list[str]:
    """Ensure F1S50/F1S100 JSON + Benchmarks/data/*.txt exist. Returns items written."""
    path = Path(config_path or DEFAULT_CONFIG)
    data = json.loads(path.read_text(encoding="utf-8"))
    benchmarks = data.setdefault("benchmarks", {})
    written: list[str] = []
    config_dirty = False
    for _alias, n, key in (("F1S50", 50, "F1S50"), ("F1S100", 100, "F1S100")):
        if key not in benchmarks:
            benchmarks[key] = build_chain_benchmark(key, n)
            config_dirty = True
            written.append(f"config:{key}")
        if not benchmark_data_complete(key):
            for p in write_benchmark_data_files(key, n):
                written.append(f"data:{p}")
    if config_dirty:
        path.write_text(json.dumps(data, indent=4), encoding="utf-8")
    return written
