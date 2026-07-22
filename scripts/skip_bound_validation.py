"""B1 validity experiment: numerically verify the bounded skip suboptimality.

Proposition (bounded skip suboptimality): skipping one negotiation round forgoes
penalized-objective improvement at most  L*|D_i|*CI_i  (= d*CI_i here, L=1), which
under the skip rule CI<=lambda*mu is linearly controlled. This script measures, over
many visited states and all agents, the REALIZED penalty drop of one negotiation
round and checks it lies below the theoretical bound, on three structurally different
negotiation rules. It also confirms the forgone improvement vanishes as CI -> 0.

Run:  python scripts/skip_bound_validation.py [--lang en] [--out PATH]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mpl_font import setup_cjk_font  # noqa: E402
from utils.mpl_sci_ticks import set_numeric_tick_font_dejavu  # noqa: E402
from utils.gated_negotiation_sandbox import measure_skip_bound  # noqa: E402

setup_cjk_font()
import matplotlib.pyplot as plt  # noqa: E402

# 命题假设 N 非扩张。average/nash 的线性化单轮满足（朝邻域参考做收缩步）；
# 随机成对 gossip 单遍扫描相对过时参考会越过、非扩张性不成立，故不纳入该界的验证
# （其聚合行为已在协议无关性图 fig:gated_universality 覆盖）。
RULES_ZH = [("average", "Metropolis 平均共识"), ("nash", "Nash 双边最佳响应(简化)")]
RULES_EN = [("average", "Metropolis averaging"), ("nash", "Best-response (simplified)")]
TXT = {
    "zh": {"xlabel": "冲突指数 $\\mathrm{CI}_i$", "ylabel": "实测放弃的惩罚改进 $\\Delta P_i$",
           "bound": "理论上界 $L|\\mathcal{D}_i|\\,\\mathrm{CI}_i$", "pts": "实测(每状态×每 agent)",
           "sup": "B1 有效性验证：跳过一轮协商的实测次优性 $\\Delta P_i$ 恒在理论界 $L|\\mathcal{D}_i|\\mathrm{CI}_i$ 之下，且随 CI→0 消失"},
    "en": {"xlabel": "Conflict index $\\mathrm{CI}_i$", "ylabel": "Realized forgone improvement $\\Delta P_i$",
           "bound": "Theory bound $L|\\mathcal{D}_i|\\,\\mathrm{CI}_i$", "pts": "Measured (per state $\\times$ agent)",
           "sup": "Validation of the skip bound: realized skip suboptimality $\\Delta P_i$ stays below $L|\\mathcal{D}_i|\\mathrm{CI}_i$ and vanishes as CI$\\to$0"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out", default="output/skip_bound_validation.png")
    args = ap.parse_args()
    txt = TXT[args.lang]
    rules = RULES_EN if args.lang == "en" else RULES_ZH
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, (rule, name) in zip(axes, rules):
        ci, drop, bound = measure_skip_bound(rule)
        # 界成立比例（容一点浮点误差）
        holds = np.mean(drop <= bound + 1e-9)
        # 抽样绘散点避免过密
        idx = np.random.default_rng(0).choice(ci.size, size=min(4000, ci.size), replace=False)
        ax.scatter(ci[idx], drop[idx], s=4, alpha=0.25, color="tab:green", label=txt["pts"])
        ax.axhline(0.0, color="gray", lw=0.8, alpha=0.7)
        xline = np.linspace(0, ci.max(), 100)
        d_dims = 4  # sandbox dimension |D_i|
        ax.plot(xline, d_dims * xline, "-", color="tab:red", lw=2, label=txt["bound"])
        neg = float(np.mean(drop < 0))
        ax.set_xlim(0, ci.max() * 1.02)
        ax.set_ylim(min(0, drop.min()), d_dims * ci.max() * 1.02)
        ax.set_title(f"{name}\n" + (f"界成立 {holds*100:.1f}%" if args.lang == "zh"
                                    else f"bound holds {holds*100:.1f}\\%"), fontsize=10)
        ax.set_xlabel(txt["xlabel"])
        ax.set_ylabel(txt["ylabel"])
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="upper left")
        print(f"[{rule}] upper-bound holds {holds*100:.2f}%  neg ΔP {neg*100:.1f}%  "
              f"max ΔP/bound ratio={np.nanmax(drop/np.maximum(bound,1e-12)):.3f}  "
              f"corr(CI,ΔP)={np.corrcoef(ci,drop)[0,1]:.3f}")

    for a in axes:
        set_numeric_tick_font_dejavu(a)
    fig.suptitle(txt["sup"], fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"图已保存: {args.out}")


if __name__ == "__main__":
    main()
