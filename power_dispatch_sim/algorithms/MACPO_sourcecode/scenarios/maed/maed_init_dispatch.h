#ifndef MAED_INIT_DISPATCH_H
#define MAED_INIT_DISPATCH_H

/**
 * MAED 可行初值：按机组容量比例分摊负荷，slack 修复平衡，联络线 T=0。
 */

#include <cstdlib>
#include <cstring>
#include <string>
#include "maed_13gen_data.h"
#include "maed_2area_data.h"
#include "maed_balance_repair.h"
#include "maed_vpe_cost.h"

inline double maed_load_mw_from_env() {
    const char* env = std::getenv("MAED_LOAD_MW");
    if (env && env[0] != '\0') return std::atof(env);
    return MAED13_DEFAULT_LOAD_MW;
}

/** 单区 13 机组：按 Pmax 比例分配总负荷 */
inline void maed13_init_feasible(double* x, double load_mw) {
    double cap_sum = 0.0;
    for (int g = 0; g < MAED13_NUM_UNITS; g++)
        cap_sum += maed13_units[g].Pmax;

    for (int g = 0; g < MAED13_NUM_UNITS; g++) {
        double P = load_mw * maed13_units[g].Pmax / cap_sum;
        maed_clamp_unit_power(P, maed13_units[g]);
        x[g] = P;
    }

    std::vector<int> dims(MAED13_NUM_UNITS);
    for (int g = 0; g < MAED13_NUM_UNITS; g++) dims[g] = g;
    maed_repair_area_balance(x, dims, maed13_units, MAED13_NUM_UNITS,
                             MAED13_SLACK_IDX, load_mw, 0.0);
}

/** 2 区 MAED：区内按比例分配，T_01=0 */
inline void maed2_init_feasible(double* x, double load_mw) {
  for (int g = 0; g < MAED2_TIE_DIM; g++) x[g] = 0.0;
  x[MAED2_TIE_DIM] = 0.0;

  for (int area = 0; area < MAED2_NUM_AREAS; area++) {
    const int *unit_idx, *gen_dims;
    int n_units;
    if (area == 0) {
      unit_idx = maed2_area0_unit_idx;
      gen_dims = maed2_area0_gen_dims;
      n_units = MAED2_NUM_UNITS_AREA0;
    } else {
      unit_idx = maed2_area1_unit_idx;
      gen_dims = maed2_area1_gen_dims;
      n_units = MAED2_NUM_UNITS_AREA1;
    }

    double demand = maed2_area_demand_mw(area, load_mw);
    double cap = maed2_area_capacity_mw(area);
    for (int k = 0; k < n_units; k++) {
      const MaedVpeUnit& u = maed13_units[unit_idx[k]];
      double P = demand * u.Pmax / cap;
      maed_clamp_unit_power(P, u);
      x[gen_dims[k]] = P;
    }

    std::vector<int> dims(gen_dims, gen_dims + n_units);
    const MaedVpeUnit* unit_table = (area == 0)
        ? maed13_units
        : (maed13_units + MAED2_NUM_UNITS_AREA0);
    maed_repair_area_balance(x, dims, unit_table, n_units,
                             MAED2_SLACK_LOCAL_IDX, demand, 0.0);
  }
}

inline void maed_init_dispatch_if_needed(const std::string& scenario,
                                         double* x, int dimension) {
    double load = maed_load_mw_from_env();
    if (scenario == "MAED13" || scenario == "VPE13") {
        if (dimension != MAED13_TOTAL_DIM) return;
        maed13_init_feasible(x, load);
    } else if (scenario == "MAED2" || scenario == "MAED2AREA") {
        if (dimension != MAED2_TOTAL_DIM) return;
        maed2_init_feasible(x, load);
    }
}

#endif
