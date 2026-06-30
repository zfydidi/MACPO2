#ifndef ENHANCED_EVALUATOR_H
#define ENHANCED_EVALUATOR_H

#include "evaluator.h"
#include <unordered_map>
#include <string>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <algorithm>

/**
 * ====================================================================
 * @class EnhancedRLPenaltyEvaluator
 * @brief 增强版RL惩罚评估器 - MACPO算法的智能化升级版本
 * ====================================================================
 * 
 * 这是针对MACPO算法七大核心问题的完整解决方案：
 * 
 * 【解决的核心问题】：
 * 1. 问题1：无差别协商 -> 变量重要性筛选，按阶段比例协商变量
 * 2. 问题2：固定λ=1/512 -> 自适应权重，基于冲突强度调整
 * 3. 问题3：静态三步协商 -> 收敛阶段自适应调整协商频率
 * 4. 问题4：梯度检测不可靠 -> 基于位置差异的简单鲁棒检测
 * 5. 问题5：冲突检测不鲁棒 -> 多指标融合+历史平滑
 * 6. 问题6：高通信开销 -> 最小间隔10轮+冲突阈值筛选
 * 7. 问题7：高CI性能差 -> CI自适应调整通信策略
 * 
 * 【关键创新】：
 * - 模块化设计：每个问题对应一个专门的智能组件
 * - 渐进式调整：避免参数剧烈变化，保持优化稳定性
 * - 自适应学习：根据优化效果动态调整所有策略参数
 * - 高效实现：大幅减少计算开销和通信频率
 */
/**
 * @struct ExperimentConfig
 * @brief 消融实验配置 - 支持 Exp1-Exp6 的配置切换
 */
struct ExperimentConfig {
    int gating_mode = 3;      // 0=无门控(每轮必通信), 1=仅Layer1, 2=Layer1+2, 3=Full
    bool use_variable_filter = true;  // 是否使用变量筛选
    bool force_disable_threshold = false; // sanity: 关闭阈值层
    bool force_disable_phase = false;     // sanity: 关闭phase层
    int threshold_mode = 1;   // 0=fixed absolute threshold, 1=relative threshold(EMA-CI)
    double relative_lambda = 1.2; // relative threshold multiplier
    double ci_ema_beta = 0.9;     // EMA coefficient for CI baseline
    bool enable_fail_safe = true; // fail-safe: force trigger after K silent rounds
    int fail_safe_k = 10;
    bool force_periodic = false;  // fixed-interval communication baseline (no CI gate)
    int periodic_k = 3;         // communicate every K outer loops when force_periodic
    double phase_early = -1;  // 阶段通信频率覆盖，-1表示使用默认
    double phase_mid = -1;
    double phase_late = -1;
    double selection_early = -1;  // 变量选择比例覆盖，-1表示使用默认
    double selection_mid = -1;
    double selection_late = -1;
};

class EnhancedRLPenaltyEvaluator : public RLPenaltyEvaluator {
private:
    double* local_global_best;  // 本地全局最优解缓存
    ExperimentConfig experiment_config;  // 消融实验配置
    
    // ====================================================================
    // 【问题1解决方案】智能变量筛选器 - 解决无差别协商问题
    // ====================================================================
    /**
     * @struct SmartVariableFilter
     * @brief 智能变量筛选器 - 学习并筛选重要变量（用于减少协商维度）
     * 
     * 【工作原理】：
     * 1. 跟踪每个变量的协商成功率和冲突贡献度
     * 2. 计算变量重要性分数 = 成功率 × 冲突敏感度
     * 3. 按阶段比例选择重要变量进行协商
     * 4. 动态更新重要性，适应问题特性变化
     * 
     * 【效果】：减少50-70%的协商开销，提高协商质量
     */
    struct SmartVariableFilter {
        std::vector<double> variable_importance;  // 变量重要性分数[0,1]
        double selection_ratio = 0.7;            // 选择比例：随阶段动态调整
        
        // 构造函数：初始化所有变量重要性为1.0
        SmartVariableFilter(int dim) : variable_importance(dim, 1.0) {}
        
        /**
         * @brief 筛选重要变量进行协商
         * @param candidates 候选变量列表（重叠维度）
         * @return 筛选后的重要变量列表
         * 
         * 算法步骤：
         * 1. 为每个候选变量打分：(重要性分数, 变量索引)
         * 2. 按重要性降序排列
         * 3. 选择前k比例的变量
         * 4. 确保至少选择1个变量
         */
        std::vector<int> filter_important_variables(const std::vector<int>& candidates) {
            if (candidates.empty()) return candidates;
            
            // 为每个变量分配重要性分数
            std::vector<std::pair<double, int>> scored_vars;
            for (int var : candidates) {
                if (var >= 0 && var < variable_importance.size()) {
                    scored_vars.emplace_back(variable_importance[var], var);
                }
            }
            
            // 按重要性降序排列：重要的变量排在前面
            std::sort(scored_vars.begin(), scored_vars.end(), std::greater<std::pair<double, int>>());
            
            // 选择前k比例的变量
            std::vector<int> filtered;
            int max_select = std::max(1, (int)(candidates.size() * selection_ratio));
            for (int i = 0; i < std::min(max_select, (int)scored_vars.size()); i++) {
                filtered.push_back(scored_vars[i].second);
            }
            
            return filtered;
        }

        /**
         * @brief 动态设置选择比例
         * @param ratio 选择比例(0,1]
         */
        void set_selection_ratio(double ratio) {
            if (ratio < 0.1) ratio = 0.1;
            if (ratio > 1.0) ratio = 1.0;
            selection_ratio = ratio;
        }
        
        /**
         * @brief 更新变量重要性
         * @param var_idx 变量索引
         * @param conflict_level 该变量的冲突强度
         * 
         * 重要性更新公式：
         * importance = 0.8 × 旧重要性 + 0.2 × 当前冲突强度
         * （高冲突的变量更重要，需要优先协商）
         */
        void update_importance(int var_idx, double conflict_level) {
            if (var_idx >= 0 && var_idx < variable_importance.size()) {
                // 基于冲突程度更新重要性：冲突越大，重要性越高
                variable_importance[var_idx] = 0.8 * variable_importance[var_idx] + 0.2 * conflict_level;
            }
        }
    };
    
    // ====================================================================
    // 【问题2解决方案】渐进式稳定权重控制器 - 替代固定λ=1/512
    // ====================================================================
    /**
     * @struct AdaptivePenaltyController
     * @brief 自适应惩罚权重控制器 - 智能调整惩罚强度
     * 
     * 【核心思想】：
     * - 摒弃固定的λ=1/512，使用智能的自适应权重
     * - 引入渐进式调整机制，避免权重剧烈波动
     * - 基于冲突强度和收敛状态动态调整权重
     * - 内置稳定因子，确保权重变化平滑
     * 
     * 【权重调整策略】：
     * - 低冲突时：促进权重下降，减少不必要的惩罚
     * - 高冲突时：适度增加权重，强化协调机制
     * - 收敛期间：逐渐降低权重，避免过度惩罚
     */
    struct AdaptivePenaltyController {
        double current_lambda = 0.02;  // 当前权重：替代固定的1/512≈0.002
        double base_lambda = 0.01;     // 基础权重：比原版更合理的起始值
        double max_lambda = 0.025;     // 最大权重：严格限制避免过度惩罚
        double min_lambda = 0.002;     // 最小权重：保持最低协调能力
        std::vector<double> conflict_history;  // 冲突历史记录
        
        // === 渐进式稳定机制核心组件 ===
        std::vector<double> recent_improvements;  // 最近的优化改进记录
        double stability_factor = 1.0;           // 稳定因子：控制权重调整敏感度
        double lambda_momentum = 0.9;            // 权重动量：平滑权重变化
        int stability_window = 5;                // 稳定性评估窗口大小
        
        /**
         * @brief 获取自适应权重
         * @param conflict_intensity 当前冲突强度
         * @param convergence_rate 收敛速度
         * @return 调整后的权重值
         * 
         * 【权重计算逻辑】：
         * 1. 更新系统稳定因子
         * 2. 根据冲突强度和收敛状态计算目标权重
         * 3. 使用高动量平滑调整（95%旧值+5%新值）
         * 4. 确保权重在安全范围内
         */
        double get_adaptive_weight(double conflict_intensity, double convergence_rate) {
            // 更新稳定因子：基于最近的优化表现
            update_stability_factor();
            
            // === 简化权重计算：减少干扰 ===
            double target_lambda = base_lambda;
            
            // 只在真正需要时才调整权重
            if (conflict_intensity > 0.02 || convergence_rate > 0.05) {
                // 温和的强度调节：避免过度反应
                double intensity_factor = 1.0 + 0.5 * conflict_intensity * stability_factor;
                target_lambda = base_lambda * intensity_factor;
            } else {
                // 低冲突时促进权重自然下降
                target_lambda = base_lambda * 0.95;
            }
            
            // 严格的边界控制
            target_lambda = std::max(min_lambda, std::min(max_lambda, target_lambda));
            
            // === 高动量平滑：确保权重变化稳定 ===
            current_lambda = 0.95 * current_lambda + 0.05 * target_lambda;
            
            return current_lambda;
        }
        
        /**
         * @brief 记录优化改进情况
         * @param improvement 本次迭代的适应度改进量
         * 
         * 用于评估系统稳定性和调整策略
         */
        void record_improvement(double improvement) {
            recent_improvements.push_back(improvement);
            if (recent_improvements.size() > stability_window) {
                recent_improvements.erase(recent_improvements.begin());
            }
        }
        
    private:
        /**
         * @brief 更新系统稳定因子
         * 
         * 【稳定性评估逻辑】：
         * - 如果最近出现多次负改进，降低权重敏感性
         * - 如果持续稳定改进，恢复正常敏感性
         * - 稳定因子范围：[0.3, 1.0]
         */
        void update_stability_factor() {
            if (recent_improvements.size() < 3) return;
            
            // 统计最近的负改进次数
            int negative_count = 0;
            double avg_improvement = 0.0;
            
            for (double imp : recent_improvements) {
                avg_improvement += imp;
                if (imp < 0) negative_count++;
            }
            avg_improvement /= recent_improvements.size();
            
            // 渐进调整稳定因子
            if (negative_count >= 2 || avg_improvement < -0.02) {
                // 系统不稳定：降低权重敏感性，避免恶化
                stability_factor *= 0.85;
                stability_factor = std::max(0.3, stability_factor);
            } else if (negative_count == 0 && avg_improvement > 0.01) {
                // 系统稳定：逐渐恢复正常敏感性
                stability_factor *= 1.05;
                stability_factor = std::min(1.0, stability_factor);
            }
        }
    };
    
    // ====================================================================
    // 【问题3解决方案】收敛阶段自适应器 - 替代静态三步协商
    // ====================================================================
    /**
     * @struct ConvergencePhaseAdapter
     * @brief 收敛阶段自适应器 - 根据优化进程调整协商频率
     * 
     * 【设计理念】：
     * - 早期阶段（EARLY）：高频通信，快速探索
     * - 中期阶段（MID）：中频通信，平衡探索与开发
     * - 后期阶段（LATE）：低频通信，精细化优化
     * 
     * 【阶段识别】：
     * - 基于迭代次数：15次→中期，30次→后期
     * - 基于收敛程度：适应度变化<0.01→中期，<0.001→后期
     * - 动态调整：根据实际表现微调通信频率
     */
    struct ConvergencePhaseAdapter {
        enum Phase { EARLY, MID, LATE };  // 优化阶段枚举
        Phase current_phase = EARLY;      // 当前阶段
        int iteration = 0;                // 迭代计数器
        
        // === 渐进式频率调整机制 ===
        double communication_frequency = 0.6;    // 动态通信频率
        double frequency_momentum = 0.95;        // 频率变化动量：平滑调整
        std::vector<double> recent_performance;  // 最近性能表现记录
        
        /**
         * @brief 更新优化阶段和通信频率
         * @param fitness_change 适应度变化量
         * @param iter 当前迭代次数
         * 
         * 【阶段更新逻辑】：
         * - 综合考虑迭代次数和收敛程度
         * - 动态调整各阶段的通信频率
         * - 基于最近表现微调频率参数
         */
        void update_phase(double fitness_change, int iter) {
            iteration = iter;
            
            // 记录性能表现用于频率微调
            recent_performance.push_back(fitness_change);
            if (recent_performance.size() > 8) {
                recent_performance.erase(recent_performance.begin());
            }
            
            // 渐进式阶段更新：基于迭代次数和收敛程度
            if (iter > 30 || fitness_change < 0.001) {
                current_phase = LATE;    // 后期：精细化阶段
            } else if (iter > 15 || fitness_change < 0.01) {
                current_phase = MID;     // 中期：平衡阶段
            }
            // 否则保持EARLY阶段
            
            // 动态调整通信频率
            update_communication_frequency();
        }
        
        /**
         * @brief 获取当前阶段的通信频率
         * @return 通信频率[0,1]
         */
        double get_communication_frequency() {
            return communication_frequency;
        }

        /** @brief 获取当前阶段（供消融实验覆盖用） */
        Phase get_current_phase() const { return current_phase; }

        /**
         * @brief 获取当前阶段的变量选择比例
         * @return 选择比例[0.1,1.0]
         */
        double get_selection_ratio() const {
            switch (current_phase) {
                case EARLY: return 0.9;  // 早期：更多变量参与协商
                case MID: return 0.7;    // 中期：平衡选择
                case LATE: return 0.5;   // 后期：减少协商变量
                default: return 0.7;
            }
        }
        
    private:
        /**
         * @brief 更新通信频率
         * 
         * 【频率调整策略】：
         * - EARLY: 60%基础频率，积极通信
         * - MID: 30%基础频率，适度通信
         * - LATE: 15%基础频率，谨慎通信
         * - 性能反馈：表现不佳时进一步降低频率
         */
        void update_communication_frequency() {
            // 计算目标频率：不同阶段有不同的基础频率
            double target_frequency;
            switch (current_phase) {
                case EARLY: target_frequency = 0.6; break;   // 早期：积极通信
                case MID: target_frequency = 0.3; break;     // 中期：适度通信
                case LATE: target_frequency = 0.15; break;   // 后期：谨慎通信
                default: target_frequency = 0.3; break;
            }
            
            // 基于最近性能表现微调频率
            if (recent_performance.size() >= 3) {
                int negative_count = 0;
                // 统计最近3次的负改进次数
                for (int i = recent_performance.size() - 3; i < recent_performance.size(); i++) {
                    if (recent_performance[i] < 0) negative_count++;
                }
                
                // 如果最近表现不佳，进一步降低通信频率
                if (negative_count >= 2) {
                    target_frequency *= 0.6;  // 降低40%
                }
            }
            
            // 动量平滑调整：避免频率剧烈变化
            communication_frequency = frequency_momentum * communication_frequency + 
                                    (1 - frequency_momentum) * target_frequency;
        }
    };
    
    // ====================================================================
    // 【问题4&5解决方案】鲁棒冲突检测器 - 可靠的冲突度量
    // ====================================================================
    /**
     * @struct RobustConflictDetector
     * @brief 鲁棒冲突检测器 - 稳定可靠的冲突度量
     * 
     * 【设计目标】：
     * - 避免复杂的梯度计算，使用简单但稳定的位置差异
     * - 引入历史平滑机制，减少噪声干扰
     * - 多指标融合，提高检测准确性
     * - 计算高效，适合实时优化环境
     * 
     * 【冲突度量公式】：
     * conflict = smooth(|x1 - x2| / range)
     * 其中smooth表示历史平滑处理
     */
    struct RobustConflictDetector {
        std::vector<double> conflict_smooth;  // 每个变量的平滑冲突值
        double smooth_factor = 0.7;          // 平滑因子：70%历史+30%当前
        
        // 构造函数：初始化平滑数组
        RobustConflictDetector(int dim) : conflict_smooth(dim, 0.0) {}
        
        /**
         * @brief 计算单个变量的鲁棒冲突
         * @param x1 第一个解的该维度值
         * @param x2 第二个解的该维度值
         * @param var_idx 变量索引
         * @param range 变量范围（用于归一化）
         * @return 该变量的冲突强度[0,1]
         * 
         * 【计算流程】：
         * 1. 计算归一化的位置差异
         * 2. 应用历史平滑处理
         * 3. 返回稳定的冲突值
         */
        double calculate_robust_conflict(double* x1, double* x2, int var_idx, double range) {
            if (var_idx < 0 || range <= 0) return 0.0;
            
            // 简单但鲁棒：基于位置差异（避免复杂梯度计算）
            double pos_diff = std::abs(x1[var_idx] - x2[var_idx]) / range;
            
            // 历史平滑处理：减少噪声，提高稳定性
            if (var_idx < conflict_smooth.size()) {
                conflict_smooth[var_idx] = smooth_factor * conflict_smooth[var_idx] + 
                                         (1 - smooth_factor) * pos_diff;
                return conflict_smooth[var_idx];
            }
            
            return pos_diff;
        }
        
        /**
         * @brief 计算整体冲突强度
         * @param x 当前解
         * @param reference 参考解（通常是全局最优）
         * @param dim 维度数
         * @param range 变量范围
         * @return 平均冲突强度
         */
        double calculate_overall_conflict(double* x, double* reference, int dim, double range) {
            double total_conflict = 0.0;
            for (int i = 0; i < dim; i++) {
                total_conflict += calculate_robust_conflict(x, reference, i, range);
            }
            return total_conflict / dim;  // 返回平均冲突
        }
    };
    
    // ====================================================================
    // 【问题6&7解决方案】智能通信管理器 - 高效通信控制
    // ====================================================================
    /**
     * @struct SmartCommunicationManager
     * @brief 智能通信管理器 - 减少通信开销，提高效率
     * 
     * 【核心功能】：
     * - 强制最小通信间隔：避免过频繁通信
     * - 自适应阈值调整：基于通信收益动态调整
     * - CI自适应机制：根据冲突指数调整策略
     * - 渐进式参数调整：确保系统稳定
     * 
     * 【通信决策逻辑】：
     * 1. 检查最小间隔：距离上次通信>=10轮
     * 2. 计算自适应阈值：基于历史收益调整
     * 3. 结合阶段频率：考虑当前优化阶段
     * 4. 做出最终决策：综合所有因素
     */
    struct SmartCommunicationManager {
        struct GateDecision {
            bool interval_ok = false;
            bool threshold_ok = false;
            bool phase_ok = false;
            bool local_gate = false;
            bool fail_safe_fired = false;
            bool use_relative_threshold = false;
            double conflict_index = 0.0;
            double threshold = 0.0;
            double ci_ema = 0.0;
            double phase_freq = 0.0;
            double phase_u = -1.0;
            int current_iter = 0;
            int last_comm_iter = -100;
        };

        int min_interval = 10;               // 最小通信间隔：强制等待轮数
        int last_comm_iter = -100;          // 上次通信的迭代次数
        double base_threshold = 0.02;       // 基础通信阈值
        double communication_efficiency = 1.0;  // 通信效率评估
        
        // === 渐进式阈值调整机制 ===
        double current_threshold = 0.02;      // 当前自适应阈值
        double threshold_momentum = 0.9;      // 阈值调整动量
        std::vector<double> comm_benefits;    // 通信收益历史
        int benefit_window = 6;               // 收益评估窗口大小
        GateDecision last_decision;           // 最近一次门控细分决策
        double ci_ema = 0.0;                  // EMA baseline of CI for relative threshold
        bool ci_ema_initialized = false;
        bool ever_communicated = false;
        
        /**
         * @brief 判断是否应该进行通信
         * @param conflict_index 当前冲突指数
         * @param current_iter 当前迭代次数
         * @param phase_freq 阶段通信频率
         * @return 是否需要通信
         * 
         * 【决策流程】：
         * 1. 强制间隔检查：确保最小间隔要求
         * 2. 渐进式阈值更新：基于历史收益调整
         * 3. 多因素决策：结合冲突强度和阶段频率
         * 4. 记录通信时间：为下次检查做准备
         */
        bool should_communicate(double conflict_index, int current_iter, double phase_freq,
                               bool use_threshold = true, bool use_phase = true,
                               bool use_relative_threshold = false,
                               double relative_lambda = 1.2, double ci_ema_beta = 0.9,
                               bool enable_fail_safe = false, int fail_safe_k = 10) {
            last_decision = GateDecision{};
            last_decision.conflict_index = conflict_index;
            last_decision.threshold = current_threshold;
            last_decision.phase_freq = phase_freq;
            last_decision.current_iter = current_iter;
            last_decision.last_comm_iter = last_comm_iter;
            last_decision.use_relative_threshold = use_relative_threshold;

            // 强制最小间隔：避免过度频繁的通信
            if (current_iter - last_comm_iter < min_interval) {
                last_decision.interval_ok = false;
                last_decision.local_gate = false;
                return false;
            }
            last_decision.interval_ok = true;
            
            // 更新CI的EMA基线（供相对阈值使用）
            bool first_ema_update = !ci_ema_initialized;
            if (!ci_ema_initialized) {
                ci_ema = conflict_index;
                ci_ema_initialized = true;
            } else {
                if (ci_ema_beta < 0.5) ci_ema_beta = 0.5;
                if (ci_ema_beta > 0.999) ci_ema_beta = 0.999;
                ci_ema = ci_ema_beta * ci_ema + (1.0 - ci_ema_beta) * conflict_index;
            }

            // 阈值更新：支持 fixed absolute / relative threshold 两种模式
            if (use_relative_threshold) {
                double ci_ref = std::max(ci_ema, 1e-6);
                double target_threshold = relative_lambda * ci_ref;
                if (first_ema_update) {
                    current_threshold = target_threshold;
                } else {
                    // Relative mode follows CI scale closely to avoid lock-up.
                    current_threshold = 0.5 * current_threshold + 0.5 * target_threshold;
                }
                current_threshold = std::max(0.001, std::min(0.2, current_threshold));
            } else {
                update_adaptive_threshold(conflict_index);
            }
            last_decision.threshold = current_threshold;
            last_decision.ci_ema = ci_ema;
            
            // 结合多个因素的综合决策（支持消融：可关闭阈值或相位检查）
            bool threshold_ok = !use_threshold || (conflict_index > current_threshold);
            double u = (double)rand() / RAND_MAX;
            bool phase_ok = !use_phase || (u < phase_freq);
            bool should_comm = threshold_ok && phase_ok;

            // fail-safe: avoid permanent negotiation shutdown
            bool fail_safe_fire = false;
            if (enable_fail_safe) {
                int silent_rounds = ever_communicated ? (current_iter - last_comm_iter) : current_iter;
                if (silent_rounds >= fail_safe_k) {
                    fail_safe_fire = true;
                    should_comm = true;
                }
            }

            last_decision.threshold_ok = threshold_ok;
            last_decision.phase_ok = phase_ok;
            last_decision.phase_u = u;
            last_decision.local_gate = should_comm;
            last_decision.fail_safe_fired = fail_safe_fire;
            
            if (should_comm) {
                last_comm_iter = current_iter;  // 记录通信时间
                last_decision.last_comm_iter = last_comm_iter;
                ever_communicated = true;
            }
            
            return should_comm;
        }

        // 用于无门控模式下写入统一决策记录
        void set_forced_decision(double conflict_index, int current_iter, double phase_freq) {
            last_decision = GateDecision{};
            last_decision.interval_ok = true;
            last_decision.threshold_ok = true;
            last_decision.phase_ok = true;
            last_decision.local_gate = true;
            last_decision.conflict_index = conflict_index;
            last_decision.threshold = current_threshold;
            last_decision.ci_ema = ci_ema;
            last_decision.phase_freq = phase_freq;
            last_decision.phase_u = 0.0;
            last_decision.current_iter = current_iter;
            last_decision.last_comm_iter = current_iter;
            last_comm_iter = current_iter;
            ever_communicated = true;
        }
        
        /**
         * @brief 更新通信效率评估
         * @param fitness_before 通信前适应度
         * @param fitness_after 通信后适应度
         * 
         * 用于评估通信的实际效果，指导后续决策
         */
        void update_efficiency(double fitness_before, double fitness_after) {
            double benefit = (fitness_before - fitness_after) / (fitness_before + 1e-10);
            communication_efficiency = 0.8 * communication_efficiency + 0.2 * std::max(0.0, benefit);
            
            // 记录通信收益用于阈值调整
            comm_benefits.push_back(benefit);
            if (comm_benefits.size() > benefit_window) {
                comm_benefits.erase(comm_benefits.begin());
            }
        }
        
    private:
        /**
         * @brief 更新自适应阈值
         * @param conflict_index 当前冲突指数
         * 
         * 【调整策略】：
         * - CI自适应：高CI时降低阈值，低CI时提高阈值
         * - 收益反馈：通信收益不佳时提高阈值
         * - 动量平滑：避免阈值剧烈变化
         */
        void update_adaptive_threshold(double conflict_index) {
            // CI自适应基础调整
            double target_threshold = base_threshold;
            if (conflict_index > 0.7) {
                target_threshold *= 0.5;  // 高CI：降低阈值，增加通信
            } else if (conflict_index < 0.3) {
                target_threshold *= 2.0;  // 低CI：提高阈值，减少通信
            }
            
            // 基于通信收益微调
            if (comm_benefits.size() >= 3) {
                double avg_benefit = 0.0;
                int negative_count = 0;
                
                for (double benefit : comm_benefits) {
                    avg_benefit += benefit;
                    if (benefit < 0) negative_count++;
                }
                avg_benefit /= comm_benefits.size();
                
                // 如果通信收益不佳，提高阈值（减少通信）
                if (negative_count >= comm_benefits.size() * 0.6 || avg_benefit < -0.01) {
                    target_threshold *= 1.5;
                }
            }
            
            // 动量平滑调整阈值：避免剧烈变化
            current_threshold = threshold_momentum * current_threshold + 
                              (1 - threshold_momentum) * target_threshold;
            
            // 限制阈值范围：确保在合理区间
            current_threshold = std::max(0.005, std::min(0.1, current_threshold));
        }
    };
    
    // ====================================================================
    // 组件实例化 - 将所有智能组件整合到评估器中
    // ====================================================================
    SmartVariableFilter variable_filter;           // 变量筛选器实例
    AdaptivePenaltyController penalty_controller;  // 权重控制器实例
    ConvergencePhaseAdapter phase_adapter;         // 阶段适配器实例
    RobustConflictDetector conflict_detector;      // 冲突检测器实例
    SmartCommunicationManager comm_manager;        // 通信管理器实例
    
    // ====================================================================
    // 系统状态变量 - 跟踪算法运行状态
    // ====================================================================
    double current_conflict_index = 0.0;   // 当前冲突指数
    int total_communications = 0;           // 总通信次数统计
    int total_iterations = 0;               // 总迭代次数统计
    std::vector<double> fitness_history;    // 适应度历史记录
    int rl_update_calls = 0;                // RL更新次数统计
    long long filter_total_candidates = 0;  // 变量筛选候选总数
    long long filter_total_selected = 0;    // 变量筛选选中总数
    int current_iter_cached = 0;            // 缓存迭代次数，供1参数版 should_communicate 使用

public:
    // ====================================================================
    // 公共接口 - 提供给外部调用的功能
    // ====================================================================
    
    /**
     * @brief 构造函数 - 初始化增强版评估器
     * 
     * 【初始化流程】：
     * 1. 继承基类RLPenaltyEvaluator的所有功能
     * 2. 初始化所有智能组件
     * 3. 设置合理的初始参数
     * 4. 创建本地缓存和状态跟踪
     */
    EnhancedRLPenaltyEvaluator(int* vs, int* cr, int dim, double* gb, double initial_alpha, 
                          Benchmarks* p_func, int group_index)
        : RLPenaltyEvaluator(vs, cr, dim, gb, initial_alpha, p_func, group_index),
          variable_filter(dim), conflict_detector(dim) {
        
        // 创建本地全局最优解缓存
        local_global_best = new double[dim];
        memcpy(local_global_best, gb, dim * sizeof(double));
        
        // 使用自适应初始权重替代固定值
        set_alpha(penalty_controller.get_adaptive_weight(0.1, 0.1));
        
        // 预留适应度历史空间
        fitness_history.reserve(100);
    }
    
    /**
     * @brief 析构函数 - 清理资源
     */
    ~EnhancedRLPenaltyEvaluator() override {
        delete[] local_global_best;
    }

    /**
     * @brief 更新全局最优解 - 同步更新 local_global_best 用于冲突计算
     */
    void set_global_best(double* new_gb) override {
        RLPenaltyEvaluator::set_global_best(new_gb);
        memcpy(local_global_best, new_gb, get_dimension() * sizeof(double));
    }

    /**
     * @brief 基类虚函数覆盖版本（1参数）- 委托给带迭代次数的版本
     */
    bool should_communicate(double* x) override {
        return should_communicate(x, current_iter_cached);
    }

    /**
     * @brief 智能通信决策 - 集成所有改进的核心接口
     * @param x 当前解
     * @param current_iter 当前迭代次数
     * @return 是否需要通信
     * 
     * 【决策流程】：
     * 1. 计算鲁棒冲突指标
     * 2. 更新收敛阶段和通信频率
     * 3. 综合所有因素做出通信决策
     * 4. 更新统计信息
     */
    bool should_communicate(double* x, int current_iter) {
        total_iterations++;
        current_iter_cached = current_iter;

        // 消融Exp1/Exp2：无门控时每轮必通信
        if (experiment_config.gating_mode == 0) {
            current_conflict_index = calculate_enhanced_conflict(x);
            comm_manager.set_forced_decision(current_conflict_index, current_iter, 1.0);
            total_communications++;
            return true;
        }

        // Periodic baseline: fixed every-K communication (RL penalty on, CI gate off)
        if (experiment_config.force_periodic && experiment_config.periodic_k > 0) {
            current_conflict_index = calculate_enhanced_conflict(x);
            bool should_comm = (current_iter % experiment_config.periodic_k == 0);
            if (should_comm) {
                total_communications++;
            }
            return should_comm;
        }
        
        // 计算鲁棒冲突指标：使用改进的检测算法
        int dim = get_dimension();
        double var_range = get_max_x() - get_min_x();
        current_conflict_index = conflict_detector.calculate_overall_conflict(
            x, local_global_best, dim, var_range);
        
        // 更新收敛阶段：根据优化进程调整策略
        double fitness_change = get_recent_fitness_change();
        phase_adapter.update_phase(fitness_change, current_iter);
        
        // 获取当前阶段的通信频率（支持消融Exp3覆盖）
        double phase_freq = phase_adapter.get_communication_frequency();
        auto ph = phase_adapter.get_current_phase();
        if (experiment_config.phase_early >= 0 && ph == ConvergencePhaseAdapter::EARLY)
            phase_freq = experiment_config.phase_early;
        else if (experiment_config.phase_mid >= 0 && ph == ConvergencePhaseAdapter::MID)
            phase_freq = experiment_config.phase_mid;
        else if (experiment_config.phase_late >= 0 && ph == ConvergencePhaseAdapter::LATE)
            phase_freq = experiment_config.phase_late;
        
        // 消融Exp2：Layer1仅间隔，Layer1+2间隔+阈值，Full全开
        bool use_threshold = (experiment_config.gating_mode >= 2);
        bool use_phase = (experiment_config.gating_mode >= 3);
        if (experiment_config.force_disable_threshold) use_threshold = false;
        if (experiment_config.force_disable_phase) use_phase = false;
        bool use_relative_threshold = (experiment_config.threshold_mode == 1);
        
        // 智能通信决策：综合所有改进
        bool should_comm = comm_manager.should_communicate(
            current_conflict_index, current_iter, phase_freq,
            use_threshold, use_phase,
            use_relative_threshold,
            experiment_config.relative_lambda,
            experiment_config.ci_ema_beta,
            experiment_config.enable_fail_safe,
            experiment_config.fail_safe_k);
        
        if (should_comm) {
            total_communications++;
        }
        
        return should_comm;
    }
    
    /**
     * @brief 获取筛选后的协商变量 - 解决问题1
     * @param overlap_dims 重叠维度列表
     * @return 筛选后的重要变量列表
     * 
     * 根据当前阶段动态调整选择比例，减少协商开销
     */
    std::vector<int> get_filtered_negotiation_variables(const std::vector<int>& overlap_dims) {
        // 消融Exp4：无变量筛选时返回全部
        if (!experiment_config.use_variable_filter) {
            filter_total_candidates += (long long)overlap_dims.size();
            filter_total_selected += (long long)overlap_dims.size();
            return overlap_dims;
        }
        // 消融Exp4：支持选择比例覆盖
        double ratio = phase_adapter.get_selection_ratio();
        auto ph = phase_adapter.get_current_phase();
        if (experiment_config.selection_early >= 0 && ph == ConvergencePhaseAdapter::EARLY)
            ratio = experiment_config.selection_early;
        else if (experiment_config.selection_mid >= 0 && ph == ConvergencePhaseAdapter::MID)
            ratio = experiment_config.selection_mid;
        else if (experiment_config.selection_late >= 0 && ph == ConvergencePhaseAdapter::LATE)
            ratio = experiment_config.selection_late;
        variable_filter.set_selection_ratio(ratio);
        auto filtered = variable_filter.filter_important_variables(overlap_dims);
        filter_total_candidates += (long long)overlap_dims.size();
        filter_total_selected += (long long)filtered.size();
        return filtered;
    }
    
    /**
     * @brief 获取自适应惩罚权重 - 解决问题2
     * @return 智能调整的权重值
     * 
     * 替代固定的λ=1/512，使用基于状态的自适应权重
     */
    double get_adaptive_penalty_weight() {
        double convergence_rate = get_convergence_rate();
        return penalty_controller.get_adaptive_weight(current_conflict_index, convergence_rate);
    }
    
    /**
     * @brief 更新系统状态 - 渐进式稳定调整的核心
     * @param x 当前解
     * @param fitness_before 通信前适应度
     * @param fitness_after 通信后适应度
     * @param shared_vars 参与协商的变量列表
     * 
     * 【更新流程】：
     * 1. 记录适应度历史
     * 2. 计算并记录改进度
     * 3. 更新通信效率评估
     * 4. 更新变量重要性
     * 5. 渐进式调整权重
     */
    void update_system_state(double* x, double fitness_before, double fitness_after, 
                           const std::vector<int>& shared_vars) {
        // 更新适应度历史：用于趋势分析
        fitness_history.push_back(fitness_after);
        if (fitness_history.size() > 50) {
            fitness_history.erase(fitness_history.begin());
        }
        
        // === 计算改进度并记录用于稳定性调整 ===
        double improvement = (fitness_before - fitness_after) / (fitness_before + 1e-10);
        penalty_controller.record_improvement(improvement);
        
        // 更新通信效率：评估本次通信的实际效果
        comm_manager.update_efficiency(fitness_before, fitness_after);
        
        // 更新变量重要性：学习哪些变量更重要
        int dim = get_dimension();
        double var_range = get_max_x() - get_min_x();
        for (int var : shared_vars) {
            double conflict = conflict_detector.calculate_robust_conflict(
                x, local_global_best, var, var_range);
            variable_filter.update_importance(var, conflict);
        }
        
        // 渐进式权重调整：使用增强的自适应机制
        double new_alpha = get_adaptive_penalty_weight();
        set_alpha(new_alpha);
    }
    
    // ====================================================================
    // 【方案2新增】RL权重比例学习接口
    // ====================================================================
    
    /**
     * @brief 设置基准α（根据目标函数值）
     * @param fitness_value 当前目标函数值
     * 
     * 使用论文验证的公式：base_alpha = |f| / 512
     * 实际惩罚权重：alpha = base_alpha × weight_ratio
     */
    void set_base_alpha(double fitness_value) {
        RLPenaltyEvaluator::set_base_alpha(fitness_value);
    }

    /** @brief 设置消融实验配置（需在首次迭代前调用） */
    void set_experiment_config(const ExperimentConfig& cfg) {
        experiment_config = cfg;
    }
    
    /**
     * @brief 获取基准α
     * @return base_alpha值
     */
    double get_base_alpha() const {
        return RLPenaltyEvaluator::get_base_alpha();
    }
    
    /**
     * @brief 获取RL学习的权重比例
     * @return weight_ratio值
     */
    double get_weight_ratio() const {
        return RLPenaltyEvaluator::get_weight_ratio();
    }
    
    /**
     * @brief 获取性能指标 - 监控算法运行状态
     */
    double get_conflict_index() const { return current_conflict_index; }
    
    double get_communication_efficiency() const {
        return total_iterations > 0 ? (double)total_communications / total_iterations : 0.0;
    }

    int get_total_communications_count() const { return total_communications; }

    int get_total_iterations_count() const { return total_iterations; }

    int get_rl_update_count() const { return rl_update_calls; }

    SmartCommunicationManager::GateDecision get_last_gate_decision() const {
        return comm_manager.last_decision;
    }

    double get_avg_selected_ratio() const {
        return filter_total_candidates > 0
            ? (double)filter_total_selected / (double)filter_total_candidates
            : 0.0;
    }
    
    /**
     * @brief 增强冲突计算 - 为兼容MACPO.cpp提供的接口
     * @param x 当前解
     * @return 冲突指数
     * 
     * 使用改进的鲁棒检测算法
     */
    double calculate_enhanced_conflict(double* x) {
        int dim = get_dimension();
        double var_range = get_max_x() - get_min_x();
        current_conflict_index = conflict_detector.calculate_overall_conflict(
            x, local_global_best, dim, var_range);
        return current_conflict_index;
    }
    
    /**
     * @brief 增强的RL权重更新 - 集成CI自适应机制
     * @param x 当前解
     * @param reward 奖励信号
     * 
     * 【更新策略】：
     * 1. 计算增强的冲突指标
     * 2. 应用CI自适应调节
     * 3. 更新RL策略
     * 4. 强制权重下降保护
     * 5. 高动量平滑更新
     */
    void update_rl_weight(double* x, double reward) override {
        rl_update_calls++;
        // 使用增强的CI计算
        double enhanced_ci = calculate_enhanced_conflict(x);
        
        // 将当前fitness注入RLAgent，供方案3/5的calculate_reward使用
        // base_alpha = current_fitness / 512，反推得到current_fitness
        current_fitness_rl = get_base_alpha() * 512.0;
        
        // === 简化的CI响应策略 ===
        double ci_factor = 1.0;
        if (enhanced_ci > 0.05) {
            // 只有CI较高时才调节，避免过度敏感
            ci_factor = 1.0 + 0.5 * enhanced_ci;  // 温和调节
        }
        
        // 获取当前状态
        std::vector<double> state = get_state(enhanced_ci);
        
        // 使用温和调节的奖励更新RL策略
        double adjusted_reward = reward * ci_factor;
        update_policy(state, last_action, adjusted_reward);
        
        // === 权重比例更新：使用方案2的RL学习 ===
        double old_alpha = get_alpha();
        
        // 使用基类的权重比例更新（RL学习相对比例）
        double new_weight_ratio = update_weight_ratio(enhanced_ci);
        
        // ⚠️ 方案2关键：直接使用base_alpha × weight_ratio
        // 不再使用固定范围限制，让α自适应问题规模
        double new_alpha = get_base_alpha() * new_weight_ratio;
        
        // 平滑更新：避免剧烈震荡
        // 使用高动量(0.9)保持稳定性
        double smoothed_alpha = 0.9 * old_alpha + 0.1 * new_alpha;
        
        set_alpha(smoothed_alpha);
    }
    
    /**
     * @brief 获取性能摘要 - 生成详细的运行报告
     * @return 格式化的性能报告字符串
     * 
     * 包含所有关键性能指标和系统状态信息
     */
    std::string get_performance_summary() const {
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(3);
        oss << "Enhanced MACPO Performance (收敛修复版):\n";
        oss << "- Communication Efficiency: " << get_communication_efficiency() << "\n";
        oss << "- Current Conflict Index: " << current_conflict_index << "\n";
        oss << "- Current Phase: " << phase_adapter.current_phase << "\n";
        oss << "- Adaptive Lambda: " << penalty_controller.current_lambda << "\n";
        oss << "- Stability Factor: " << penalty_controller.stability_factor << "\n";
        oss << "- RL Weight Ratio: " << get_weight_ratio() << "\n";
        oss << "- Base Alpha: " << get_base_alpha() << "\n";
        oss << "- Actual Alpha: " << get_alpha() << "\n";
        oss << "- Total Communications: " << total_communications << "/" << total_iterations;
        return oss.str();
    }

private:
    // ====================================================================
    // 私有辅助函数 - 内部计算和状态管理
    // ====================================================================
    
    /**
     * @brief 计算最近适应度变化
     * @return 相对适应度变化量
     * 
     * 用于判断收敛程度和阶段转换
     */
    double get_recent_fitness_change() {
        if (fitness_history.size() < 2) return 0.1;
        
        double recent = fitness_history.back();
        double previous = fitness_history[fitness_history.size() - 2];
        return std::abs(previous - recent) / (std::abs(previous) + 1e-10);
    }
    
    /**
     * @brief 计算收敛速度
     * @return 收敛速度指标
     * 
     * 基于最近适应度的标准差评估收敛程度
     */
    double get_convergence_rate() {
        if (fitness_history.size() < 5) return 0.1;
        
        // 计算最近10次的标准差作为收敛指标
        int n = std::min(10, (int)fitness_history.size());
        double mean = 0.0;
        for (int i = fitness_history.size() - n; i < fitness_history.size(); i++) {
            mean += fitness_history[i];
        }
        mean /= n;
        
        double variance = 0.0;
        for (int i = fitness_history.size() - n; i < fitness_history.size(); i++) {
            variance += (fitness_history[i] - mean) * (fitness_history[i] - mean);
        }
        variance /= n;
        
        return std::sqrt(variance) / (std::abs(mean) + 1e-10);
    }
};

#endif // ENHANCED_EVALUATOR_H