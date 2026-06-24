// AUTO-GENERATED registry
#include <cstring>

#ifndef IEEE_GRID_REGISTRY_H
#define IEEE_GRID_REGISTRY_H

#include "ieee_grid_types.h"
#include "generated/ieee14bus_data.h"
#include "generated/ieee30bus_data.h"
#include "generated/ieee57bus_data.h"
#include "generated/ieee118bus_data.h"

enum class IeeeGridCaseId { IEEE14, IEEE30, IEEE57, IEEE118, UNKNOWN };

struct IeeeGridCaseDesc {
    IeeeGridCaseId id;
    const char* name;
    const char* label;
    int n_regions;
    int n_gens;
    int n_ties;
    int total_dim;
    const GenData* generators;
    const double* region_demand;
    const int* region_dim_sizes;
    const int* region_dims;      // flat [n_regions * max_local]
    int region_dims_stride;
    const TieLine* tielines;
    const int* overlap_groups;   // flat [n_regions * overlap_stride]
    int overlap_stride;
    const int* gen_region;
    double min_x;
    double max_x;
};

static const IeeeGridCaseDesc kCase_IEEE14 = {
    IeeeGridCaseId::IEEE14,
    "IEEE14",
    "IEEE 14-bus Economic Dispatch",
    IEEE14_NUM_REGIONS,
    IEEE14_NUM_GENERATORS,
    IEEE14_NUM_TIELINES,
    IEEE14_TOTAL_DIM,
    ieee14_generators,
    ieee14_region_demand,
    ieee14_region_dim_sizes,
    &ieee14_region_dims[0][0],
    4,
    ieee14_tielines,
    &ieee14_overlap_groups[0][0],
    3,
    ieee14_gen_region,
    ieee14_min_x,
    ieee14_max_x,
};

static const IeeeGridCaseDesc kCase_IEEE30 = {
    IeeeGridCaseId::IEEE30,
    "IEEE30",
    "IEEE 30-bus Economic Dispatch",
    IEEE30_NUM_REGIONS,
    IEEE30_NUM_GENERATORS,
    IEEE30_NUM_TIELINES,
    IEEE30_TOTAL_DIM,
    ieee30_generators,
    ieee30_region_demand,
    ieee30_region_dim_sizes,
    &ieee30_region_dims[0][0],
    5,
    ieee30_tielines,
    &ieee30_overlap_groups[0][0],
    4,
    ieee30_gen_region,
    ieee30_min_x,
    ieee30_max_x,
};

static const IeeeGridCaseDesc kCase_IEEE57 = {
    IeeeGridCaseId::IEEE57,
    "IEEE57",
    "IEEE 57-bus Economic Dispatch",
    IEEE57_NUM_REGIONS,
    IEEE57_NUM_GENERATORS,
    IEEE57_NUM_TIELINES,
    IEEE57_TOTAL_DIM,
    ieee57_generators,
    ieee57_region_demand,
    ieee57_region_dim_sizes,
    &ieee57_region_dims[0][0],
    4,
    ieee57_tielines,
    &ieee57_overlap_groups[0][0],
    3,
    ieee57_gen_region,
    ieee57_min_x,
    ieee57_max_x,
};

static const IeeeGridCaseDesc kCase_IEEE118 = {
    IeeeGridCaseId::IEEE118,
    "IEEE118",
    "IEEE 118-bus Economic Dispatch",
    IEEE118_NUM_REGIONS,
    IEEE118_NUM_GENERATORS,
    IEEE118_NUM_TIELINES,
    IEEE118_TOTAL_DIM,
    ieee118_generators,
    ieee118_region_demand,
    ieee118_region_dim_sizes,
    &ieee118_region_dims[0][0],
    20,
    ieee118_tielines,
    &ieee118_overlap_groups[0][0],
    5,
    ieee118_gen_region,
    ieee118_min_x,
    ieee118_max_x,
};

inline IeeeGridCaseId parse_ieee_grid_case(const char* s) {
    if (!s) return IeeeGridCaseId::UNKNOWN;
    if (strcmp(s, "IEEE14") == 0 || strcmp(s, "POWER14") == 0) return IeeeGridCaseId::IEEE14;
    if (strcmp(s, "IEEE30") == 0 || strcmp(s, "POWER30") == 0) return IeeeGridCaseId::IEEE30;
    if (strcmp(s, "IEEE57") == 0 || strcmp(s, "POWER57") == 0) return IeeeGridCaseId::IEEE57;
    if (strcmp(s, "IEEE118") == 0 || strcmp(s, "POWER118") == 0) return IeeeGridCaseId::IEEE118;
    return IeeeGridCaseId::UNKNOWN;
}

inline const IeeeGridCaseDesc* ieee_grid_case_desc(IeeeGridCaseId id) {
    switch (id) {
    case IeeeGridCaseId::IEEE14: return &kCase_IEEE14;
    case IeeeGridCaseId::IEEE30: return &kCase_IEEE30;
    case IeeeGridCaseId::IEEE57: return &kCase_IEEE57;
    case IeeeGridCaseId::IEEE118: return &kCase_IEEE118;
    default: return nullptr;
    }
}

#endif