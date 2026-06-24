#ifndef MAED_MULTI_AREA_BENCHMARKS_H
#define MAED_MULTI_AREA_BENCHMARKS_H

/**
 * 2 区域 MAED（L2：验证多智能体 + 联络线耦合）
 *
 *   Rank 0: P_1..P_6 + T_01 (共享)
 *   Rank 1: P_7..P_13 + T_01 (共享，符号相反)
 *
 * 层 1: 区内平衡修复 + 阀点成本
 * 层 2: 联络线容量罚；一致性由 MACPO 协商 + 惩罚评估器保证
 */

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "../../Benchmarks/Benchmarks.h"
#include "maed_2area_data.h"
#include "maed_vpe_cost.h"
#include "maed_balance_repair.h"
#include "maed_area_redispatch.h"

class MaedMultiAreaBenchmarks : public Benchmarks {
    double load_mw;
    double demand[MAED2_NUM_AREAS];

    void area_units(int area, const int** idx_out, int* n_out,
                    const int** dim_out) const {
        if (area == 0) {
            *idx_out = maed2_area0_unit_idx;
            *n_out = MAED2_NUM_UNITS_AREA0;
            *dim_out = maed2_area0_gen_dims;
        } else {
            *idx_out = maed2_area1_unit_idx;
            *n_out = MAED2_NUM_UNITS_AREA1;
            *dim_out = maed2_area1_gen_dims;
        }
    }

    double tie_export_from_area(int area, const double* x) const {
        double T = x[MAED2_TIE_DIM];
        return (area == 0) ? T : -T;
    }

    double area_gen_cost(const double* x, int area) const {
        const int *unit_idx, *gen_dims;
        int n_units;
        area_units(area, &unit_idx, &n_units, &gen_dims);

        double total = 0.0;
        for (int k = 0; k < n_units; k++) {
            int d = gen_dims[k];
            double P = x[d];
            const MaedVpeUnit& u = maed13_units[unit_idx[k]];
            total += maed_vpe_unit_cost(P, u);
            total += maed_box_violation_penalty(P, u);
        }
        return total;
    }

    double tie_capacity_penalty(const double* x) const {
        double T = x[MAED2_TIE_DIM];
        double viol = std::fabs(T) - maed2_tie_max_mw;
        if (viol <= 0.0) return 0.0;
        return maed2_tie_penalty_lambda * viol * viol;
    }

    double eval_area(double* x, int area, bool count_eval) {
        if (x[MAED2_TIE_DIM] > maed2_tie_max_mw)
            x[MAED2_TIE_DIM] = maed2_tie_max_mw;
        if (x[MAED2_TIE_DIM] < -maed2_tie_max_mw)
            x[MAED2_TIE_DIM] = -maed2_tie_max_mw;

        const int *unit_idx, *gen_dims;
        int n_units;
        area_units(area, &unit_idx, &n_units, &gen_dims);

        std::vector<int> dims(gen_dims, gen_dims + n_units);
        double net_tie = tie_export_from_area(area, x);
        double effective_d = demand[area] + net_tie;

        const MaedVpeUnit* unit_table = (area == 0)
            ? maed13_units
            : (maed13_units + MAED2_NUM_UNITS_AREA0);

        maed_redispatch_area(x, dims, unit_table, n_units, std::max(0.0, effective_d));

        double residual = maed_repair_area_balance(
            x, dims, unit_table, n_units,
            MAED2_SLACK_LOCAL_IDX, demand[area], net_tie);

        double cost = area_gen_cost(x, area)
                    + maed_balance_penalty(residual, maed13_balance_lambda);

        if (area == 0)
            cost += tie_capacity_penalty(x) * 0.5;
        else
            cost += tie_capacity_penalty(x) * 0.5;

        if (count_eval) eva_count++;
        return cost;
    }

public:
    MaedMultiAreaBenchmarks() : Benchmarks(), load_mw(MAED13_DEFAULT_LOAD_MW) {
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

        const char* env = std::getenv("MAED_LOAD_MW");
        if (env && env[0] != '\0') load_mw = std::atof(env);
        for (int a = 0; a < MAED2_NUM_AREAS; a++)
            demand[a] = maed2_area_demand_mw(a, load_mw);
    }

    double local_eva(double* x, int groupIndex) override {
        if (groupIndex < 0 || groupIndex >= MAED2_NUM_AREAS) return 1e10;
        double work[MAED2_TOTAL_DIM];
        memcpy(work, x, sizeof(double) * MAED2_TOTAL_DIM);
        return eval_area(work, groupIndex, true);
    }

    double global_fitness(double* x) override {
        double total = 0.0;
        for (int a = 0; a < MAED2_NUM_AREAS; a++) {
            double work[MAED2_TOTAL_DIM];
            memcpy(work, x, sizeof(double) * MAED2_TOTAL_DIM);
            total += eval_area(work, a, false);
        }
        return total;
    }

    double global_eva(double* x) override {
        double total = 0.0;
        for (int a = 0; a < MAED2_NUM_AREAS; a++)
            total += local_eva(x, a);
        return total;
    }

    double getMinX() override { return maed2_min_x; }
    double getMaxX() override { return maed2_max_x; }
    int getGroupNum() override { return MAED2_NUM_AREAS; }
    int getDimension() override { return MAED2_TOTAL_DIM; }

    std::vector<int> getGroupDim(int g) override {
        std::vector<int> dims;
        if (g == 0) {
            for (int k = 0; k < MAED2_NUM_UNITS_AREA0; k++)
                dims.push_back(maed2_area0_gen_dims[k]);
            dims.push_back(MAED2_TIE_DIM);
        } else if (g == 1) {
            for (int k = 0; k < MAED2_NUM_UNITS_AREA1; k++)
                dims.push_back(maed2_area1_gen_dims[k]);
            dims.push_back(MAED2_TIE_DIM);
        }
        return dims;
    }

    std::vector<int> getGroupExcluDim(int g) override {
        std::vector<int> exclu;
        const int *unit_idx, *gen_dims;
        int n_units;
        area_units(g, &unit_idx, &n_units, &gen_dims);
        for (int k = 0; k < n_units; k++) exclu.push_back(gen_dims[k]);
        return exclu;
    }

    std::vector<int> getOverlapGroup(int g) override {
        std::vector<int> gr;
        for (int j = 0; j < 2; j++)
            if (maed2_overlap[g][j] >= 0) gr.push_back(maed2_overlap[g][j]);
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
