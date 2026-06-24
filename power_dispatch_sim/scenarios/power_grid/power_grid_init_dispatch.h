#ifndef POWER_GRID_INIT_DISPATCH_H
#define POWER_GRID_INIT_DISPATCH_H

/**
 * IEEE 电力场景可行初值：按机组容量比例分摊总负荷，联络线置 0。
 * 各 rank 本地独立计算（确定性），用于 globalBest 与种群种子。
 */
#include <algorithm>
#include <cstring>
#include <vector>

#include "ieee_grid_registry.h"
#include "../../components/optimizer.h"

inline void power_grid_init_feasible(const IeeeGridCaseDesc* desc, double* x) {
    if (!desc || !x) return;
    std::memset(x, 0, desc->total_dim * sizeof(double));

    double total_demand = 0.0;
    for (int r = 0; r < desc->n_regions; r++) {
        total_demand += desc->region_demand[r];
    }
    double total_pmax = 0.0;
    for (int g = 0; g < desc->n_gens; g++) {
        total_pmax += desc->generators[g].Pmax;
    }
    if (total_pmax <= 0.0) total_pmax = 1.0;

    for (int g = 0; g < desc->n_gens; g++) {
        const GenData& gen = desc->generators[g];
        double P = total_demand * gen.Pmax / total_pmax;
        if (P < gen.Pmin) P = gen.Pmin;
        if (P > gen.Pmax) P = gen.Pmax;
        x[g] = P;
    }
    for (int t = 0; t < desc->n_ties; t++) {
        x[desc->tielines[t].global_dim] = 0.0;
    }
}

/** 将可行初值写入前 10% 粒子（至少 1 个）的自有维度 */
inline void power_grid_seed_swarm_from_feasible(optimizer* opt,
                                              const double* x_full,
                                              const std::vector<int>& group_dims) {
    if (!opt || !x_full || group_dims.empty() || opt->swarm.empty()) return;
    int n_seed = std::max(1, opt->swarmSize / 10);
    n_seed = std::min(n_seed, (int)opt->swarm.size());
    for (int p = 0; p < n_seed; p++) {
        for (int d : group_dims) {
            opt->swarm[p]->X[d] = x_full[d];
        }
    }
}

#endif
