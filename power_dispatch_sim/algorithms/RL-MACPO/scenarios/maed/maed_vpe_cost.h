#ifndef MAED_VPE_COST_H
#define MAED_VPE_COST_H

/**
 * 阀点效应 (valve-point) 发电成本 — MAED / VPE-ED 标准形式
 *
 *   C(P) = a·P² + b·P + c + | e·sin( f·(Pmin − P) ) |
 *
 * 参考: Sin & Than (1997); Gaing (2003); 多篇 PSO/DE-ED 文献共用 13 机组参数表。
 */

#include <cmath>

struct MaedVpeUnit {
    double Pmin;
    double Pmax;
    double a, b, c;
    double e, f;  // 阀点正弦项系数
};

inline double maed_vpe_unit_cost(double P, const MaedVpeUnit& u) {
  double val = u.a * P * P + u.b * P + u.c
             + std::fabs(u.e * std::sin(u.f * (u.Pmin - P)));
  return val;
}

/** 越界软罚（箱约束修复后残余违反） */
inline double maed_box_violation_penalty(double P, const MaedVpeUnit& u, double w = 500.0) {
  double pen = 0.0;
  if (P < u.Pmin) {
    double v = u.Pmin - P;
    pen += w * v * v;
  } else if (P > u.Pmax) {
    double v = P - u.Pmax;
    pen += w * v * v;
  }
  return pen;
}

inline double maed_clamp_unit_power(double& P, const MaedVpeUnit& u) {
  if (P < u.Pmin) P = u.Pmin;
  if (P > u.Pmax) P = u.Pmax;
  return P;
}

#endif
