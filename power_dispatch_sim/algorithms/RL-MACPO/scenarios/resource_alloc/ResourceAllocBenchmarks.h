#ifndef RESOURCE_ALLOC_BENCHMARKS_H
#define RESOURCE_ALLOC_BENCHMARKS_H

/**
 * 附录 V: 网络资源分配 (式 S1)
 *   min Σ_i ( U_i - (g_i + Σ_{j∈N_i} c_ij) )²
 */

#include <cmath>
#include <cstring>
#include <vector>
#include <algorithm>
#include "../../Benchmarks/Benchmarks.h"
#include "../ndo_common/chain_layout.h"
#include "resource_alloc_data.h"

class ResourceAllocBenchmarks : public Benchmarks {
    ChainLayout layout;
    double U[RA_NUM_NODES];

public:
    ResourceAllocBenchmarks() : Benchmarks(), layout(RA_NUM_NODES) {
        group_num = 0;
        if_rotate = if_shift = false;
        group = nullptr;
        xopt = nullptr;
        R = nullptr;
        W = nullptr;
        max_eva_times = 3000000;
        eva_count = 0;
        reach_max_eva_times = false;
        overlap_grouping = true;
        for (int i = 0; i < RA_NUM_NODES; i++) U[i] = ra_U[i];
    }

    double local_fitness_at(double* x, int groupIndex) const {
        if (groupIndex < 0 || groupIndex >= RA_NUM_NODES) return 1e10;
        double gap = layout.resource_balance_gap(x, groupIndex, U[groupIndex]);
        return gap * gap;
    }

    double local_eva(double* x, int groupIndex) override {
        eva_count++;
        return local_fitness_at(x, groupIndex);
    }

    double global_fitness(double* x) override {
        double total = 0.0;
        for (int r = 0; r < RA_NUM_NODES; r++) total += local_fitness_at(x, r);
        return total;
    }

    double global_eva(double* x) override {
        double total = 0.0;
        for (int r = 0; r < RA_NUM_NODES; r++) total += local_eva(x, r);
        return total;
    }

    double getMinX() override { return ra_min_x; }
    double getMaxX() override { return ra_max_x; }
    int getGroupNum() override { return RA_NUM_NODES; }
    int getDimension() override { return layout.total_dim; }

    std::vector<int> getGroupDim(int g) override {
        std::vector<int> dims;
        for (int j = 0; j < layout.region_dim_size[g]; j++)
            dims.push_back(layout.group_map[g][j]);
        return dims;
    }

    std::vector<int> getGroupExcluDim(int g) override {
        std::vector<int> exclu;
        for (int d : getGroupDim(g))
            if (d == ChainLayout::g_dim(g)) exclu.push_back(d);
        return exclu;
    }

    std::vector<int> getOverlapGroup(int g) override {
        std::vector<int> gr;
        for (int j = 0; j < 3; j++)
            if (layout.overlap_groups[g][j] >= 0)
                gr.push_back(layout.overlap_groups[g][j]);
        return gr;
    }

    std::vector<int> getOverlapDim(int g1, int g2) override {
        auto d1 = getGroupDim(g1), d2 = getGroupDim(g2);
        std::vector<int> ov;
        std::sort(d1.begin(), d1.end());
        std::sort(d2.begin(), d2.end());
        std::set_intersection(d1.begin(), d1.end(), d2.begin(), d2.end(),
                              std::back_inserter(ov));
        return ov;
    }

    std::vector<int> getOverlapDimIndex(int g1, int g2) override {
        auto ov = getOverlapDim(g1, g2);
        auto gd = getGroupDim(g1);
        std::vector<int> idx(ov.size());
        for (size_t i = 0; i < ov.size(); i++)
            for (size_t j = 0; j < gd.size(); j++)
                if (ov[i] == gd[j]) idx[i] = (int)j;
        return idx;
    }

    bool reachMaxEva() override {
        if (eva_count >= max_eva_times) {
            if (!reach_max_eva_times) reach_max_eva_times = true;
            return true;
        }
        return false;
    }
};

#endif
