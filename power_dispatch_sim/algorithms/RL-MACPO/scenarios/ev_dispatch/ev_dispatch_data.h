#ifndef EV_DISPATCH_DATA_H
#define EV_DISPATCH_DATA_H

/** 附录 VI 电动汽车充电站调度 — 10 节点链 */
#define EV_NUM_NODES 10
#define EV_NUM_VEHICLES 5

static const double ev_a[EV_NUM_NODES] = {
    0.08, 0.09, 0.10, 0.11, 0.10, 0.09, 0.10, 0.11, 0.12, 0.10
};
static const double ev_p1 = 0.05;
static const double ev_alpha = 0.02;
static const double ev_L = 1.0;       // 相邻站距离
static const double ev_m = 2.5;
static const double ev_price_eps = 0.02;
static const int ev_price_max_iter = 80;

/** 各站 EV 初始电量比例 Q0_k ∈ [0,1]（固定场景参数） */
static const double ev_Q0[EV_NUM_NODES][EV_NUM_VEHICLES] = {
    {0.55, 0.62, 0.48, 0.71, 0.53},
    {0.60, 0.45, 0.58, 0.67, 0.50},
    {0.52, 0.70, 0.44, 0.61, 0.56},
    {0.48, 0.59, 0.65, 0.51, 0.63},
    {0.57, 0.49, 0.68, 0.54, 0.60},
    {0.64, 0.53, 0.47, 0.66, 0.58},
    {0.50, 0.61, 0.55, 0.72, 0.46},
    {0.63, 0.52, 0.59, 0.48, 0.65},
    {0.56, 0.68, 0.51, 0.57, 0.62},
    {0.54, 0.46, 0.60, 0.69, 0.55},
};

static const double ev_min_x = -2.0;
static const double ev_max_x = 15.0;

#endif
