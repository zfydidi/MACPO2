"""
FES vs best-so-far fitness plotting helpers (MACPO vs RL-MACPO).
Single source for trajectory parsing and fair comparison curves.
"""
from __future__ import annotations

import os

import numpy as np
from scipy import interpolate

COLORS = {"macpo": "#2166ac", "rl": "#d73027"}
ALPHA_SHADE = 0.25
# 部分函数上 mean±std 在对数纵轴上带状“下沉”，单图/面板中仅画均值曲线
NO_STD_SHADE_FUNCS: frozenset[str] = frozenset({"F2", "F6"})

# 面板图：统一纵轴范围与刻度（10²…10¹²，6 个主刻度）；横轴 4 个刻度
PANEL_YLIM = (1e2, 1e12)
PANEL_Y_TICKS = np.array([1e2, 1e4, 1e6, 1e8, 1e10, 1e12])
PANEL_X_TICKS = np.array([0.0, 50_000.0, 100_000.0, 150_000.0])
PANEL_XLIM = (0.0, 150_000.0)


def log_minor_tick_positions(ymin: float, ymax: float) -> np.ndarray:
    """
    对数纵轴细刻度位置：每个十倍频内 2…9 倍该幂次（与常见 log 纸一致）。
    用于 matplotlib 在跨多十倍频时 LogLocator(subs) 易返回空的情况。
    """
    if ymin <= 0 or ymax <= 0:
        return np.array([])
    ymin, ymax = float(ymin), float(ymax)
    if ymin > ymax:
        ymin, ymax = ymax, ymin
    p_min = int(np.floor(np.log10(ymin)))
    p_max = int(np.ceil(np.log10(ymax))) - 1
    p_max = max(p_min, p_max)
    ticks: list[float] = []
    for p in range(p_min, p_max + 1):
        base = 10.0**p
        for m in range(2, 10):
            t = m * base
            if ymin <= t <= ymax:
                ticks.append(t)
    return np.asarray(ticks, dtype=float)


# 面板固定 y 轴时的细刻度（预计算，避免每子图重复算）
PANEL_Y_MINOR_TICKS = log_minor_tick_positions(PANEL_YLIM[0], PANEL_YLIM[1])


def load_trajectory(filepath: str):
    """Parse log: columns iter, eval, f_penalty, f_pure (whitespace-separated)."""
    evals, fpure = [], []
    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    evals.append(float(parts[1]))
                    fpure.append(float(parts[3]))
                except (ValueError, IndexError):
                    pass
    return np.asarray(evals), np.asarray(fpure)


def best_so_far_curve(evals: np.ndarray, fpure: np.ndarray):
    if len(evals) == 0:
        return evals, fpure
    order = np.argsort(evals)
    e = evals[order]
    f = fpure[order]
    y = np.minimum.accumulate(f)
    return e, y


def runs_mean_std(runs: list[tuple[np.ndarray, np.ndarray]], grid: np.ndarray):
    vals = []
    for ev, fp in runs:
        e, y = best_so_far_curve(ev, fp)
        if len(e) < 2:
            continue
        fn = interpolate.interp1d(
            e,
            y,
            kind="linear",
            bounds_error=False,
            fill_value=(y[0], y[-1]),
        )
        vals.append(fn(grid))
    if not vals:
        return np.full_like(grid, np.nan), np.full_like(grid, np.nan)
    arr = np.stack(vals, axis=0)
    return np.nanmean(arr, axis=0), np.nanstd(arr, axis=0)


def plot_macpo_vs_rl(
    macpo_paths: list[str],
    rl_paths: list[str],
    out_path: str,
    title: str,
    *,
    setup_font,
    show_std_shade: bool = True,
) -> tuple[float, float, int, int]:
    """
    setup_font: callable () -> None (e.g. utils.mpl_font.setup_cjk_font).
    show_std_shade: if True, draw mean±std band (fill_between); if False, mean line only.
    Returns (emin, emax, n_macpo, n_rl).
    """
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, LogFormatterSciNotation, LogLocator, NullFormatter

    setup_font()
    matplotlib.rcParams["axes.unicode_minus"] = False
    macpo_runs = [load_trajectory(p) for p in macpo_paths if os.path.isfile(p)]
    rl_runs = [load_trajectory(p) for p in rl_paths if os.path.isfile(p)]

    all_first, all_last = [], []
    for ev, _ in macpo_runs + rl_runs:
        if len(ev):
            all_first.append(float(ev.min()))
            all_last.append(float(ev.max()))
    if not all_first:
        raise FileNotFoundError("No valid trajectory data for plotting.")

    emin = min(all_first)
    emax = max(all_last)
    grid = np.linspace(emin, emax, min(200, max(40, int((emax - emin) / 400))))

    m_mean, m_std = runs_mean_std(macpo_runs, grid)
    r_mean, r_std = runs_mean_std(rl_runs, grid)

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.set_yscale("log")
    # 对数纵轴：10 的幂主刻度；细次刻度为每十倍频内 2…9（matplotlib LogLocator 跨多十倍频时 subs 常为空，故用手动位置）
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(LogFormatterSciNotation())
    if not np.all(np.isnan(m_mean)):
        ax.plot(grid, m_mean, color=COLORS["macpo"], lw=1.2, label="MACPO")
        if show_std_shade:
            lo = np.maximum(m_mean - np.nan_to_num(m_std), 1e-300)
            hi = np.maximum(m_mean + np.nan_to_num(m_std), lo * 1.0001)
            ax.fill_between(grid, lo, hi, color=COLORS["macpo"], alpha=ALPHA_SHADE)
    if not np.all(np.isnan(r_mean)):
        ax.plot(grid, r_mean, color=COLORS["rl"], lw=1.2, label="RL-MACPO")
        if show_std_shade:
            lo = np.maximum(r_mean - np.nan_to_num(r_std), 1e-300)
            hi = np.maximum(r_mean + np.nan_to_num(r_std), lo * 1.0001)
            ax.fill_between(grid, lo, hi, color=COLORS["rl"], alpha=ALPHA_SHADE)

    ax.set_xlabel("Evaluations")
    ax.set_ylabel("fitness")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    # 与常见收敛图一致：横轴从 0 到预算上限（数据仍从首个 FES 起有曲线）
    ax.set_xlim(0.0, max(emax, 150000.0))

    ymin, ymax = ax.get_ylim()
    ax.yaxis.set_minor_locator(FixedLocator(log_minor_tick_positions(ymin, ymax)))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.tick_params(axis="y", which="major", length=5.5, width=0.6, direction="in")
    ax.tick_params(axis="y", which="minor", length=3.0, width=0.5, direction="in")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close()

    return emin, emax, len(macpo_runs), len(rl_runs)


def _format_x_evaluations_comma(value: float, _pos: int | None) -> str:
    """横轴大整数用千分位，便于与 0 / 50,000 / … 风格一致。"""
    return f"{int(round(value)):,}"


def plot_fes_panel_2x3(
    items: list[tuple[str, list[str], list[str]]],
    out_path: str,
    *,
    setup_font,
) -> None:
    """
    2×3 子图（两行三列）：MACPO vs RL-MACPO，共享纵轴 [1e2, 1e12]（6 个对数主刻度），
    横轴 0–150000（4 个刻度）。子图顺序为 F1,F2,F3 / F4,F5,F6。每子图标题为函数名；
    xlabel「Evaluations」、ylabel「fitness」；刻度朝内。与单图一致使用 NO_STD_SHADE_FUNCS 控制是否画 std 阴影。

    items: 长度 6 的列表，每项 (函数名, MACPO 轨迹路径列表, RL 轨迹路径列表)。
    """
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, FuncFormatter, LogFormatterSciNotation, NullFormatter

    if len(items) != 6:
        raise ValueError(f"Expected 6 panels, got {len(items)}")

    setup_font()
    matplotlib.rcParams["axes.unicode_minus"] = False

    # 两行三列；不共享轴（sharex/sharey=False），否则 matplotlib 只在最下/最左子图显示刻度数字，
    # 论文面板需要每个子图都有 Evaluations 与 fitness 的刻度。各子图仍用同一 xlim/ylim。
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.4), sharex=False, sharey=False)
    axes_flat = axes.flatten()

    for idx, (fn, macpo_paths, rl_paths) in enumerate(items):
        ax = axes_flat[idx]
        macpo_runs = [load_trajectory(p) for p in macpo_paths if os.path.isfile(p)]
        rl_runs = [load_trajectory(p) for p in rl_paths if os.path.isfile(p)]

        all_first, all_last = [], []
        for ev, _ in macpo_runs + rl_runs:
            if len(ev):
                all_first.append(float(ev.min()))
                all_last.append(float(ev.max()))
        if not all_first:
            raise FileNotFoundError(f"No valid trajectory data for panel {fn}.")

        emin = min(all_first)
        emax = max(all_last)
        grid = np.linspace(emin, emax, min(200, max(40, int((emax - emin) / 400))))

        m_mean, m_std = runs_mean_std(macpo_runs, grid)
        r_mean, r_std = runs_mean_std(rl_runs, grid)
        show_std_shade = fn not in NO_STD_SHADE_FUNCS

        ax.set_yscale("log")
        ax.set_xlim(*PANEL_XLIM)
        ax.set_ylim(*PANEL_YLIM)

        ax.xaxis.set_major_locator(FixedLocator(PANEL_X_TICKS))
        ax.xaxis.set_major_formatter(FuncFormatter(_format_x_evaluations_comma))
        ax.xaxis.set_minor_formatter(NullFormatter())

        ax.yaxis.set_major_locator(FixedLocator(PANEL_Y_TICKS))
        ax.yaxis.set_major_formatter(LogFormatterSciNotation())
        ax.yaxis.set_minor_locator(FixedLocator(PANEL_Y_MINOR_TICKS))
        ax.yaxis.set_minor_formatter(NullFormatter())

        lbl_m = "MACPO" if idx == 0 else "_nolegend_"
        lbl_r = "RL-MACPO" if idx == 0 else "_nolegend_"

        if not np.all(np.isnan(m_mean)):
            ax.plot(grid, m_mean, color=COLORS["macpo"], lw=1.2, label=lbl_m)
            if show_std_shade:
                lo = np.maximum(m_mean - np.nan_to_num(m_std), 1e-300)
                hi = np.maximum(m_mean + np.nan_to_num(m_std), lo * 1.0001)
                ax.fill_between(grid, lo, hi, color=COLORS["macpo"], alpha=ALPHA_SHADE)
        if not np.all(np.isnan(r_mean)):
            ax.plot(grid, r_mean, color=COLORS["rl"], lw=1.2, label=lbl_r)
            if show_std_shade:
                lo = np.maximum(r_mean - np.nan_to_num(r_std), 1e-300)
                hi = np.maximum(r_mean + np.nan_to_num(r_std), lo * 1.0001)
                ax.fill_between(grid, lo, hi, color=COLORS["rl"], alpha=ALPHA_SHADE)

        ax.set_title(fn)
        ax.set_xlabel("Evaluations")
        ax.set_ylabel("fitness")
        ax.grid(True, alpha=0.3, which="major")
        ax.tick_params(
            axis="both",
            which="both",
            direction="in",
            top=True,
            right=True,
            bottom=True,
            left=True,
        )
        ax.tick_params(axis="y", which="major", length=5.5, width=0.6, direction="in")
        ax.tick_params(axis="y", which="minor", length=3.0, width=0.5, direction="in")
        ax.tick_params(axis="x", which="major", labelbottom=True)
        ax.tick_params(axis="y", which="major", labelleft=True)

    axes_flat[0].legend(loc="upper right", fontsize=9)

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close()
