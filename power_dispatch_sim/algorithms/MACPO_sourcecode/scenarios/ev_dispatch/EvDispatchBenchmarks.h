#ifndef EV_DISPATCH_BENCHMARKS_H
#define EV_DISPATCH_BENCHMARKS_H

/**
 * 附录 VI: 电动汽车充电站电力调度 (式 S2 + Algorithm S1)
 *   min Σ_i [ f_product(g_i) + Σ_j f_deal(c_ij) - f_gain(supply) ]
 */

#include <algorithm>
#include <cmath>
#include <cstring>
#include <vector>
#include "../../Benchmarks/Benchmarks.h"
#include "../ndo_common/chain_layout.h"
#include "ev_dispatch_data.h"

class EvDispatchBenchmarks : public Benchmarks {
    ChainLayout layout;

    static double R_loss(double Q, double m) {
        return Q * Q - (m + 1.0) * Q + m;
    }

    /** Algorithm S1 + S3/S4: 演化博弈求 f_gain */
    static double compute_fgain(double supply, int station) {
        if (supply <= 1e-9) return 0.0;

        double p_sell = ev_a[station];
        double Qk[EV_NUM_VEHICLES];
        for (int k = 0; k < EV_NUM_VEHICLES; k++)
            Qk[k] = 0.0;

        for (int t = 0; t < ev_price_max_iter; t++) {
            double total_q = 0.0;
            for (int k = 0; k < EV_NUM_VEHICLES; k++) {
                double Q0 = ev_Q0[station][k];
                double lo = -Q0;
                double hi = 1.0 - Q0;
                double opt = 0.5 * ((ev_m + 1.0) - 2.0 * Q0 - p_sell);
                if (opt < lo) opt = lo;
                if (opt > hi) opt = hi;
                Qk[k] = opt;
                total_q += Qk[k];
            }

            double p_new = p_sell;
            if (total_q > supply + 1e-8)
                p_new = p_sell + ev_price_eps;
            else if (total_q < supply - 1e-8)
                p_new = p_sell - ev_price_eps;
            if (std::fabs(p_new - p_sell) < 1e-7) break;
            p_sell = std::max(ev_a[station] * 0.5, p_new);
        }

        double sum_q = 0.0;
        for (int k = 0; k < EV_NUM_VEHICLES; k++) sum_q += Qk[k];
        return p_sell * sum_q;
    }

    static double deal_cost(double c_signed) {
        return ev_p1 * (1.0 + ev_alpha * ev_L) * std::fabs(c_signed);
    }

public:
    EvDispatchBenchmarks() : Benchmarks(), layout(EV_NUM_NODES) {
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
    }

    double local_fitness_at(double* x, int groupIndex) const {
        if (groupIndex < 0 || groupIndex >= EV_NUM_NODES) return 1e10;

        double gi = layout.production_at(x, groupIndex);
        double f_prod = ev_a[groupIndex] * gi;

        double f_deal = 0.0;
        if (groupIndex > 0)
            f_deal += deal_cost(-x[ChainLayout::e_dim(groupIndex - 1)]);
        if (groupIndex < EV_NUM_NODES - 1)
            f_deal += deal_cost(x[ChainLayout::e_dim(groupIndex)]);

        double supply = gi + layout.signed_net_inflow(x, groupIndex);
        double f_gain = compute_fgain(std::max(0.0, supply), groupIndex);
        return f_prod + f_deal - f_gain;
    }

    double local_eva(double* x, int groupIndex) override {
        eva_count++;
        return local_fitness_at(x, groupIndex);
    }

    double global_fitness(double* x) override {
        double total = 0.0;
        for (int r = 0; r < EV_NUM_NODES; r++) total += local_fitness_at(x, r);
        return total;
    }

    double global_eva(double* x) override {
        double total = 0.0;
        for (int r = 0; r < EV_NUM_NODES; r++) total += local_eva(x, r);
        return total;
    }

    double getMinX() override { return ev_min_x; }
    double getMaxX() override { return ev_max_x; }
    int getGroupNum() override { return EV_NUM_NODES; }
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
