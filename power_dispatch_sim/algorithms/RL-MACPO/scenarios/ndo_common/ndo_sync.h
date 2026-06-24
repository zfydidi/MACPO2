#ifndef NDO_SYNC_H
#define NDO_SYNC_H

/**
 * 附录 V/VI 配对实验：在 MACPO 与 RL-MACPO 间同步全局解快照。
 */
#include <mpi.h>
#include <vector>
#include "../../Benchmarks/Benchmarks.h"

inline void merge_local_best(double* global_best, const double* local_best,
                             const std::vector<int>& group_dims) {
    for (int d : group_dims) global_best[d] = local_best[d];
}

/** 未协商时，对共享边变量与邻居取算术平均，供 f_pure 记录用 */
inline void sync_overlap_average(double* x, Benchmarks* pFunc, int myrank) {
    MPI_Status stat;
    std::vector<int> neighbors = pFunc->getOverlapGroup(myrank);
    for (int nb : neighbors) {
        std::vector<int> ov = pFunc->getOverlapDim(myrank, nb);
        if (ov.empty()) continue;
        int n = (int)ov.size();
        double* mine = new double[n];
        double* theirs = new double[n];
        for (int i = 0; i < n; i++) mine[i] = x[ov[i]];
        MPI_Sendrecv(mine, n, MPI_DOUBLE, nb, 77, theirs, n, MPI_DOUBLE, nb, 77,
                     MPI_COMM_WORLD, &stat);
        for (int i = 0; i < n; i++) x[ov[i]] = 0.5 * (mine[i] + theirs[i]);
        delete[] mine;
        delete[] theirs;
    }
}

/**
 * 汇总各 rank 自有维度，得到完整 globalBest 供 global_eva 报告。
 * 各 rank 的 global_best 仅维护本地维 + 协商后的联络线维，其他区发电机维为 0；
 * 直接 global_eva(global_best) 会对未拥有维施加虚假平衡罚。
 */
inline void assemble_global_best_for_report(double* full_out, const double* global_best,
                                            const std::vector<int>& group_dims, int dimension) {
    std::vector<double> my_view(dimension, 0.0);
    std::vector<double> count_view(dimension, 0.0);
    for (int d : group_dims) {
        my_view[d] = global_best[d];
        count_view[d] = 1.0;
    }
    std::vector<double> acc(dimension, 0.0);
    std::vector<double> counts(dimension, 0.0);
    MPI_Allreduce(my_view.data(), acc.data(), dimension, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(count_view.data(), counts.data(), dimension, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
    for (int d = 0; d < dimension; d++) {
        full_out[d] = (counts[d] > 0.0) ? (acc[d] / counts[d]) : 0.0;
    }
}

#endif
