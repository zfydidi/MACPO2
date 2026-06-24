#ifndef BENCHMARKS_H // 如果没有定义 BENCHMARKS_H 宏
#define BENCHMARKS_H // 定义 BENCHMARKS_H 宏，防止重复包含此头文件

#include <string>
#include <vector>
#include "../util/json.hpp"// 包含 JSON 库，用于读取配置数据
using json = nlohmann::json;// 使用 nlohmann::json 的 json 命名空间别名
using std::string;
using std::vector;

/**
 * @brief 基准测试类，用于实现多种评估函数及其特性。
 */
// 定义一个基准测试类 Benchmarks
class Benchmarks {
private:
    int group_num;                  ///< 分组的数量
    json func_config;               ///< 函数配置，以 JSON 格式存储
    string funcID;                  ///< 函数 ID，用于标识当前使用的基准测试函数
    template<typename T>T** read_data(string); ///< 模板函数，用于读取数据

    // 第一类函数的变量
    int **group;                    ///< 组的二维数组，每组包含多个索引
    double ***R, **xopt;            ///< 旋转矩阵 R 和最优解向量 xopt
    double local_eva_for_global_solution(double*, int); ///< 局部评估函数，用于计算全局解
    bool overlap_grouping;          ///< 是否启用重叠分组策略
    double local_eva_type1(double* x, int groupIndex); ///< 第一类函数的局部评估

    // 第二类函数的变量
    double **R_global, **A, **W = nullptr; ///< 全局旋转矩阵 R_global，矩阵 A 和权重矩阵 W
    bool if_rotate;                ///< 是否启用旋转变换
    bool if_shift;                 ///< 是否启用平移变换
    double scaling_factor;         ///< 缩放因子
    double local_eva_type2(double* x, int groupIndex); ///< 第二类函数的局部评估
    double global_eva_type2(double* x); ///< 第二类函数的全局评估

    // 第三类函数的变量
    double local_eva_type3(double* x, int groupIndex); ///< 第三类函数的局部评估
    int funcClass;                ///< 函数分类编号
    double weight;                ///< 权重值
    bool if_heterogeneous;        ///< 是否启用异构处理

    // 第四类函数的变量
    double local_eva_type4(double* x, int groupIndex); ///< 第四类函数的局部评估
    int target_num;              ///< 目标数量
    int source_num;              ///< 来源数量
    int coordinate_dim;          ///< 坐标维度
    double **target, **source, **noisy_dis = nullptr; ///< 噪声相关的距离矩阵
    double **noisy_elevation = nullptr, **noisy_azimuth = nullptr; ///< 噪声仰角和噪声方位角

    // 第五类函数的变量
    double local_eva_type5(double* x, int groupIndex); ///< 第五类函数的局部评估
    bool dfs(int x);                                 ///< 深度优先搜索函数
    double KM();                                    ///< KM 算法，用于最优匹配
    int **match_truth;                              ///< 匹配的二维数组
	// const int N=205;
	// double w[N][N];
	// double la[N],lb[N];
	// bool va[N],vb[N];
	// int match[N];
	// int n;
    double **w;                                     ///< 权重矩阵
    double *Lx, *Ly;                                ///< x 和 y 节点的标签
    bool *VisX, *VisY;                              ///< x 和 y 节点的访问标记
    int *MatchY;                                    ///< y 节点的匹配状态
    double* Slack;                                  ///< 懒惰矩阵，用于优化计算

public:
    int max_eva_times;                              ///< 最大评估次数
    int eva_count;                                  ///< 当前评估次数
    bool reach_max_eva_times;                       ///< 是否达到最大评估次数

    /**
     * @brief 构造函数，初始化 Benchmarks 对象。
     * @param ID 函数 ID，用于标识测试函数。
     * @param max_eva_times 最大评估次数，默认值为 3000000。
     * @param overlap_grouping 是否启用重叠分组策略，默认为 true。
     */
    Benchmarks(string ID, int max_eva_times = 3000000, bool overlap_grouping = true);

    /**
     * @brief 析构函数，释放 Benchmarks 对象的资源。
     */
    ~Benchmarks();

    // 基准测试功能方法
    double global_eva(double* x);                  ///< 全局评估函数
    double local_eva(double* x, int groupIndex);   ///< 局部评估函数
    double getMinX();                              ///< 获取最小 X 值
    double getMaxX();                              ///< 获取最大 X 值
    int getGroupNum();                             ///< 获取分组数量
    int getDimension();                            ///< 获取问题维度
    vector<int> getOverlapDim(int g1, int g2);     ///< 获取指定两个分组的重叠维度
    vector<int> getOverlapDimIndex(int g1, int g2);///< 获取重叠维度的索引
    vector<int> getGroupDim(int g);                ///< 获取分组的维度索引
    vector<int> getGroupExcluDim(int groupIndex);  ///< 获取分组排除的维度索引
    vector<int> getOverlapGroup(int g);            ///< 获取重叠分组索引
    bool reachMaxEva();                            ///< 检查是否达到最大评估次数
    double getLocalOpt(int groupIndex);            ///< 获取分组的局部最优值
    double** getNetworkGraph();                    ///< 获取网络图矩阵
    double getMatchRes(double* x);                 ///< 获取匹配结果
    double getRMSE(double* x);                     ///< 获取均方根误差
    void reload_target_pos(string, string);        ///< 重新加载目标位置信息
    void reload_track_data(string target_fname, string source_fname, string network_fname, string measurement_fname, string = ""); ///< 重新加载轨迹数据
    void change_target_num(int);                   ///< 修改目标数量
};

#endif    // 结束条件编译