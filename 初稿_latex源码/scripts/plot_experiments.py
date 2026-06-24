#!/usr/bin/env python3
"""
Generate all RL-MACPO experiment figures with English labels.
Data source: ablation_experiments/results/汇总对比表.csv and 补做实验_25runs/fitness_summary.csv
Style: color-blind-friendly palette, error bands, publication-ready axes.
"""
import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib import font_manager

# 数据路径（相对于项目根）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SUMMARY_CSV = os.path.join(PROJECT_ROOT, 'ablation_experiments', 'results', '汇总对比表.csv')
FITNESS_CSV = os.path.join(PROJECT_ROOT, 'ablation_experiments', 'results', '补做实验_25runs', 'fitness_summary.csv')
MACPO_ORIGINAL_CSV = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'MACPO_LLSO_25runs_summary.csv')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', '初稿_latex源码', 'media')
os.makedirs(OUT_DIR, exist_ok=True)

# 基准值：优先使用 MACPO_original_output 运行数据，否则用论文 Table I
BASE = {'F1': 1.75e8, 'F2': 7.65e5, 'F3': 2.13e10, 'F4': 2.7e7, 'F5': 6.58e8, 'F6': 2.39e8}
FUNCS = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']


def _parse_float(s, default=0):
    if s is None or s == '':
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _load_macpo_original():
    """加载 MACPO 原始运行数据（25 次）"""
    if not os.path.exists(MACPO_ORIGINAL_CSV):
        return None
    data = {}
    with open(MACPO_ORIGINAL_CSV, encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for row in r:
            fn = row.get('函数', '').strip()
            if fn in FUNCS:
                data[fn] = (_parse_float(row.get('F_mean')), _parse_float(row.get('F_std')))
    return data if len(data) == 6 else None


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
else:
    matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 10
matplotlib.rcParams['axes.linewidth'] = 1.2
matplotlib.rcParams['pdf.fonttype'] = 42

# 高对比度配色（参照 ColorBrewer Set1，色盲友好，区分度强）
COLORS = {
    'baseline': '#2166ac',   # 深蓝 (MACPO)
    'rl_only': '#d73027',    # 红
    'full': '#1a9850',       # 绿
    'layer1': '#f46d43',     # 橙红
    'layer1_2': '#66bd63',   # 草绿
    'no_gating': '#e41a1c',  # 红
    'eta_fixed': '#4d4d4d',  # 深灰（替代浅灰，提高可见度）
    'eta_phase': '#984ea3',  # 紫
    'eta_rl': '#377eb8',     # 蓝
    'unified': '#ff7f00',    # 橙
    'simple': '#e41a1c',     # 红
    'ppo': '#377eb8',        # 蓝
    'a2c': '#4daf4a',        # 绿
    'lstm': '#984ea3',       # 紫
    'mlp': '#ff7f00',        # 橙
    'dqn': '#a65628',        # 棕
    'dueling': '#f781bf',    # 粉
    'llso': '#377eb8', 'cso': '#ff7f00',
}
# 消融 9 配置专用：互不相似
ABLATION_9_COLORS = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628', '#f781bf', '#636363', '#006d2c']
# 深度 RL 7 架构专用
DEEPRL_7_COLORS = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628', '#f781bf']


def _load_summary():
    """加载汇总对比表"""
    data = {}
    with open(SUMMARY_CSV, encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for row in r:
            name = row['方法']
            data[name] = {k: row.get(k) for k in row}
    return data


def _load_fitness_summary():
    """加载补做实验 fitness_summary"""
    data = {}
    with open(FITNESS_CSV, encoding='utf-8-sig') as f:
        r = csv.DictReader(f)
        for row in r:
            name = row['配置名']
            data[name] = {k: row.get(k) for k in row}
    return data


def _load_convergence_trajectories():
    """从 MACPO_original_output/LLSO_25runs 和 RL-MACPO 输出加载收敛轨迹"""
    from scipy import interpolate
    MACPO_DIR = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'LLSO_25runs')
    RLMACPO_DIR = os.path.join(PROJECT_ROOT, 'ablation_experiments', 'Exp4_Variable_Selection',
                               'MACPO2_WithSelection_0.9_0.7_0.5', 'output')

    def load_traj(path):
        ev, fp = [], []
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        ev.append(float(parts[1]))
                        fp.append(float(parts[3]))
                    except (ValueError, IndexError):
                        pass
        return np.array(ev), np.array(fp)

    def load_runs(base_dir, pattern, n=25):
        out = {}
        for fn in FUNCS:
            runs = []
            for i in range(1, n + 1):
                p = os.path.join(base_dir, pattern(fn, i))
                if os.path.exists(p):
                    ev, fp = load_traj(p)
                    if len(ev) > 0:
                        runs.append((ev, fp))
            out[fn] = runs
        return out

    def interp_grid(runs, grid):
        if not runs:
            return np.full_like(grid, np.nan), np.full_like(grid, np.nan)
        vals = []
        for ev, fp in runs:
            if len(ev) < 2:
                continue
            o = np.argsort(ev)
            ev, fp = np.array(ev)[o], np.array(fp)[o]
            f = interpolate.interp1d(ev, fp, kind='linear', bounds_error=False, fill_value='extrapolate')
            v = np.clip(f(grid), 1e-10, None)
            vals.append(v)
        if not vals:
            return np.full_like(grid, np.nan), np.full_like(grid, np.nan)
        arr = np.array(vals)
        return np.nanmean(arr, 0), np.nanstd(arr, 0)

    grid = np.linspace(0, 150000, 150)
    macpo = load_runs(MACPO_DIR, lambda fn, i: f'{fn}_LLSO_run{i:02d}.txt')
    rl = load_runs(RLMACPO_DIR, lambda fn, i: f'{fn}_LLSO_run{i:02d}.txt')
    return macpo, rl, grid, interp_grid


def fig_main_comparison():
    """图1: 主对比 - F1--F6 收敛曲线（MACPO vs RL-MACPO），数据来自 LLSO_25runs，统一 Y 轴"""
    macpo_data, rl_data, grid, interp = _load_convergence_trajectories()
    # 第一遍：收集所有子图的 Y 值（含 mean ± std）以统一 Y 轴范围
    all_ys = []
    for fn in FUNCS:
        m_mean, m_std = interp(macpo_data.get(fn, []), grid)
        r_mean, r_std = interp(rl_data.get(fn, []), grid)
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
        y_min = max(1e-10, np.min(all_ys) * 0.5)
        y_max = np.max(all_ys) * 2
    else:
        y_min, y_max = 1e4, 1e10

    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    axes = axes.flatten()
    for fi, fn in enumerate(FUNCS):
        ax = axes[fi]
        ax.set_yscale('log')
        m_mean, m_std = interp(macpo_data.get(fn, []), grid)
        if not np.all(np.isnan(m_mean)):
            ax.plot(grid, m_mean, color=COLORS['baseline'], linewidth=0.6, label='MACPO', marker='s', markevery=25, markersize=2)
            m_low = np.maximum(m_mean - m_std, 1e-10)
            m_high = np.maximum(m_mean + m_std, 1e-10)
            ax.fill_between(grid, m_low, m_high, color=COLORS['baseline'], alpha=0.2)
        r_mean, r_std = interp(rl_data.get(fn, []), grid)
        if not np.all(np.isnan(r_mean)):
            ax.plot(grid, r_mean, color=COLORS['full'], linewidth=0.6, label='RL-MACPO', marker='o', markevery=25, markersize=2)
            r_low = np.maximum(r_mean - r_std, 1e-10)
            r_high = np.maximum(r_mean + r_std, 1e-10)
            ax.fill_between(grid, r_low, r_high, color=COLORS['full'], alpha=0.2)
        ax.set_xlabel('Evaluations')
        ax.set_ylabel('Fitness')
        ax.set_title(fn)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 150000)
        ax.set_ylim(y_min, y_max)
    fig.suptitle('Main Comparison: MACPO vs RL-MACPO Convergence Curves (F1--F6, 25 Runs, Shaded ±1σ)')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_main_comparison.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_main_comparison.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_main_comparison')


def fig_main_results_bar():
    """主结果柱状图：F1--F6 最终适应度（mean ± std），非改善率，数据来自 LLSO_25runs"""
    macpo_data = _load_macpo_original()
    summary = _load_summary()
    rl = summary.get('RL_Only_SimpleRL', {})
    full = summary.get('Full_S5_LLSO', {})

    if not macpo_data:
        print('Skip fig_main_results_bar: 缺少 MACPO_original_output 数据')
        return

    means = {
        'MACPO': [macpo_data[f][0] for f in FUNCS],
        'RL_Only': [_parse_float(rl.get(f'{f}均值')) for f in FUNCS],
        'RL-MACPO Full': [_parse_float(full.get(f'{f}均值')) for f in FUNCS],
    }
    stds = {
        'MACPO': [macpo_data[f][1] for f in FUNCS],
        'RL_Only': [_parse_float(rl.get(f'{f}标准差')) for f in FUNCS],
        'RL-MACPO Full': [_parse_float(full.get(f'{f}标准差')) for f in FUNCS],
    }
    x = np.arange(len(FUNCS))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_yscale('log')
    bar_colors = ['#6baed6', '#fc8d59', '#91cf60']  # 浅蓝、浅橙、浅绿，避免过深
    for i, (label, c) in enumerate([('MACPO', bar_colors[0]), ('RL_Only', bar_colors[1]), ('RL-MACPO Full', bar_colors[2])]):
        m = np.array(means[label])
        s = np.array(stds[label])
        m = np.maximum(m, 1e-10)
        pos = x + (i - 1) * w
        ax.bar(pos, m, w, label=label, color=c, edgecolor='black', linewidth=0.5)
        ax.errorbar(pos, m, yerr=s, fmt='none', color='black', capsize=2, linewidth=0.8)
    ax.set_xlabel('Benchmark Function')
    ax.set_ylabel('Fitness (log)')
    ax.set_xticks(x)
    ax.set_xticklabels(FUNCS)
    ax.legend()
    ax.set_title('Main Results: Final Fitness on F1--F6 (25 Runs, LLSO)')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_main_results_bar.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_main_results_bar.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_main_results_bar')


def fig_gating_ablation():
    """图2: 门控消融 - F1--F6 各函数的最终适应度（折线图），统一 Y 轴"""
    fit = _load_fitness_summary()
    configs = ['NoGating', 'Layer1', 'Layer1+2', 'Layer1+2+3']
    keys = ['MACPO_baseline', 'MACPO2_Layer1', 'MACPO2_Layer1_2', 'MACPO2_Full_S5']
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    axes = axes.flatten()
    x = np.arange(4)
    # 第一遍：收集所有子图的 Y 值（含 mean ± std）以统一 Y 轴范围
    all_ys = []
    for fn in FUNCS:
        means, stds = [], []
        for k in keys:
            row = fit.get(k, {})
            m = _parse_float(row.get(f'{fn}_mean'))
            s = _parse_float(row.get(f'{fn}_std'))
            means.append(max(m, 1e-10))
            stds.append(s)
        means, stds = np.array(means), np.array(stds)
        all_ys.extend((means - stds).tolist())
        all_ys.extend((means + stds).tolist())
    all_ys = np.array([y for y in all_ys if y > 0 and np.isfinite(y)])
    if len(all_ys) > 0:
        y_min = max(1e-10, np.min(all_ys) * 0.5)
        y_max = np.max(all_ys) * 2
    else:
        y_min, y_max = 1e4, 1e10

    for fi, fn in enumerate(FUNCS):
        ax = axes[fi]
        ax.set_yscale('log')
        means, stds = [], []
        for k in keys:
            row = fit.get(k, {})
            m = _parse_float(row.get(f'{fn}_mean'))
            s = _parse_float(row.get(f'{fn}_std'))
            means.append(max(m, 1e-10))
            stds.append(s)
        means, stds = np.array(means), np.array(stds)
        ax.plot(x, means, 'o-', color='#6baed6', linewidth=1, markersize=4)
        ax.fill_between(x, means - stds, means + stds, color='#6baed6', alpha=0.2)
        ax.set_xticks(x)
        ax.set_xticklabels(configs, rotation=15, ha='right')
        ax.set_ylabel('Fitness')
        ax.set_title(fn)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(y_min, y_max)
    fig.suptitle('Gating Layer Ablation: Final Fitness of Each Configuration on F1--F6')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_gating_ablation.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_gating_ablation.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_gating_ablation')


def fig_variable_selection():
    """图3: 变量选择消融 - F1--F6 各函数的最终适应度（折线图），统一 Y 轴"""
    fit = _load_fitness_summary()
    configs = ['NoSelection', '0.9/0.6/0.2', '0.9/0.6/0.3', '0.9/0.7/0.5']
    keys = ['MACPO2_NoSelection', 'MACPO2_WithSelection_0.9_0.6_0.2', 'MACPO2_WithSelection_0.9_0.6_0.3', 'MACPO2_WithSelection_0.9_0.7_0.5']
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    axes = axes.flatten()
    x = np.arange(4)
    for fi, fn in enumerate(FUNCS):
        ax = axes[fi]
        ax.set_yscale('log')
        means, stds = [], []
        for k in keys:
            row = fit.get(k, {})
            m = _parse_float(row.get(f'{fn}_mean'))
            s = _parse_float(row.get(f'{fn}_std'))
            means.append(max(m, 1e-10))
            stds.append(s)
        means, stds = np.array(means), np.array(stds)
        ax.plot(x, means, 's-', color='#6baed6', linewidth=1, markersize=4)
        low = np.maximum(means - stds, 1e-10)
        high = np.maximum(means + stds, 1e-10)
        ax.fill_between(x, low, high, color='#6baed6', alpha=0.2)
        ax.set_xticks(x)
        ax.set_xticklabels(configs, rotation=15, ha='right')
        ax.set_ylabel('Fitness')
        ax.set_title(fn)
        ax.grid(True, alpha=0.3)
        # Use per-subplot y-range for better readability.
        local_y = np.concatenate([low, high])
        local_y = local_y[np.isfinite(local_y) & (local_y > 0)]
        if local_y.size > 0:
            ax.set_ylim(np.min(local_y) * 0.85, np.max(local_y) * 1.25)
    fig.suptitle('Variable Selection Ablation: Final Fitness of Each Configuration on F1--F6')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_variable_selection.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_variable_selection.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_variable_selection')


def fig_phase_eta():
    """图4: 阶段采样与 Eta 消融 - F1--F6 各函数的最终适应度"""
    fit = _load_fitness_summary()
    configs_phase = ['NoPhase', 'Full']
    keys_phase = ['MACPO2_NoPhase', 'MACPO2_Full_S5']
    configs_eta = ['Fixed', 'Phase', 'Eta_RL', 'Unified']
    keys_eta = ['MACPO2_Eta_Fixed05', 'MACPO2_Eta_Phase', 'MACPO2_Eta_RL', 'MACPO2_Unified_AlphaEta']
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(FUNCS))
    for ax, keys, configs, colors in [
        (ax1, keys_phase, configs_phase, [COLORS['eta_fixed'], COLORS['full']]),
        (ax2, keys_eta, configs_eta, [COLORS['eta_fixed'], COLORS['eta_phase'], COLORS['eta_rl'], COLORS['unified']]),
    ]:
        ax.set_yscale('log')
        for j, (k, c) in enumerate(zip(keys, colors)):
            y = [max(_parse_float(fit.get(k, {}).get(f'{fn}_mean')), 1e-10) for fn in FUNCS]
            s = [_parse_float(fit.get(k, {}).get(f'{fn}_std')) for fn in FUNCS]
            ax.plot(x, y, 'o-', label=configs[j], color=c, linewidth=1, markersize=4)
            ax.fill_between(x, np.array(y) - np.array(s), np.array(y) + np.array(s), color=c, alpha=0.08)
        ax.set_xticks(x)
        ax.set_xticklabels(FUNCS)
        ax.set_ylabel('Fitness')
        ax.legend()
        ax.grid(True, alpha=0.3)
    ax1.set_title('Phase Sampling Ablation')
    ax2.set_title('Eta Strategy Ablation')
    fig.suptitle('Phase Sampling and Eta Strategy Ablation: Final Fitness on F1--F6')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_phase_eta.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_phase_eta.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_phase_eta')


def fig_deeprl():
    """图5: 深度 RL 架构对比 - F1--F6 最终适应度（折线图，7 条线）"""
    summary = _load_summary()
    methods = ['SimpleNet', 'PPO', 'A2C', 'LSTM', 'MLP', 'DQN', 'Dueling DQN']
    keys = ['Full_S5_LLSO', 'DeepRL_Torch_PPO', 'DeepRL_A2C', 'DeepRL_Torch_LSTM', 'DeepRL_Eigen_MLP', 'DeepRL_Torch_DQN', 'DeepRL_DuelingDQN']
    colors = DEEPRL_7_COLORS
    x = np.arange(len(FUNCS))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_yscale('log')
    all_y = []
    for j, (method, key) in enumerate(zip(methods, keys)):
        means = [max(_parse_float(summary.get(key, {}).get(f'{f}均值') or summary.get(key, {}).get(f'{f}_mean'), 0), 1e-10) for f in FUNCS]
        stds = [_parse_float(summary.get(key, {}).get(f'{f}标准差') or summary.get(key, {}).get(f'{f}_std'), 0) for f in FUNCS]
        ax.plot(x, means, 'o-', label=method, color=colors[j], linewidth=1, markersize=3)
        all_y.extend(means)
        # 7 条线重叠时阴影会严重遮挡，此处不绘制阴影以保持折线清晰
    ax.set_xticks(x)
    ax.set_xticklabels(FUNCS)
    ax.set_xlabel('Benchmark Function')
    ax.set_ylabel('Fitness')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=8)
    ax.grid(True, alpha=0.3)
    y = np.array([v for v in all_y if np.isfinite(v) and v > 0])
    if y.size > 0:
        ax.set_ylim(np.min(y) * 0.8, np.max(y) * 1.25)
    ax.set_title('Deep RL Architecture Comparison: Final Fitness on F1--F6')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_deeprl_comparison.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_deeprl_comparison.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_deeprl_comparison')


def fig_ablation_comparison():
    """图6: 消融实验对比 - 折线图，各配置在 F1--F6 上的最终适应度（替代热力图）"""
    fit = _load_fitness_summary()
    summary = _load_summary()
    configs = ['NoGating', 'Layer1', 'Layer1+2', 'Full', 'NoSelection', '0.9/0.7/0.5', 'NoPhase', 'Eta_Phase', 'PPO']
    keys = ['MACPO_baseline', 'MACPO2_Layer1', 'MACPO2_Layer1_2', 'MACPO2_Full_S5', 'MACPO2_NoSelection',
            'MACPO2_WithSelection_0.9_0.7_0.5', 'MACPO2_NoPhase', 'MACPO2_Eta_Phase', 'DeepRL_Torch_PPO']
    colors = ABLATION_9_COLORS
    x = np.arange(len(FUNCS))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_yscale('log')
    for i, (cfg, k) in enumerate(zip(configs, keys)):
        if k in fit:
            means = [max(_parse_float(fit[k].get(f'{f}_mean')), 1e-10) for f in FUNCS]
            stds = [_parse_float(fit[k].get(f'{f}_std')) for f in FUNCS]
        else:
            means = [max(_parse_float(summary.get(k, {}).get(f'{f}均值')), 1e-10) for f in FUNCS]
            stds = [_parse_float(summary.get(k, {}).get(f'{f}标准差')) for f in FUNCS]
        ax.plot(x, means, 'o-', label=cfg, color=colors[i], linewidth=0.6, markersize=2)
        ax.fill_between(x, np.array(means) - np.array(stds), np.array(means) + np.array(stds),
                        color=colors[i], alpha=0.15)
    ax.set_xticks(x)
    ax.set_xticklabels(FUNCS)
    ax.set_xlabel('Benchmark Function')
    ax.set_ylabel('Fitness')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_title('Ablation Comparison: Final Fitness of Each Configuration on F1--F6 (LLSO)')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'fig_ablation_comparison.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(OUT_DIR, 'fig_ablation_comparison.pdf'), bbox_inches='tight')
    plt.close()
    print('Saved fig_ablation_comparison')


if __name__ == '__main__':
    fig_main_comparison()
    fig_main_results_bar()
    fig_gating_ablation()
    fig_variable_selection()
    fig_phase_eta()
    fig_deeprl()
    fig_ablation_comparison()
    print('All figures saved to', OUT_DIR)
