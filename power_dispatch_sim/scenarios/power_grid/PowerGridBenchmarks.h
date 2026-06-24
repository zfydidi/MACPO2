#ifndef POWER_GRID_BENCHMARKS_H
#define POWER_GRID_BENCHMARKS_H

/**
 * PowerGridBenchmarks — IEEE 标准算例区域互联经济调度（连续 ED，非机组组合 UC）
 *
 * 区域功率平衡 + 联络线决策变量（非 DC 潮流 B·θ 模型）。
 * 支持 IEEE 14 / 30 / 57 / 118（MATPOWER case 数据，见 generated 目录）
 * 每个 MPI rank = 一个控制区域；共享维 = 区域间联络线功率。
 */

#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <algorithm>
#include "../../Benchmarks/Benchmarks.h"
#include "ieee_grid_registry.h"

using std::vector;

class PowerGridBenchmarks : public Benchmarks {
private:
    const IeeeGridCaseDesc* case_desc;

    struct TieInfo {
        int global_dim;
        int sign;
    };

    int region_dim_size[32];
    int** group_map;
    vector<TieInfo> region_ties[32];

    static constexpr double w_balance = 1000.0;
    static constexpr double w_tie_cap  = 80.0;
    double best_fitness;

    double tie_eval_cap(const TieLine& tl) const {
        double cap = (tl.Pmax > 0.0) ? tl.Pmax : 200.0;
        if (case_desc->id == IeeeGridCaseId::IEEE14 && cap > 100.0) {
            cap = 100.0;
        }
        return cap;
    }

    static double clamp_tie_flow(double raw, double cap) {
        if (raw > cap) return cap;
        if (raw < -cap) return -cap;
        return raw;
    }

    double tie_flow_for_balance(int global_dim, const double* x) const {
        for (int t = 0; t < case_desc->n_ties; t++) {
            const TieLine& tl = case_desc->tielines[t];
            if (tl.global_dim == global_dim) {
                return clamp_tie_flow(x[global_dim], tie_eval_cap(tl));
            }
        }
        return x[global_dim];
    }

    double tie_capacity_penalty(const double* x) const {
        double pen = 0.0;
        for (int t = 0; t < case_desc->n_ties; t++) {
            const TieLine& tl = case_desc->tielines[t];
            int d = tl.global_dim;
            double cap = tie_eval_cap(tl);
            double viol = std::fabs(x[d]) - cap;
            if (viol > 0.0)
                pen += w_tie_cap * viol * viol;
        }
        return pen;
    }

    static double gen_cost(double P_G, const GenData& gen) {
        if (P_G < gen.Pmin) {
            double viol = gen.Pmin - P_G;
            return gen.a * gen.Pmin * gen.Pmin + gen.b * gen.Pmin + gen.c
                   + 500.0 * viol * viol;
        }
        if (P_G > gen.Pmax) {
            double viol = P_G - gen.Pmax;
            return gen.a * gen.Pmax * gen.Pmax + gen.b * gen.Pmax + gen.c
                   + 500.0 * viol * viol;
        }
        return gen.a * P_G * P_G + gen.b * P_G + gen.c;
    }

    const int* region_dims_row(int r) const {
        return case_desc->region_dims + r * case_desc->region_dims_stride;
    }

    const int* overlap_row(int r) const {
        return case_desc->overlap_groups + r * case_desc->overlap_stride;
    }

    void init_ties() {
        for (int r = 0; r < case_desc->n_regions; r++) {
            region_ties[r].clear();
            for (int t = 0; t < case_desc->n_ties; t++) {
                const TieLine& tl = case_desc->tielines[t];
                if (tl.region_from == r || tl.region_to == r) {
                    TieInfo info;
                    info.global_dim = tl.global_dim;
                    info.sign = (tl.region_from == r) ? 1 : -1;
                    region_ties[r].push_back(info);
                }
            }
        }
    }

public:
    explicit PowerGridBenchmarks(IeeeGridCaseId id)
        : Benchmarks(), case_desc(ieee_grid_case_desc(id))
    {
        if (!case_desc) {
            case_desc = ieee_grid_case_desc(IeeeGridCaseId::IEEE14);
        }

        group_num = 0;
        if_rotate = false;
        if_shift  = false;
        group     = nullptr;
        xopt      = nullptr;
        R         = nullptr;
        W         = nullptr;

        max_eva_times       = 3000000;
        eva_count           = 0;
        reach_max_eva_times = false;
        overlap_grouping    = true;
        best_fitness        = 1e10;

        for (int r = 0; r < case_desc->n_regions; r++) {
            region_dim_size[r] = case_desc->region_dim_sizes[r];
        }

        group_map = new int*[case_desc->n_regions];
        for (int r = 0; r < case_desc->n_regions; r++) {
            group_map[r] = new int[region_dim_size[r]];
            const int* row = region_dims_row(r);
            for (int j = 0; j < region_dim_size[r]; j++) {
                group_map[r][j] = row[j];
            }
        }
        init_ties();
    }

    ~PowerGridBenchmarks() override {
        if (!case_desc) return;
        for (int r = 0; r < case_desc->n_regions; r++) {
            delete[] group_map[r];
        }
        delete[] group_map;
    }

    const IeeeGridCaseDesc* descriptor() const { return case_desc; }

    double local_eva(double* x, int groupIndex) override {
        if (!case_desc || groupIndex < 0 || groupIndex >= case_desc->n_regions)
            return 1e10;

        if (region_dim_size[groupIndex] <= 0)
            return 0.0;

        double total_gen_cost = 0.0;
        double total_gen_pow  = 0.0;

        for (int j = 0; j < region_dim_size[groupIndex]; j++) {
            int d = group_map[groupIndex][j];
            if (d < case_desc->n_gens) {
                const GenData& gen = case_desc->generators[d];
                if (case_desc->gen_region[d] != groupIndex)
                    continue;
                double P_G = x[d];
                total_gen_cost += gen_cost(P_G, gen);
                double P_eff = P_G;
                if (P_eff < gen.Pmin) P_eff = gen.Pmin;
                if (P_eff > gen.Pmax) P_eff = gen.Pmax;
                total_gen_pow += P_eff;
            }
        }

        double net_export = 0.0;
        for (const TieInfo& ti : region_ties[groupIndex]) {
            net_export += ti.sign * tie_flow_for_balance(ti.global_dim, x);
        }

        double imbalance = total_gen_pow - case_desc->region_demand[groupIndex] - net_export;
        double cost = total_gen_cost + w_balance * imbalance * imbalance
                      + tie_capacity_penalty(x) / case_desc->n_regions;

        eva_count += 1;
        return cost;
    }

    double global_eva(double* x) override {
        double total = 0.0;
        for (int r = 0; r < case_desc->n_regions; r++) {
            total += local_eva(x, r);
        }
        return total;
    }

    /** 报告专用：汇总全区纯目标，不占用优化器 eva_count 预算 */
    double global_eva_report(double* x) {
        int saved = eva_count;
        double total = 0.0;
        for (int r = 0; r < case_desc->n_regions; r++) {
            total += local_eva(x, r);
        }
        eva_count = saved;
        return total;
    }

    double getMinX() override { return case_desc->min_x; }
    double getMaxX() override { return case_desc->max_x; }
    int    getGroupNum() override { return case_desc->n_regions; }
    int    getDimension() override { return case_desc->total_dim; }

    vector<int> getGroupDim(int groupIndex) override {
        vector<int> dims;
        for (int j = 0; j < region_dim_size[groupIndex]; j++) {
            dims.push_back(group_map[groupIndex][j]);
        }
        return dims;
    }

    vector<int> getGroupExcluDim(int groupIndex) override {
        vector<int> all_dims   = getGroupDim(groupIndex);
        vector<int> overlap_grp = getOverlapGroup(groupIndex);
        vector<int> exclu;
        for (int d : all_dims) {
            bool is_shared = false;
            for (int og : overlap_grp) {
                vector<int> ov = getOverlapDim(groupIndex, og);
                if (std::find(ov.begin(), ov.end(), d) != ov.end()) {
                    is_shared = true;
                    break;
                }
            }
            if (!is_shared) exclu.push_back(d);
        }
        return exclu;
    }

    vector<int> getOverlapGroup(int groupIndex) override {
        vector<int> groups;
        const int* row = overlap_row(groupIndex);
        for (int j = 0; j < case_desc->overlap_stride; j++) {
            if (row[j] >= 0) groups.push_back(row[j]);
        }
        return groups;
    }

    vector<int> getOverlapDim(int g1, int g2) override {
        vector<int> dim1 = getGroupDim(g1);
        vector<int> dim2 = getGroupDim(g2);
        vector<int> overlap;
        std::sort(dim1.begin(), dim1.end());
        std::sort(dim2.begin(), dim2.end());
        std::set_intersection(dim1.begin(), dim1.end(),
                              dim2.begin(), dim2.end(),
                              std::back_inserter(overlap));
        return overlap;
    }

    vector<int> getOverlapDimIndex(int g1, int g2) override {
        vector<int> overlap    = getOverlapDim(g1, g2);
        vector<int> group_dim  = getGroupDim(g1);
        vector<int> dim_index;
        dim_index.resize(overlap.size());
        for (size_t i = 0; i < overlap.size(); i++) {
            for (size_t j = 0; j < group_dim.size(); j++) {
                if (overlap[i] == group_dim[j]) {
                    dim_index[i] = (int)j;
                    break;
                }
            }
        }
        return dim_index;
    }

    double getBestFitness() override { return best_fitness; }

    bool reachMaxEva() override {
        if (eva_count >= max_eva_times) {
            if (!reach_max_eva_times) reach_max_eva_times = true;
            return true;
        }
        return false;
    }
};

inline PowerGridBenchmarks* create_power_grid_benchmark(const std::string& name) {
    IeeeGridCaseId id = parse_ieee_grid_case(name.c_str());
    if (id == IeeeGridCaseId::UNKNOWN) return nullptr;
    return new PowerGridBenchmarks(id);
}

#endif
