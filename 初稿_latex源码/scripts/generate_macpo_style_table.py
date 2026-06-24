#!/usr/bin/env python3
"""
生成与 MACPO 论文 Table I 格式一致的对比表格
包含：mean, median, std（分行）, Wilcoxon p-value, w/t/l
"""
import os
import re
import numpy as np
from scipy import stats
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNCS = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']


def extract_fitness_from_summary_format(filepath):
    """从 Run_X: ... final fitness=X.XXe+YY 格式提取"""
    vals = []
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            m = re.search(r'final fitness=([\d.e+-]+)', line)
            if m:
                vals.append(float(m.group(1)))
    return np.array(vals) if vals else None


def extract_fitness_from_trajectory(filepath):
    """从 MACPO 轨迹文件提取最后一行的 f_pure"""
    vals = []
    with open(filepath, encoding='utf-8') as f:
        lines = [l for l in f if not l.startswith('#') and l.strip()]
    for line in lines:
        parts = line.split()
        if len(parts) >= 4:
            try:
                vals.append(float(parts[3]))  # f_pure
            except ValueError:
                pass
    return float(vals[-1]) if vals else None


def load_macpo_original():
    """从 MACPO_original_output/LLSO_25runs 加载"""
    base = PROJECT_ROOT / 'MACPO_original_output' / 'LLSO_25runs'
    data = {}
    for fn in FUNCS:
        vals = []
        for i in range(1, 26):
            path = base / f'{fn}_LLSO_run{i:02d}.txt'
            if path.exists():
                v = extract_fitness_from_trajectory(str(path))
                if v is not None:
                    vals.append(v)
        data[fn] = np.array(vals) if vals else None
    return data


def load_from_buzuo(config_prefix, base_dir=None):
    """从补做实验_25runs 加载"""
    if base_dir is None:
        base_dir = PROJECT_ROOT / 'ablation_experiments' / 'results' / '补做实验_25runs'
    data = {}
    for fn in FUNCS:
        path = base_dir / f'{config_prefix}_LLSO_{fn}.txt'
        if path.exists():
            vals = extract_fitness_from_summary_format(str(path))
            data[fn] = vals
        else:
            data[fn] = None
    return data


def load_rl_only():
    """从 Full_System_and_RLonly 加载 RL_Only"""
    base = PROJECT_ROOT / 'ablation_experiments' / 'results' / 'Full_System_and_RLonly_LLSO_CSO_25runs'
    data = {}
    for fn in FUNCS:
        path = base / f'RL_Only_SimpleRL_S5_LLSO_{fn}.txt'
        if path.exists():
            vals = extract_fitness_from_summary_format(str(path))
            data[fn] = vals
        else:
            data[fn] = None
    return data


def load_full_s5():
    """加载 RL-MACPO Full"""
    return load_from_buzuo('MACPO2_Full_S5')


def fmt_sci(x):
    """格式化为科学计数法 1.75E+08"""
    if x == 0 or not np.isfinite(x):
        return '0'
    exp = int(np.floor(np.log10(abs(x))))
    mant = x / (10 ** exp)
    sign = '+' if exp >= 0 else ''
    return f'{mant:.2f}E{sign}{exp}'


def wilcoxon_test(a, b):
    """Wilcoxon rank-sum test. a=baseline(MACPO), b=other. 返回 (p_less, p_greater)"""
    if a is None or b is None or len(a) < 5 or len(b) < 5:
        return None, None
    _, p_less = stats.mannwhitneyu(b, a, alternative='less')   # H1: b < a (other better)
    _, p_greater = stats.mannwhitneyu(b, a, alternative='greater')  # H1: b > a (other worse)
    return p_less, p_greater


def main():
    # 加载数据：优先用 MACPO_original（与论文一致），否则用 MACPO_baseline
    macpo_orig = load_macpo_original()
    macpo_baseline = load_from_buzuo('MACPO_baseline')
    rl_only = load_rl_only()
    full_s5 = load_full_s5()

    # 选择 MACPO：若 original 有完整数据则用 original，否则用 baseline
    macpo_ok = all(macpo_orig[f] is not None and len(macpo_orig[f]) >= 20 for f in FUNCS)
    macpo_data = macpo_orig if macpo_ok else macpo_baseline
    macpo_name = 'MACPO' if macpo_ok else 'MACPO (ours)'

    algos = [
        (macpo_name, macpo_data),
        ('RL\_Only', rl_only),
        ('RL-MACPO', full_s5),
    ]

    # 计算统计量
    results = {}
    for name, data in algos:
        results[name] = {}
        for fn in FUNCS:
            v = data.get(fn)
            if v is not None and len(v) > 0:
                results[name][fn] = {
                    'mean': np.mean(v),
                    'median': np.median(v),
                    'std': np.std(v),
                    'vals': v,
                }
            else:
                results[name][fn] = None

    # Wilcoxon p-value (vs MACPO)
    baseline_vals = {fn: results[macpo_name][fn]['vals'] for fn in FUNCS if results[macpo_name][fn]}
    pvalues = {}
    for name, data in algos:
        if name == macpo_name:
            continue
        pvalues[name] = {}
        for fn in FUNCS:
            b = baseline_vals.get(fn)
            a = results[name][fn]['vals'] if results[name][fn] else None
            pl, pg = wilcoxon_test(b, a) if b is not None and a is not None else (None, None)
            pvalues[name][fn] = (pl, pg)

    # w/t/l
    def wtl(other_name):
        w = t = l = 0
        for fn in FUNCS:
            base = results[macpo_name][fn]
            oth = results[other_name][fn]
            if base is None or oth is None:
                continue
            base_mean, oth_mean = base['mean'], oth['mean']
            pv = pvalues[other_name].get(fn)
            if pv is None:
                t += 1
                continue
            pl, pg = pv
            if oth_mean < base_mean and pl is not None and pl < 0.05:
                w += 1  # other wins
            elif oth_mean > base_mean and pg is not None and pg < 0.05:
                l += 1  # other loses
            else:
                t += 1
        return w, t, l

    # 生成 LaTeX
    algo_names = [macpo_name, 'RL\\_Only', 'RL-MACPO']
    n_cols = len(algo_names)

    lines = []
    lines.append(r'\begin{table}[htbp]')
    lines.append(r'\centering')
    lines.append(r'\caption{Comparison with MACPO (25 Runs, LLSO). Mean, median, std in separate rows. * significantly better than MACPO; \# significantly worse (Wilcoxon, $\alpha=0.05$).}')
    lines.append(r'\label{tab:macpo_style}')
    lines.append(r'\resizebox{\textwidth}{!}{%')
    lines.append(r'\begin{tabular}{l' + 'c' * n_cols + '}')
    lines.append(r'\hline')
    lines.append(r'\textbf{Function} & ' + ' & '.join(r'\textbf{' + n.replace('\\_', ' ') + '}' for n in algo_names) + r' \\')
    lines.append(r'\hline')

    for fn in FUNCS:
        lines.append(r'\multicolumn{' + str(n_cols + 1) + r'}{l}{\textit{' + fn + r'}} \\')
        # mean
        mean_row = 'mean'
        for name in algo_names:
            r = results[name].get(fn)
            mean_row += ' & ' + (fmt_sci(r['mean']) if r else '-')
        lines.append(mean_row + r' \\')
        # median
        med_row = 'median'
        for name in algo_names:
            r = results[name].get(fn)
            med_row += ' & ' + (fmt_sci(r['median']) if r else '-')
        lines.append(med_row + r' \\')
        # std
        std_row = 'std'
        for name in algo_names:
            r = results[name].get(fn)
            std_row += ' & ' + (fmt_sci(r['std']) if r else '-')
        lines.append(std_row + r' \\')
        # p-value (only for non-MACPO)
        pval_row = 'p-value'
        for name in algo_names:
            if name == macpo_name:
                pval_row += ' & -'
            else:
                pv = pvalues[name].get(fn)
                if pv is not None:
                    pl, pg = pv
                    s = f'{pl:.2e}'  # report p for "other better" test
                    if pl is not None and pl < 0.05:
                        s += '*'   # significantly better
                    elif pg is not None and pg < 0.05:
                        s += '\\#'  # significantly worse
                    pval_row += ' & ' + s
                else:
                    pval_row += ' & -'
        lines.append(pval_row + r' \\')
        lines.append(r'\hline')

    # w/t/l
    wtl_row = 'w/t/l'
    for name in algo_names:
        if name == macpo_name:
            wtl_row += ' & -'
        else:
            w, t, l = wtl(name)
            wtl_row += f' & {w}/{t}/{l}'
    lines.append(wtl_row + r' \\')
    lines.append(r'\hline')
    lines.append(r'\end{tabular}%')
    lines.append(r'}')
    lines.append(r'\end{table}')

    out = '\n'.join(lines)
    print(out)

    # 保存
    out_dir = Path(__file__).parent.parent / 'media' / 'media'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'table_macpo_style.tex'
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(out)
    print(f'\nSaved to {out_file}')


if __name__ == '__main__':
    main()
