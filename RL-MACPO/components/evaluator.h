#ifndef EVALUATOR_H
#define EVALUATOR_H

#include <vector>
#include <memory>
#include <random>
#include <cmath>
#include <algorithm>
#include <cfloat>
#include <deque>
#include <tuple>
#include <cstring>  // 添加cstring头文件以使用memcpy
#include "./struct.h"  // 先包含struct.h，使用其中定义的unit结构体
#include "../Benchmarks/Benchmarks.h"  // 添加完整的Benchmarks类定义

// 前向声明
// class Benchmarks; // 已不需要，因为我们直接包含了头文件

/**
 * @class evaluator
 * @brief 评估器基类 - 定义了所有评估器的通用接口
 * 
 * 这是MACPO算法中最重要的组件之一，负责：
 * 1. 计算个体的适应度值（包含惩罚项）
 * 2. 检测智能体间的冲突程度
 * 3. 决定是否需要进行通信协商
 * 4. 管理惩罚权重的动态调整
 */
class evaluator {
protected:
    int* variable_switch;  // 变量开关数组：控制哪些变量参与协商（1=参与，0=不参与）
    int* conflict_record;  // 冲突记录数组：记录每个变量的历史冲突情况
    int dimension;         // 问题维度：优化问题的总变量个数
    double* global_best;   // 全局最优解：当前找到的最好解

public:
    // 构造函数：初始化评估器的基本参数
    evaluator(int* vs, int* cr, int dim, double* gb) 
        : variable_switch(vs), conflict_record(cr), dimension(dim), global_best(gb) {}
    
    // 虚析构函数：确保多态删除时调用正确的析构函数
    virtual ~evaluator() = default;

    // 纯虚函数：评估单个解的适应度（目标函数值+惩罚项）
    virtual double evaluate(double* x) = 0;
    
    // 纯虚函数：批量评估整个种群的适应度
    virtual void total_evaluate(std::vector<unit*>& swarm) = 0;
    
    // 纯虚函数：判断当前解是否需要与邻居智能体通信
    virtual bool should_communicate(double* x) = 0;
    
    // 纯虚函数：获取当前惩罚权重
    virtual double get_alpha() const = 0;
    
    // 纯虚函数：设置新的惩罚权重
    virtual void set_alpha(double new_alpha) = 0;
    
    // 纯虚函数：使用强化学习更新惩罚权重
    virtual void update_rl_weight(double* x, double reward) = 0;
    
    // 纯虚函数：设置变量开关状态
    virtual void set_variable_switch(int dim, int value) = 0;
    
    // 纯虚函数：更新全局最优解
    virtual void set_global_best(double* new_gb) = 0;
    
    // 纯虚函数：获取问题维度
    virtual int get_dimension() const = 0;
    
    // 纯虚函数：获取变量下界
    virtual double get_min_x() const = 0;
    
    // 纯虚函数：获取变量上界
    virtual double get_max_x() const = 0;
    
    // 纯虚函数：计算冲突强度（核心功能）
    virtual double calculate_conflict(double* x, bool use_central_diff = true) = 0;
    
    // 纯虚函数：获取学习率
    virtual double get_lr() const = 0;
};

/**
 * @class SimpleNet
 * @brief 简单神经网络类 - 用于强化学习的策略网络
 * 
 * 这是一个轻量级的全连接神经网络，专门为实时优化环境设计：
 * 1. 输入：当前冲突状态和趋势信息
 * 2. 输出：权重调整建议
 * 3. 学习：基于优化效果调整策略
 */
class SimpleNet {
private:
    std::vector<std::vector<double>> weights;  // 权重矩阵：连接输入层和输出层
    std::vector<double> bias;                  // 偏置向量：每个神经元的偏置值
    std::mt19937 rng;                         // 随机数生成器：用于权重初始化

public:
    // 构造函数：创建指定输入输出维度的神经网络
    SimpleNet(int input_dim, int output_dim);
    
    // 前向传播：根据输入计算网络输出
    std::vector<double> forward(const std::vector<double>& input);
    
    // 反向传播：根据目标值更新网络权重
    void update(const std::vector<double>& input, const std::vector<double>& target, double learning_rate);
};

/**
 * @struct Transition
 * @brief 经验回放结构 - 存储强化学习的历史经验
 * 
 * 每个Transition记录一次决策的完整信息：
 * - state: 当时的环境状态（冲突强度、趋势等）
 * - action: 采取的行动（权重调整量）
 * - reward: 获得的奖励（优化效果）
 * - priority: 经验的重要性（用于优先回放）
 */
struct Transition {
    std::vector<double> state;  // 状态：决策时的环境信息
    double action;              // 行动：权重调整的具体数值
    double reward;              // 奖励：这次决策带来的优化效果
    double priority;            // 优先级：重要经验会被更频繁地学习
};

/**
 * @class RLAgent
 * @brief 强化学习代理类 - MACPO算法的智能决策核心
 * 
 * 这个类实现了智能的权重调整策略：
 * 1. 观察当前的冲突状态和历史趋势
 * 2. 使用神经网络决定如何调整惩罚权重
 * 3. 根据优化效果学习和改进决策策略
 * 4. 使用经验回放机制提高学习效率
 */
class RLAgent {
protected:
    std::shared_ptr<SimpleNet> policy_net;     // 策略网络：决策的"大脑"
    double current_weight_ratio;               // 当前权重比例：RL学习的比例系数 ∈ [0.1, 2.0]
    double learning_rate;                      // 学习率：控制学习的速度
    double last_action;                        // 上次行动：记录最近一次的权重调整
    std::vector<int> conflict_history;         // 冲突历史：记录最近的冲突强度变化
    std::vector<double> conflict_trends;       // 冲突趋势：分析冲突是在增加还是减少
    std::deque<Transition> replay_buffer;      // 经验回放缓冲区：存储学习经验
    const int buffer_size = 64;               // 缓冲区大小：最多存储64个经验
    std::mt19937 rng{std::random_device{}()};  // 随机数生成器
    
    // 新增：比例系数范围参数（基于论文的512设计）
    // ⚠️ 重要：default_ratio=1.0，不再额外缩放！
    // 这样 α = (|f|/512) × 1.0 = |f|/512，与源代码一致
    const double min_ratio = 0.1;          // 最小比例：0.1 (更保守)
    const double max_ratio = 2.0;          // 最大比例：2.0 (更激进)
    const double default_ratio = 1.0;      // 默认比例：1.0 (论文基准)
    
    // 用于计算最终reward的历史状态
    double prev_conflict = -1.0;           // 上一次的conflict（-1表示未初始化）
    double prev_ratio = -1.0;              // 上一次的ratio（-1表示未初始化）
    double prev_fitness = -1.0;            // 上一次的fitness
    double current_fitness_rl = -1.0;      // 当前fitness快照（由update_rl_weight注入）
    double last_rl_reward = 0.0;           // 最近一次的内部RL reward，供外部读取记录

public:
    // 构造函数：初始化RL代理
    RLAgent(int state_dim = 2, int action_dim = 1, double lr = 0.01);
    
    // 获取当前状态：将环境信息转换为神经网络的输入
    std::vector<double> get_state(double conflict_now);
    
    // 获取行动：基于当前状态决定权重调整量
    double get_action(double conflict_now, double conflict_trend);
    
    // 计算reward：评估ratio调整的正确性
    double calculate_reward(double conflict_now, double current_ratio);
    
    // 获取最近一次的内部RL reward（供输出文件记录）
    double get_last_rl_reward() const { return last_rl_reward; }
    
    // 更新fitness历史（用于方案3）
    void update_fitness_history(double fitness) { prev_fitness = fitness; }
    
    // 更新权重比例：结合RL建议调整当前比例系数
    double update_weight_ratio(double conflict_now);
    
    // 更新策略：根据奖励改进决策网络
    double update_policy(const std::vector<double>& state, double action, double reward);
    
    // 更新冲突历史：记录新的冲突信息并计算趋势
    void update_conflict_history(double conflict_now);
    
    // 获取当前权重比例
    double get_weight_ratio() const { return current_weight_ratio; }
    
    // 存储经验：将新的决策经验保存到回放缓冲区
    void store_experience(const std::vector<double>& state, double action, double reward) {
        if(replay_buffer.size() >= buffer_size) {
            replay_buffer.pop_front();  // 缓冲区满时删除最老的经验
        }
        // 使用奖励绝对值作为优先级：重要的经验会被优先学习
        double priority = std::abs(reward);
        replay_buffer.push_back({state, action, reward, priority});
    }

    // 优先级采样：根据经验重要性选择学习样本
    std::vector<size_t> sample_indices() {
        std::vector<double> priorities;
        for (const auto& t : replay_buffer) {
            priorities.push_back(t.priority);
        }
        // 重要的经验有更高概率被选中
        std::discrete_distribution<> dist(priorities.begin(), priorities.end());
        
        std::vector<size_t> indices;
        for (int i = 0; i < 32; ++i) {  // 每次采样32个经验
            indices.push_back(dist(rng));
        }
        return indices;
    }

    // 批量更新策略：使用多个经验同时改进决策网络
    double update_policy() {
        if(replay_buffer.size() < 32) return 0.0;  // 经验不够时不学习
        
        // 按优先级采样重要经验
        auto indices = sample_indices();
        
        double total_loss = 0.0;
        // 小批量更新：用32个经验同时训练网络
        for(auto idx : indices) {
            const auto& t = replay_buffer[idx];
            total_loss += update_policy(t.state, t.action, t.reward);
        }
        replay_buffer.clear();  // 清空缓冲区
        return total_loss / 32.0;  // 返回平均损失
    }
};

/**
 * @class RLPenaltyEvaluator
 * @brief RL惩罚评估器类 - 集成强化学习的智能评估器
 * 
 * 这是MACPO算法的核心组件，结合了传统惩罚方法和现代强化学习：
 * 
 * 工作原理：
 * 1. 计算目标函数值：f(x) = 原始目标函数
 * 2. 计算冲突惩罚：penalty = alpha * conflict(x, global_best)
 * 3. 最终适应度：fitness = f(x) + penalty
 * 4. 智能调整alpha：使用RL代理根据优化效果动态调整
 * 
 * 关键创新：
 * - 缓存机制：避免重复计算相同解的冲突
 * - 自适应阈值：动态调整通信触发条件
 * - 智能权重：RL代理学习最优惩罚强度
 */
class RLPenaltyEvaluator : public evaluator, protected RLAgent {
private:
    double* global_best;           // 全局最优解：所有智能体共享的最好解
    int overlap_size;              // 重叠维度大小：当前智能体管理的重叠变量数量
    double var_range;              // 变量范围：max_x - min_x，用于归一化
    Benchmarks* p_func;            // 基准函数指针：具体的优化问题
    int group_index;               // 组索引：当前智能体的编号
    std::vector<int> overlap_dim;  // 重叠维度：哪些变量是重叠的
    std::vector<int> which_group;  // 所属组：变量属于哪些组
    double min_x;                  // 最小值：变量下界
    double max_x;                  // 最大值：变量上界
    double alpha;                  // 惩罚系数：实际使用的惩罚权重 = base_alpha * weight_ratio
    double base_alpha;             // 基准α：|f|/512，论文验证的最佳基准值（动态更新）
    double current_fitness;        // 当前适应度：用于计算base_alpha
    double computing_cost;         // 计算成本：评估函数的调用次数统计
    static double avg_conflict;    // 静态成员：跟踪平均冲突水平
    int iter_count;                // 迭代计数器：用于控制通信频率
    double adaptive_threshold;     // 自适应阈值：动态调整的通信触发阈值
    std::vector<double> conflict_levels; // 冲突水平历史：用于计算自适应阈值
    const int conflict_history_size = 10; // 历史大小：保持最近10次的冲突记录
    
    // 冲突计算的优化机制
    double cached_conflict;        // 缓存的冲突值：避免重复计算
    double* cached_x;              // 缓存的解向量：上次计算冲突时的解
    bool conflict_cache_valid;     // 缓存有效性：标记缓存是否可用
    int conflict_eval_count;       // 冲突评估计数：控制精确计算频率
    const int CONFLICT_EVAL_INTERVAL = 20;  // 评估间隔：每20次才精确计算一次

public:
    // 构造函数：初始化RL惩罚评估器（初始α=0）
    RLPenaltyEvaluator(int* vs, int* cr, int dim, double* gb, double initial_alpha, 
                      Benchmarks* p_func, int group_index);
    
    // 析构函数：清理动态分配的内存
    ~RLPenaltyEvaluator() override;
    
    // 评估函数：计算解的总适应度（目标函数值+惩罚项）
    double evaluate(double* x) override;
    
    // 批量评估：计算整个种群的适应度
    void total_evaluate(std::vector<unit*>& swarm) override;
    
    // 冲突计算：测量当前解与全局最优解的冲突程度
    double calculate_conflict(double* x, bool use_central_diff = false) override;
    
    // 通信判断：决定是否需要与邻居智能体协商
    bool should_communicate(double* x) override;
    
    // 获取实际惩罚权重
    double get_alpha() const override;
    
    // 设置惩罚权重（不推荐直接使用，应该用set_base_alpha）
    void set_alpha(double new_alpha) override;
    
    // 设置基准α（根据目标函数值）- 推荐使用
    void set_base_alpha(double fitness_value);
    
    // 获取基准α
    double get_base_alpha() const { return base_alpha; }
    
    // 获取RL学习的权重比例
    double get_weight_ratio() const { return current_weight_ratio; }
    
    // 获取最近一次内部RL reward（转发自RLAgent，因protected继承需显式暴露）
    double get_last_rl_reward() const { return RLAgent::get_last_rl_reward(); }
    
    // RL权重更新：使用强化学习调整惩罚权重比例
    void update_rl_weight(double* x, double reward) override;
    
    // 设置变量开关
    void set_variable_switch(int dim, int value) override;
    
    // 更新全局最优解
    void set_global_best(double* new_gb) override;
    
    // 获取维度信息
    int get_dimension() const override;
    double get_min_x() const override;
    double get_max_x() const override;
    double get_lr() const override;
};

#endif // EVALUATOR_H