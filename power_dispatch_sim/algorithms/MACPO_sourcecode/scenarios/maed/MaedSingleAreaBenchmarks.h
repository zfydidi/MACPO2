#ifndef MAED_SINGLE_AREA_BENCHMARKS_H
#define MAED_SINGLE_AREA_BENCHMARKS_H

/**
 * 单区域 13 机组 VPE-ED（L1 benchmark：验证非凸搜索能力）
 *
 * 1 个 MPI rank / 1 个 agent，13 维私有变量，无共享维。
 * 功率平衡: 修复 + 罚函数；箱约束: clamp + 软罚。
 */

#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
#include "../../Benchmarks/Benchmarks.h"
#include "maed_13gen_data.h"
#include "maed_vpe_cost.h"
#include "maed_balance_repair.h"

class MaedSingleAreaBenchmarks : public Benchmarks {
    double load_mw;

    double unit_cost_sum(const double* x) const {
        double total = 0.0;
        for (int g = 0; g < MAED13_NUM_UNITS; g++) {
            double P = x[g];
            total += maed_vpe_unit_cost(P, maed13_units[g]);
            total += maed_box_violation_penalty(P, maed13_units[g]);
        }
        return total;
    }

    double eval_with_repair(double* x, bool count_eval) {
        double work[MAED13_TOTAL_DIM];
        memcpy(work, x, sizeof(double) * MAED13_TOTAL_DIM);

        std::vector<int> dims(MAED13_NUM_UNITS);
        for (int g = 0; g < MAED13_NUM_UNITS; g++) dims[g] = g;

        double residual = maed_repair_area_balance(
            work, dims, maed13_units, MAED13_NUM_UNITS,
            MAED13_SLACK_IDX, load_mw, 0.0);

        double cost = unit_cost_sum(work) + maed_balance_penalty(residual, maed13_balance_lambda);
        if (count_eval) eva_count++;
        return cost;
    }

public:
    MaedSingleAreaBenchmarks() : Benchmarks(), load_mw(MAED13_DEFAULT_LOAD_MW) {
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
    }

    double local_eva(double* x, int groupIndex) override {
        if (groupIndex != 0) return 1e10;
        return eval_with_repair(x, true);
    }

    double global_fitness(double* x) override {
        return eval_with_repair(x, false);
    }

    double global_eva(double* x) override {
        return local_eva(x, 0);
    }

    double getMinX() override { return maed13_min_x; }
    double getMaxX() override { return maed13_max_x; }
    int getGroupNum() override { return 1; }
    int getDimension() override { return MAED13_TOTAL_DIM; }

    std::vector<int> getGroupDim(int g) override {
        std::vector<int> dims;
        if (g != 0) return dims;
        for (int i = 0; i < MAED13_TOTAL_DIM; i++) dims.push_back(i);
        return dims;
    }

    std::vector<int> getGroupExcluDim(int g) override {
        return getGroupDim(g);
    }

    std::vector<int> getOverlapGroup(int) override {
        return {};
    }

    std::vector<int> getOverlapDim(int, int) override {
        return {};
    }

    std::vector<int> getOverlapDimIndex(int, int) override {
        return {};
    }

    bool reachMaxEva() override {
        if (eva_count >= max_eva_times) {
            if (!reach_max_eva_times) reach_max_eva_times = true;
            return true;
        }
        return false;
    }

    double get_load_mw() const { return load_mw; }
};

#endif
