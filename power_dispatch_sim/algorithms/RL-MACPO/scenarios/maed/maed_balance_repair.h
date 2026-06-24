#ifndef MAED_BALANCE_REPAIR_H
#define MAED_BALANCE_REPAIR_H

/**
 * 单区 / 多区 MAED 功率平衡修复
 *
 * 选定 slack 机组吸收不平衡量: P_slack ← P_slack + (D + net_tie − Σ_{g≠s} P_g)
 * 再裁剪到 [Pmin, Pmax]。若仍不可行，返回平方残差供罚函数使用。
 */

#include <cmath>
#include <vector>
#include "maed_vpe_cost.h"

inline double maed_repair_area_balance(
    double* x,
    const std::vector<int>& gen_dims,
    const MaedVpeUnit* units,
    int num_units,
    int slack_local_idx,
    double demand_mw,
    double net_tie_export_mw)
{
  double sum_other = 0.0;
  for (int k = 0; k < num_units; k++) {
    if (k == slack_local_idx) continue;
    int d = gen_dims[k];
    maed_clamp_unit_power(x[d], units[k]);
    sum_other += x[d];
  }

  int slack_dim = gen_dims[slack_local_idx];
  const MaedVpeUnit& slack = units[slack_local_idx];
  double target = demand_mw + net_tie_export_mw - sum_other;
  x[slack_dim] = target;
  maed_clamp_unit_power(x[slack_dim], slack);

  double total = sum_other + x[slack_dim];
  double residual = total - demand_mw - net_tie_export_mw;
  return residual;
}

inline double maed_balance_penalty(double residual_mw, double lambda = 50.0) {
  return lambda * residual_mw * residual_mw;
}

#endif
