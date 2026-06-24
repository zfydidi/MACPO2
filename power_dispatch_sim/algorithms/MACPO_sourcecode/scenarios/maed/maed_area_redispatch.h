#ifndef MAED_AREA_REDISPATCH_H
#define MAED_AREA_REDISPATCH_H

/**
 * 按有效需求 effective = D + net_tie 在区内按比例分配出力，再由 slack 微调。
 */

#include <vector>
#include "maed_vpe_cost.h"

inline void maed_redispatch_area(
    double* x,
    const std::vector<int>& gen_dims,
    const MaedVpeUnit* units,
    int n_units,
    double effective_demand_mw)
{
    if (n_units <= 0 || effective_demand_mw < 0.0) return;

    double cap_sum = 0.0;
    for (int k = 0; k < n_units; k++) cap_sum += units[k].Pmax;

    for (int k = 0; k < n_units; k++) {
        double P = (cap_sum > 0.0)
            ? effective_demand_mw * units[k].Pmax / cap_sum
            : 0.0;
        maed_clamp_unit_power(P, units[k]);
        x[gen_dims[k]] = P;
    }
}

#endif
