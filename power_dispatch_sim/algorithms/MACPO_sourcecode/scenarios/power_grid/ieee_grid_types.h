#ifndef IEEE_GRID_TYPES_H
#define IEEE_GRID_TYPES_H

/** 发电机二次成本: a*P^2 + b*P + c ($/h) */
struct GenData {
    int bus_id;
    double Pmax, Pmin;
    double a, b, c;
};

/** 区域间联络线 → 全局共享维；Pmax 为割集上支路额定容量之和 (MW) */
struct TieLine {
    int region_from, region_to;
    int global_dim;
    double Pmax;
};

#endif
