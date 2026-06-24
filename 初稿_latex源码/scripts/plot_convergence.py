#!/usr/bin/env python3
"""
Plot convergence curves: MACPO vs RL-MACPO, F1--F6, 2x3 subplots with shaded variance.
Style: log-scale Y axis and mean ± std bands.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager
from scipy import interpolate

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MACPO_DIR = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'LLSO_25runs')
RLMACPO_DIR = os.path.join(PROJECT_ROOT, 'ablation_experiments', 'Exp4_Variable_Selection',
                           'MACPO2_WithSelection_0.9_0.7_0.5', 'output')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', '初稿_latex源码', 'media')
FUNCS = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']


def _pick_cjk_font():
    candidates = ['PingFang SC', 'Hiragino Sans GB', 'Heiti SC', 'STHeiti', 'SimHei', 'Microsoft YaHei',
                  'Noto Sans CJK SC', 'Arial Unicode MS']
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


_CJK_FONT = _pick_cjk_font()
if _CJK_FONT:
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['font.sans-serif'] = [_CJK_FONT, 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 10
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['pdf.fonttype'] = 42

# 高对比度：深蓝 vs 红（参照 MACPO 论文附录）
COLORS = {'macpo': '#2166ac', 'rl_macpo': '#d73027'}
ALPHA_SHADE = 0.25
# 论文图纵轴（对数）下限：与 conference_en_ready.tex 中 Fig.4 说明一致
Y_AXIS_FLOOR = 100.0


def load_trajectory(filepath):
    """解析轨迹文件，返回 (eval, f_pure) 数组"""
    evals, fpure = [], []
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                try:
                    evals.append(float(parts[1]))
                    fpure.append(float(parts[3]))
                except (ValueError, IndexError):
                    pass
    return np.array(evals), np.array(fpure)


def load_runs(base_dir, pattern_func, n_runs=25):
    """加载 n_runs 次运行的轨迹，pattern_func(fn, i) -> 文件名"""
    data = {}
    for fn in FUNCS:
        runs = []
        for i in range(1, n_runs + 1):
            fname = pattern_func(fn, i)
            path = os.path.join(base_dir, fname)
            if os.path.exists(path):
                ev, fp = load_trajectory(path)
                if len(ev) > 0:
                    runs.append((ev, fp))
        data[fn] = runs
    return data


def interpolate_to_grid(runs, grid):
    """将多次运行插值到统一网格，返回 (mean, std)"""
    if not runs:
        return np.full_like(grid, np.nan), np.full_like(grid, np.nan)
    vals = []
    for ev, fp in runs:
        if len(ev) < 2:
            continue
        # 确保单调
        ev = np.array(ev)
        fp = np.array(fp)
        order = np.argsort(ev)
        ev, fp = ev[order], fp[order]
        # 插值到 grid
        f_interp = interpolate.interp1d(ev, fp, kind='linear', bounds_error=False, fill_value='extrapolate')
        v = f_interp(grid)
        v = np.clip(v, 1e-10, None)  # 避免 log(0)
        vals.append(v)
    if not vals:
        return np.full_like(grid, np.nan), np.full_like(grid, np.nan)
    arr = np.array(vals)
    return np.nanmean(arr, axis=0), np.nanstd(arr, axis=0)


def fig_convergence_curves():
    """收敛曲线：2x3 子图，MACPO vs RL-MACPO，f(x) 对数轴，带阴影，统一 Y 轴"""
    # MACPO: F1_LLSO_run01.txt ...
    macpo_data = load_runs(MACPO_DIR, lambda fn, i: f'{fn}_LLSO_run{i:02d}.txt')
    # RL-MACPO: F1_LLSO_run01.txt ...
    rl_data = load_runs(RLMACPO_DIR, lambda fn, i: f'{fn}_LLSO_run{i:02d}.txt')

    # 统一网格：0 到 150000
    grid = np.linspace(0, 150000, 150)

    # 第一遍：收集所有子图的 Y 值（含 mean ± std）以统一 Y 轴范围
    all_ys = []
    for fn in FUNCS:
        m_mean, m_std = interpolate_to_grid(macpo_data.get(fn, []), grid)
        r_mean, r_std = interpolate_to_grid(rl_data.get(fn, []), grid)
        for mean, std in [(m_mean, m_std), (r_mean, r_std)]:
            if not np.all(np.isnan(mean)):
                valid = np.isfinite(mean) & (mean > 1e-10)
                if np.any(valid):
                    low = np.maximum(mean - np.nan_to_num(std), 1e-10)
                    high = mean + np.nan_to_num(std)
                    all_ys.extend(low[valid].tolist())
                    all_ys.extend(high[valid].tolist())
    all_ys = np.array([y for y in all_ys if y > 0 and np.isfinite(y)])
    if len(all_ys) > 0:
        y_min = max(Y_AXIS_FLOOR, max(1e-10, np.min(all_ys) * 0.5))
        y_max = np.max(all_ys) * 2
    else:
        y_min, y_max = Y_AXIS_FLOOR, 1e10

    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    axes = axes.flatten()

    for fi, fn in enumerate(FUNCS):
        ax = axes[fi]
        ax.set_yscale('log')

        # MACPO
        m_mean, m_std = interpolate_to_grid(macpo_data.get(fn, []), grid)
        if not np.all(np.isnan(m_mean)):
            ax.plot(grid, m_mean, color=COLORS['macpo'], linewidth=0.6, label='MACPO', marker='s', markevery=25, markersize=2)
            m_low = np.maximum(m_mean - m_std, 1e-10)
            m_high = np.maximum(m_mean + m_std, 1e-10)
            ax.fill_between(grid, m_low, m_high, color=COLORS['macpo'], alpha=ALPHA_SHADE)

        # RL-MACPO
        r_mean, r_std = interpolate_to_grid(rl_data.get(fn, []), grid)
        if not np.all(np.isnan(r_mean)):
            ax.plot(grid, r_mean, color=COLORS['rl_macpo'], linewidth=0.6, label='RL-MACPO', marker='o', markevery=25, markersize=2)
            r_low = np.maximum(r_mean - r_std, 1e-10)
            r_high = np.maximum(r_mean + r_std, 1e-10)
            ax.fill_between(grid, r_low, r_high, color=COLORS['rl_macpo'], alpha=ALPHA_SHADE)

        ax.set_xlabel('Evaluations')
        ax.set_ylabel('Fitness')
        ax.set_title(fn)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 150000)
        ax.set_ylim(y_min, y_max)

    fig.suptitle('Convergence Curves: MACPO vs RL-MACPO (f(x), 25 Runs)')
    fig.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(os.path.join(OUT_DIR, 'fig_convergence_curves.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_convergence_curves.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_convergence_curves')


if __name__ == '__main__':
    fig_convergence_curves()
    print('Convergence curves saved to', OUT_DIR)
