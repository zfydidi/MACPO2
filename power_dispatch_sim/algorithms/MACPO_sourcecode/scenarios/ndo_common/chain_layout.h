#ifndef CHAIN_LAYOUT_H
#define CHAIN_LAYOUT_H

/**
 * MACPO 论文附录 V/VI 使用的链式网络拓扑（N 个节点，N-1 条边）
 *
 * 全局编码（2N-1 维）:
 *   dim 2i   = g_i  (私有: 节点 i 产量/发电)
 *   dim 2i+1 = e_i  (共享: 边 i ↔ i+1 上的传输量, i=0..N-2)
 *
 * 符号约定（与附录式 S1/S2 一致）:
 *   c_{i,j} = +e  若 i < j
 *   c_{i,j} = -e  若 i > j   （e 为边 min(i,j) 的共享变量）
 */

#include <algorithm>
#include <cmath>
#include <vector>

struct ChainLayout {
    int n_nodes = 0;
    int total_dim = 0;
    std::vector<int> region_dim_size;
    int** group_map = nullptr;
    int overlap_groups[64][3];  // 最多 64 节点

    explicit ChainLayout(int n) { build(n); }

    ~ChainLayout() {
        if (group_map) {
            for (int r = 0; r < n_nodes; r++) delete[] group_map[r];
            delete[] group_map;
        }
    }

    void build(int n) {
        n_nodes = n;
        total_dim = 2 * n - 1;
        region_dim_size.assign(n, 0);

        group_map = new int*[n];
        for (int r = 0; r < n; r++) {
            if (r == 0) {
                region_dim_size[r] = 2;
                group_map[r] = new int[2]{0, 1};
            } else if (r == n - 1) {
                region_dim_size[r] = 2;
                group_map[r] = new int[2]{2 * r - 1, 2 * r};
            } else {
                region_dim_size[r] = 3;
                group_map[r] = new int[3]{2 * r - 1, 2 * r, 2 * r + 1};
            }
            for (int j = 0; j < 3; j++) overlap_groups[r][j] = -1;
            if (r > 0) overlap_groups[r][0] = r - 1;
            if (r < n - 1) overlap_groups[r][1] = r + 1;
        }
    }

    static int g_dim(int i) { return 2 * i; }
    static int e_dim(int i) { return 2 * i + 1; }  // 边 i — i+1

    /** 节点 i 的净输入（邻居 → i 的 signed c_ij 之和） */
    double signed_net_inflow(const double* x, int i) const {
        double s = 0.0;
        if (i > 0) s -= x[e_dim(i - 1)];   // c_{i,i-1} = -e
        if (i < n_nodes - 1) s += x[e_dim(i)];  // c_{i,i+1} = +e
        return s;
    }

    double production_at(const double* x, int i) const {
        return x[g_dim(i)];
    }

    /** U_i - (g_i + Σ_j c_ij) */
    double resource_balance_gap(const double* x, int i, double U_i) const {
        return U_i - (production_at(x, i) + signed_net_inflow(x, i));
    }
};

#endif
