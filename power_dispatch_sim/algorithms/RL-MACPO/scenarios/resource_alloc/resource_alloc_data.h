#ifndef RESOURCE_ALLOC_DATA_H
#define RESOURCE_ALLOC_DATA_H

/** 附录 V 网络资源分配 — 默认 10 节点链式网络 */
#define RA_NUM_NODES 10

static const double ra_U[RA_NUM_NODES] = {
    12.0, 11.5, 10.0, 9.5, 10.5, 11.0, 9.0, 10.0, 11.5, 12.5
};

static const double ra_min_x = -5.0;
static const double ra_max_x = 25.0;

#endif
