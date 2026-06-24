#!/usr/bin/env python3
"""
从 MACPO_original_output 聚合原始 MACPO 运行数据，生成 summary CSV
数据来源：MACPO_original_log/LLSO/F*/F*_LLSO_exp*.txt 或 LLSO_25runs/*.txt
"""
import os
import re
import csv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MACPO_LOG = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'MACPO_original_log', 'LLSO')
MACPO_RUNS = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'LLSO_25runs')
OUT_CSV = os.path.join(PROJECT_ROOT, 'MACPO_original_output', 'MACPO_LLSO_25runs_summary.csv')


def parse_from_log():
    """从 MACPO_original_log 解析"""
    results = {}
    for f in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']:
        vals = []
        d = os.path.join(MACPO_LOG, f)
        for i in range(1, 26):
            fn = os.path.join(d, f'{f}_LLSO_exp{i:02d}.txt')
            if os.path.exists(fn):
                with open(fn, encoding='utf-8') as fp:
                    for line in fp:
                        if 'Final Fitness' in line:
                            m = re.search(r'Final Fitness:\s*([0-9.eE+-]+)', line)
                            if m:
                                vals.append(float(m.group(1)))
                            break
        if vals:
            import numpy as np
            results[f] = (np.mean(vals), np.std(vals))
    return results


def parse_from_runs():
    """从 LLSO_25runs 解析：支持 F_MACPO_LLSO_25runs.txt 或 F_LLSO_run*.txt"""
    results = {}
    for f in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']:
        vals = []
        # 聚合文件
        fn = os.path.join(MACPO_RUNS, f'{f}_MACPO_LLSO_25runs.txt')
        if os.path.exists(fn):
            with open(fn, encoding='utf-8') as fp:
                for line in fp:
                    m = re.search(r'final fitness=([0-9.eE+-]+)', line)
                    if m:
                        vals.append(float(m.group(1)))
        # 或从单次运行文件解析
        if not vals and os.path.isdir(MACPO_RUNS):
            for i in range(1, 26):
                rfn = os.path.join(MACPO_RUNS, f'{f}_LLSO_run{i:02d}.txt')
                if os.path.exists(rfn):
                    with open(rfn, encoding='utf-8') as fp:
                        content = fp.read()
                    m = re.search(r'final fitness[=:]\s*([0-9.eE+-]+)', content)
                    if m:
                        vals.append(float(m.group(1)))
                    else:
                        # 最后一行的 f_penalty (第3列)
                        lines = [l for l in content.split('\n') if l and not l.startswith('#')]
                        for line in reversed(lines):
                            parts = line.split()
                            if len(parts) >= 3:
                                try:
                                    vals.append(float(parts[2]))
                                    break
                                except (ValueError, IndexError):
                                    pass
        if vals:
            import numpy as np
            results[f] = (np.mean(vals), np.std(vals))
    return results


def main():
    results = parse_from_runs() or parse_from_log()
    if not results:
        print('未找到 MACPO 原始数据')
        return
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['函数', 'F_mean', 'F_std'])
        for fn in ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']:
            if fn in results:
                m, s = results[fn]
                w.writerow([fn, f'{m:.6e}', f'{s:.6e}'])
    print(f'已写入 {OUT_CSV}')


if __name__ == '__main__':
    main()
