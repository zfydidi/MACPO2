#include "evaluator.h"
#include <random>
#include <cmath>
#include <algorithm>
#include <iostream>

// ====================================================================
// 静态成员初始化
// ====================================================================
double RLPenaltyEvaluator::avg_conflict = 0.0;

// ====================================================================
// SimpleNet类实现 - 轻量级神经网络
// ====================================================================

/**
 * @brief SimpleNet构造函数
 * @param input_dim 输入维度（通常是2：当前冲突+趋势）
 * @param output_dim 输出维度（通常是1：权重调整建议）
 * 
 * 功能：创建一个简单的全连接神经网络
 * - 随机初始化权重和偏置
 * - 使用正态分布N(0, 0.1)初始化参数
 */
SimpleNet::SimpleNet(int input_dim, int output_dim) : rng(std::random_device{}()) {
    // 创建权重矩阵：input_dim x output_dim
    weights.resize(input_dim, std::vector<double>(output_dim));
    // 创建偏置向量：output_dim
    bias.resize(output_dim);
    
    // 初始化权重：使用小的随机值避免对称性
    std::normal_distribution<double> dist(0.0, 0.1);  // 均值0，标准差0.1
    for (auto& row : weights) {
        for (auto& w : row) {
            w = dist(rng);  // 每个权重都是独立的随机数
        }
    }
    // 初始化偏置：同样使用小随机值
    for (auto& b : bias) {
        b = dist(rng);
    }
}

/**
 * @brief 前向传播计算
 * @param input 输入向量（如[冲突强度, 趋势]）
 * @return 输出向量（如[权重调整建议]）
 * 
 * 计算过程：
 * 1. output[i] = bias[i] + Σ(input[j] * weights[j][i])
 * 2. output[i] = tanh(output[i])  // 激活函数
 */
std::vector<double> SimpleNet::forward(const std::vector<double>& input) {
    std::vector<double> output(bias.size());
    
    // 计算每个输出神经元的值
    for (size_t i = 0; i < output.size(); i++) {
        output[i] = bias[i];  // 从偏置开始
        
        // 加权求和：Σ(input[j] * weights[j][i])
        for (size_t j = 0; j < input.size(); j++) {
            output[i] += input[j] * weights[j][i];
        }
        
        // 应用tanh激活函数：输出范围(-1, 1)
        output[i] = std::tanh(output[i]);
    }
    return output;
}

/**
 * @brief 反向传播更新网络参数
 * @param input 输入向量
 * @param target 目标输出向量
 * @param learning_rate 学习率
 * 
 * 使用梯度下降更新权重和偏置：
 * - 计算输出误差：error = target - actual_output
 * - 计算梯度：grad = error * tanh'(output)
 * - 更新参数：weight += learning_rate * grad * input
 */
void SimpleNet::update(const std::vector<double>& input, const std::vector<double>& target, double learning_rate) {
    // 先计算当前输出
    auto output = forward(input);
    
    // 对每个输出神经元进行梯度下降更新
    for (size_t i = 0; i < output.size(); i++) {
        double error = target[i] - output[i];  // 计算误差
        
        // tanh的导数：tanh'(x) = 1 - tanh²(x)
        double grad = error * (1.0 - output[i] * output[i]);
        
        // 更新偏置：bias += learning_rate * grad
        bias[i] += learning_rate * grad;
        
        // 更新权重：weight[j][i] += learning_rate * grad * input[j]
        for (size_t j = 0; j < input.size(); j++) {
            weights[j][i] += learning_rate * grad * input[j];
        }
    }
}

// ====================================================================
// RLAgent类实现 - 强化学习智能代理
// ====================================================================

/**
 * @brief RLAgent构造函数
 * @param state_dim 状态维度（默认2：冲突+趋势）
 * @param action_dim 动作维度（默认1：权重比例调整）
 * @param lr 学习率（默认0.01）
 * 
 * 初始化强化学习代理的各个组件
 * ⚠️ 重要：current_weight_ratio初始化为1.0（不额外缩放）
 * 这样 α = (|f|/512) × 1.0 = |f|/512，与源代码一致
 */
RLAgent::RLAgent(int state_dim, int action_dim, double lr) 
    : learning_rate(lr), current_weight_ratio(1.0), last_action(0.0) {
    
    // 创建策略神经网络
    policy_net = std::make_shared<SimpleNet>(state_dim, action_dim);
    
    // 预留历史记录空间，避免频繁内存分配
    conflict_history.reserve(50);
    conflict_trends.reserve(50);
}

/**
 * @brief 获取当前环境状态
 * @param conflict_now 当前冲突强度
 * @return 状态向量[当前冲突, 冲突趋势]
 * 
 * 将环境信息转换为神经网络可处理的状态向量
 */
std::vector<double> RLAgent::get_state(double conflict_now) {
    // 计算冲突趋势：如果有历史数据，使用最新趋势；否则为0
    double trend = 0.0;
    if (conflict_trends.size() > 0) {
        trend = conflict_trends.back();
    }
    
    // 返回状态向量：[当前冲突强度, 变化趋势]
    return {conflict_now, trend};
}

/**
 * @brief 根据当前状态决定权重调整动作
 * @param conflict_now 当前冲突强度
 * @param conflict_trend 冲突变化趋势
 * @return 权重调整建议（-1到1之间）
 * 
 * 使用神经网络策略选择动作
 */
double RLAgent::get_action(double conflict_now, double conflict_trend) {
    // 获取当前状态
    auto state = get_state(conflict_now);
    
    // 通过策略网络计算动作概率
    auto action_prob = policy_net->forward(state);
    
    // 记录这次的动作（用于后续学习）
    last_action = action_prob[0];
    return last_action;
}

/**
 * @brief 更新权重比例
 * @param conflict_now 当前冲突强度
 * @return 更新后的权重比例 ∈ [min_ratio, max_ratio]
 * 
 * 结合历史信息和RL策略调整权重比例
 * ⚠️ 实际惩罚权重 α = base_alpha × weight_ratio = (|f|/512) × ratio
 * 默认ratio=1.0，即α = |f|/512（与源代码一致）
 * RL可以学习将ratio调整到[0.1, 2.0]范围，实现智能优化
 */
/**
 * @brief 计算reward（最终版本）
 * @param conflict_now 当前冲突强度
 * @param current_ratio 当前ratio值
 * @return reward值，范围(-1,1)
 */
double RLAgent::calculate_reward(double conflict_now, double current_ratio) {
    // 首次调用，初始化历史状态
    if (prev_conflict < 0) {
        prev_conflict = conflict_now;
        prev_ratio = current_ratio;
        return 0.0;  // 第一次没有变化，reward=0
    }
    
    double reward = 0.0;

    // ==================== 最终reward：惩罚效率比（无量纲，无放大因子）====================
    // 设计依据：penalty 有效 ⟺ conflict下降 且 f_pure改善同时发生
    //
    // reward = tanh(-conflict_change_rate × fpure_improvement_rate)
    //
    // 物理含义：
    //   conflict_change_rate < 0 (conflict下降) 且 fpure_improvement_rate > 0 (f_pure改善)
    //   → 乘积 < 0 → -乘积 > 0 → tanh > 0 → 正奖励 (penalty有效)
    //
    //   conflict_change_rate > 0 (conflict上升) 且 fpure_improvement_rate > 0 (f_pure改善)
    //   → 乘积 > 0 → -乘积 < 0 → tanh < 0 → 负奖励 (penalty过度，可能阻碍收敛)
    //
    // 优点：
    //   ① 完全用相对变化率，量纲统一，无需任何放大因子
    //   ② tanh自然归一化到(-1,1)，无需手动截断
    //   ③ 全程有非零信号（只要f_pure或conflict有变化）
    if (prev_fitness < 0 || current_fitness_rl < 0) {
        reward = 0.0;  // 无历史，跳过
    } else {
        // f_pure 相对改善率（正=改善，负=变差）
        double fpure_improvement_rate = (prev_fitness - current_fitness_rl)
                                      / (std::fabs(prev_fitness) + 1e-10);
        
        // conflict 相对变化率（正=上升，负=下降）
        double conflict_change_rate = (conflict_now - prev_conflict)
                                    / (prev_conflict + 1e-10);
        
        // 两率之积：有理论依据的无量纲信号
        double raw = -conflict_change_rate * fpure_improvement_rate * 100.0;
        reward = std::tanh(raw);
        
        static int debug_count = 0;
        if (debug_count++ < 15) {
            std::cout << "[Reward-Final]"
                      << " conflict_chg=" << (conflict_change_rate*100) << "%"
                      << " fpure_improv=" << (fpure_improvement_rate*100) << "%"
                      << " raw=" << raw
                      << " reward=" << reward << std::endl;
        }
    }
    
    // 更新历史
    prev_conflict = conflict_now;
    prev_ratio = current_ratio;
    prev_fitness = current_fitness_rl;
    
    return reward;
}

/**
 * @brief 更新权重比例 - 使用真正的RL逻辑
 * @param conflict_now 当前冲突强度
 * @return 更新后的权重比例 ∈ [min_ratio, max_ratio]
 * 
 * RL流程：
 * 1. 获取当前状态（conflict + trend）
 * 2. 使用策略网络决定action
 * 3. 应用action调整ratio
 * 4. 计算reward（评估调整的正确性）
 * 5. 更新策略网络（学习）
 */
double RLAgent::update_weight_ratio(double conflict_now) {
    // 更新冲突历史（这会自动计算趋势）
    update_conflict_history(conflict_now);
    
    // 获取最新趋势
    double trend = conflict_trends.empty() ? 0.0 : conflict_trends.back();
    
    // ========== 真正的RL逻辑 ==========
    
    // 1. 获取状态
    std::vector<double> state = get_state(conflict_now);
    
    // 2. 使用策略网络获取action（范围约[-1, 1]）
    double action = get_action(conflict_now, trend);
    
    // 3. 应用action调整ratio
    // action的含义：对ratio的增量调整
    // 使用较小的步长（0.1），避免调整过激
    double old_ratio = current_weight_ratio;
    current_weight_ratio = current_weight_ratio + 0.1 * action;
    
    // 限制ratio范围
    current_weight_ratio = std::max(min_ratio, 
                                   std::min(max_ratio, 
                                           current_weight_ratio));
    
    // 4. 计算reward
    double reward = calculate_reward(conflict_now, current_weight_ratio);
    last_rl_reward = reward;  // 保存，供外部记录到输出文件
    
    // 5. 更新策略网络（学习）
    update_policy(state, action, reward);
    
    // 调试输出
    static int debug_count = 0;
    if (debug_count++ < 20) {
        std::cout << "[RL] conflict=" << conflict_now 
                  << ", trend=" << trend 
                  << ", action=" << action
                  << ", ratio: " << old_ratio << " → " << current_weight_ratio
                  << " (change: " << ((current_weight_ratio/old_ratio - 1.0)*100) << "%)"
                  << ", reward=" << reward
                  << std::endl;
    }
    
    return current_weight_ratio;
}

/**
 * @brief 更新策略网络
 * @param state 决策时的状态
 * @param action 采取的动作
 * @param reward 获得的奖励
 * @return 策略损失值
 * 
 * 根据奖励信号改进决策策略
 */
double RLAgent::update_policy(const std::vector<double>& state, double action, double reward) {
    // 计算目标动作：当前动作 + 奖励修正
    std::vector<double> target = {action + 0.1 * reward};
    
    // 使用监督学习方式更新网络
    policy_net->update(state, target, learning_rate);
    
    // 返回奖励的绝对值作为损失指标
    return std::abs(reward);
}

/**
 * @brief 更新冲突历史记录并计算趋势
 * @param conflict_now 当前冲突强度
 * 
 * 维护冲突历史的滑动窗口，并计算变化趋势
 */
void RLAgent::update_conflict_history(double conflict_now) {
    // 添加新的冲突记录（乘以1000转换为整数，提高数值稳定性）
    conflict_history.push_back(static_cast<int>(conflict_now * 1000));
    
    // 维护固定大小的历史窗口（最近10次）
    if (conflict_history.size() > 10) {
        conflict_history.erase(conflict_history.begin());
    }
    
    // 计算冲突变化趋势
    if (conflict_history.size() >= 2) {
        // 趋势 = 当前值 - 前一个值
        double trend = conflict_history.back() - conflict_history[conflict_history.size()-2];
        conflict_trends.push_back(trend);
        
        // 维护趋势历史窗口
        if (conflict_trends.size() > 10) {
            conflict_trends.erase(conflict_trends.begin());
        }
    }
}

// ====================================================================
// RLPenaltyEvaluator类实现 - 集成RL的惩罚评估器
// ====================================================================

/**
 * @brief RLPenaltyEvaluator构造函数
 * 
 * 初始化评估器的所有组件：
 * - 继承evaluator基类
 * - 继承RLAgent智能决策能力
 * - 设置问题相关参数
 * - 初始化缓存机制
 * 
 * 注意：初始alpha=0（第一次迭代无惩罚），base_alpha在首次评估后根据适应度设置
 */
RLPenaltyEvaluator::RLPenaltyEvaluator(int* vs, int* cr, int dim, double* gb, double initial_alpha, 
                                      Benchmarks* p_func, int group_index)
    : evaluator(vs, cr, dim, gb), RLAgent(2, 1, 0.01),  // 2输入1输出，学习率0.01
      global_best(gb), p_func(p_func), group_index(group_index),
      alpha(0.0), base_alpha(0.0), current_fitness(1e10),  // 初始α=0，base_alpha待设置
      iter_count(0), adaptive_threshold(0.02),
      conflict_cache_valid(false), conflict_eval_count(0) {
    
    // 获取问题的变量边界
    min_x = p_func->getMinX();
    max_x = p_func->getMaxX();
    var_range = max_x - min_x;  // 变量范围，用于归一化
    
    // 获取当前智能体负责的维度信息
    auto group_dims = p_func->getGroupDim(group_index);
    overlap_size = group_dims.size();  // 重叠维度数量
    overlap_dim = group_dims;          // 重叠维度索引
    
    // 初始化冲突计算缓存
    cached_x = new double[dim];        // 分配缓存空间
    cached_conflict = 0.0;             // 初始化缓存值
    computing_cost = 0.0;              // 初始化计算成本
}

/**
 * @brief 析构函数 - 清理动态分配的内存
 */
RLPenaltyEvaluator::~RLPenaltyEvaluator() {
    delete[] cached_x;  // 释放冲突计算缓存
}

/**
 * @brief 评估单个解的适应度
 * @param x 候选解向量
 * @return 总适应度 = 目标函数值 + 惩罚项
 * 
 * 这是MACPO算法的核心：
 * fitness(x) = f(x) + α * conflict(x, x_global)
 * 其中α是动态调整的惩罚权重
 */
double RLPenaltyEvaluator::evaluate(double* x) {
    // 计算原始目标函数值
    double obj_value = p_func->local_eva(x, group_index);
    
    // 计算冲突惩罚项
    double conflict_penalty = calculate_conflict(x);
    
    // 返回总适应度：目标函数 + 加权惩罚
    return obj_value + alpha * conflict_penalty;
}

/**
 * @brief 批量评估整个种群
 * @param swarm 种群中的所有个体
 * 
 * 对种群中每个个体调用evaluate函数
 */
void RLPenaltyEvaluator::total_evaluate(std::vector<unit*>& swarm) {
    for (auto& particle : swarm) {
        particle->fitness = evaluate(particle->X);
    }
}

/**
 * @brief 计算冲突强度（带缓存优化）
 * @param x 当前解
 * @param use_central_diff 是否使用中心差分（默认false，提高效率）
 * @return 冲突强度值
 * 
 * 三层优化策略：
 * 1. 缓存检查：如果x没变，直接返回缓存结果
 * 2. 间隔计算：每20次迭代才精确计算一次
 * 3. 简化度量：基于位置差异而非复杂梯度
 */
double RLPenaltyEvaluator::calculate_conflict(double* x, bool use_central_diff) {
    // ========== 第一层优化：缓存检查 ==========
    bool is_same_x = true;
    if (conflict_cache_valid) {
        // 检查x是否与缓存的解相同
        for (int i = 0; i < dimension; i++) {
            if (std::abs(x[i] - cached_x[i]) > 1e-10) {
                is_same_x = false;
                break;
            }
        }
    } else {
        is_same_x = false;
    }
    
    // 如果解没变，直接返回缓存的冲突值
    if (is_same_x) {
        return cached_conflict;
    }
    
    // ========== 第二层优化：间隔计算 ==========
    conflict_eval_count++;
    // 每CONFLICT_EVAL_INTERVAL次才进行精确计算，其他时候用缓存
    if (conflict_eval_count % CONFLICT_EVAL_INTERVAL != 0 && conflict_cache_valid) {
        return cached_conflict;
    }
    
    // ========== 第三层优化：简化冲突计算 ==========
    double total_conflict = 0.0;
    
    // 基于位置差异的简化冲突度量（避免复杂的梯度计算）
    for (int i = 0; i < overlap_size && i < overlap_dim.size(); i++) {
        int dim_idx = overlap_dim[i];  // 获取重叠维度索引
        
        if (dim_idx >= 0 && dim_idx < dimension) {
            // 计算归一化的位置差异
            // 只除以var_range，不除以overlap_size
            // 后续会通过动态调整α来达到最优的penalty/f比例
            double diff = std::abs(x[dim_idx] - global_best[dim_idx]);
            total_conflict += diff / var_range;
        }
    }
    
    // ========== 更新缓存 ==========
    std::memcpy(cached_x, x, dimension * sizeof(double));  // 保存当前解
    // 不除以overlap_size，保持conflict的原始规模
    // 将通过动态调整α来适应不同问题的conflict规模
    cached_conflict = total_conflict;
    conflict_cache_valid = true;  // 标记缓存有效
    
    return cached_conflict;
}

/**
 * @brief 自适应通信决策
 * @param x 当前解
 * @return 是否需要通信
 * 
 * 动态调整通信策略：
 * 1. 计算当前冲突强度
 * 2. 根据历史冲突调整阈值
 * 3. 强制最小通信间隔（每10次迭代）
 */
bool RLPenaltyEvaluator::should_communicate(double* x) {
    // 计算当前冲突强度
    double conflict = calculate_conflict(x);
    
    // ========== 自适应阈值调整 ==========
    conflict_levels.push_back(conflict);  // 记录冲突历史
    
    // 维护固定大小的历史窗口
    if (conflict_levels.size() > conflict_history_size) {
        conflict_levels.erase(conflict_levels.begin());
    }
    
    // 基于最近冲突水平动态调整阈值
    if (conflict_levels.size() >= 5) {
        double avg_recent = 0.0;
        for (double c : conflict_levels) {
            avg_recent += c;
        }
        avg_recent /= conflict_levels.size();
        
        // 阈值逐渐趋向于最近的平均冲突水平
        adaptive_threshold = 0.7 * adaptive_threshold + 0.3 * avg_recent;
    }
    
    // ========== 强制通信间隔控制 ==========
    iter_count++;
    
    // 每10次迭代才允许通信一次（避免过频繁通信）
    if (iter_count % 10 != 0) {
        return false;
    }
    
    // ========== 最终通信决策 ==========
    return conflict > adaptive_threshold;
}

/**
 * @brief 获取当前惩罚权重
 */
double RLPenaltyEvaluator::get_alpha() const {
    return alpha;
}

/**
 * @brief 设置惩罚权重（不推荐直接使用）
 * @param new_alpha 新的权重值
 * 
 * 注意：推荐使用set_base_alpha而非直接设置alpha
 */
void RLPenaltyEvaluator::set_alpha(double new_alpha) {
    alpha = new_alpha;
}

/**
 * @brief 根据目标函数值设置基准α（推荐使用）
 * @param fitness_value 当前目标函数值
 * 
 * 使用论文验证的公式：base_alpha = |f| / 512
 * 实际惩罚权重：alpha = base_alpha × weight_ratio
 */
void RLPenaltyEvaluator::set_base_alpha(double fitness_value) {
    current_fitness = fitness_value;
    base_alpha = std::fabs(fitness_value) / 512.0;
    
    // 更新实际α = base_alpha × weight_ratio
    alpha = base_alpha * current_weight_ratio;
}

/**
 * @brief 使用强化学习更新惩罚权重
 * @param x 当前解
 * @param reward 优化奖励信号
 * 
 * 完整的RL学习流程：
 * 1. 计算当前冲突状态
 * 2. 更新冲突历史和趋势
 * 3. 使用RL策略调整weight_ratio（相对比例）
 * 4. 更新实际α = base_alpha × weight_ratio
 * 5. 存储经验并进行策略学习
 */
void RLPenaltyEvaluator::update_rl_weight(double* x, double reward) {
    // 计算当前冲突状态
    double conflict = calculate_conflict(x);
    
    // 注意：不在此处调用 update_conflict_history，
    // update_weight_ratio 内部会调用一次，避免重复写入导致趋势计算错误
    
    // 将当前fitness快照注入RLAgent，供方案3的calculate_reward使用
    current_fitness_rl = current_fitness;
    
    // ========== RL权重比例更新 ==========
    // update_weight_ratio返回新的weight_ratio ∈ [min_ratio, max_ratio]
    double new_ratio = update_weight_ratio(conflict);
    
    // 更新实际α = base_alpha × weight_ratio
    // 如果base_alpha尚未设置(=0)，则保持alpha=0
    if (base_alpha > 0) {
        alpha = base_alpha * new_ratio;
    }
    
    // ========== 经验存储和学习 ==========
    auto state = get_state(conflict);  // 获取当前状态
    store_experience(state, last_action, reward);  // 存储决策经验
    
    // 如果经验足够，进行策略学习
    if (replay_buffer.size() >= 32) {
        update_policy();  // 批量学习经验
    }
}

/**
 * @brief 设置变量开关状态
 */
void RLPenaltyEvaluator::set_variable_switch(int dim, int value) {
    if (dim >= 0 && dim < dimension) {
        variable_switch[dim] = value;
    }
}

/**
 * @brief 更新全局最优解
 * @param new_gb 新的全局最优解
 * 
 * 当全局最优解更新时，冲突缓存失效
 */
void RLPenaltyEvaluator::set_global_best(double* new_gb) {
    std::memcpy(global_best, new_gb, dimension * sizeof(double));
    conflict_cache_valid = false;  // 全局最优更新时，冲突缓存失效
}

/**
 * @brief 获取问题维度
 */
int RLPenaltyEvaluator::get_dimension() const {
    return dimension;
}

/**
 * @brief 获取变量下界
 */
double RLPenaltyEvaluator::get_min_x() const {
    return min_x;
}

/**
 * @brief 获取变量上界
 */
double RLPenaltyEvaluator::get_max_x() const {
    return max_x;
}

/**
 * @brief 获取学习率
 */
double RLPenaltyEvaluator::get_lr() const {
    return learning_rate;
} 