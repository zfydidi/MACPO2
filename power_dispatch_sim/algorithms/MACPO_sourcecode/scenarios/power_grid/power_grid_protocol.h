#ifndef POWER_GRID_PROTOCOL_H
#define POWER_GRID_PROTOCOL_H

#include <mpi.h>
#include <vector>

#include "PowerGridBenchmarks.h"
#include "../ndo_common/ndo_sync.h"
#include "ieee_grid_registry.h"

/** 完整解 f_pure 报告间隔（降频 Allreduce；末轮仍单独汇总） */
static constexpr int kPowerGridReportInterval = 10;

/** 配对实验：至少每 K 轮强制一次完整协商（抑制边界漂移）；默认 K=3，IEEE30/57 用 K=2 */
inline int power_grid_force_comm_interval(IeeeGridCaseId id) {
    switch (id) {
    case IeeeGridCaseId::IEEE30:
    case IeeeGridCaseId::IEEE57:
        return 2;
    default:
        return 3;
    }
}

/** IEEE 电力场景优化预算（MACPO / RL-MACPO 配对须一致） */
struct PowerGridProtocol {
    double gen_per_d;
    int eva_per_d;
};

inline PowerGridProtocol power_grid_protocol(IeeeGridCaseId id) {
    switch (id) {
    case IeeeGridCaseId::IEEE14:
        return {2.0, 4000};
    case IeeeGridCaseId::IEEE30:
        return {2.0, 4000};
    case IeeeGridCaseId::IEEE57:
        return {2.0, 6000};
    case IeeeGridCaseId::IEEE118:
        return {2.5, 8000};
    default:
        return {2.0, 4000};
    }
}

/** 全员参与 assemble；仅 rank 0 计算并广播 f_pure（不计 eva_count） */
inline double power_grid_report_pure(
    PowerGridBenchmarks* pFunc, int myrank,
    double* report_buf, const double* global_best,
    const std::vector<int>& group_dims, int dimension) {
    assemble_global_best_for_report(report_buf, global_best, group_dims, dimension);
    double f_pure = 0.0;
    if (myrank == 0) {
        f_pure = pFunc->global_eva_report(report_buf);
    }
    MPI_Bcast(&f_pure, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    return f_pure;
}

#endif
