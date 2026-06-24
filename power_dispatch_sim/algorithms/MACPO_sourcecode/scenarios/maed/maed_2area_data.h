#ifndef MAED_2AREA_DATA_H
#define MAED_2AREA_DATA_H

/**
 * 2 区域 MAED：13 机组拆分为 6 + 7，单条联络线耦合
 *
 *   Area 0: 机组 1–6  (global dim 0–5),  负荷 D0
 *   Area 1: 机组 7–13 (global dim 6–12), 负荷 D1
 *   共享:   dim 13 = T_01 (Area0 出口为正)
 *
 * 联络线容量、负荷按总负荷 MAED_LOAD_MW 比例分配（与 13 机组总容量成比例）。
 */

#include "maed_13gen_data.h"

#define MAED2_NUM_AREAS 2
#define MAED2_NUM_UNITS_AREA0 6
#define MAED2_NUM_UNITS_AREA1 7
#define MAED2_TIE_DIM 13
#define MAED2_TOTAL_DIM 14

/** 区域 0 机组在 maed13_units 中的索引 */
static const int maed2_area0_unit_idx[MAED2_NUM_UNITS_AREA0] = {0, 1, 2, 3, 4, 5};
/** 区域 1 机组索引 */
static const int maed2_area1_unit_idx[MAED2_NUM_UNITS_AREA1] = {6, 7, 8, 9, 10, 11, 12};

static const int maed2_area0_gen_dims[MAED2_NUM_UNITS_AREA0] = {0, 1, 2, 3, 4, 5};
static const int maed2_area1_gen_dims[MAED2_NUM_UNITS_AREA1] = {6, 7, 8, 9, 10, 11, 12};

/** 邻区表: area0 ↔ area1 */
static const int maed2_overlap[MAED2_NUM_AREAS][2] = {
    {1, -1},
    {0, -1},
};

static const double maed2_tie_max_mw = 200.0;
static const double maed2_tie_penalty_lambda = 80.0;
static const double maed2_min_x = 0.0;
static const double maed2_max_x = 680.0;

/** Area0 slack = 本地第 0 台 (global unit 0); Area1 slack = 本地第 0 台 (global unit 6) */
#define MAED2_SLACK_LOCAL_IDX 0

inline double maed2_area_capacity_mw(int area) {
  double cap = 0.0;
  if (area == 0) {
    for (int k = 0; k < MAED2_NUM_UNITS_AREA0; k++)
      cap += maed13_units[maed2_area0_unit_idx[k]].Pmax;
  } else {
    for (int k = 0; k < MAED2_NUM_UNITS_AREA1; k++)
      cap += maed13_units[maed2_area1_unit_idx[k]].Pmax;
  }
  return cap;
}

inline double maed2_area_demand_mw(int area, double total_load_mw) {
  double c0 = maed2_area_capacity_mw(0);
  double c1 = maed2_area_capacity_mw(1);
  double frac = (area == 0) ? (c0 / (c0 + c1)) : (c1 / (c0 + c1));
  return total_load_mw * frac;
}

#endif
