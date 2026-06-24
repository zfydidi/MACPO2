#ifndef OPTIMIZER_H
#define OPTIMIZER_H

#include <cfloat>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <algorithm>
#include <iostream>
#include <random>
#include <vector>

#include "../Benchmarks/Benchmarks.h"
#include "./evaluator.h"
#include "./struct.h"
#include <Eigen/Dense>// Eigen库，用于线性代数操作
using std::vector;
using std::cout;
using std::endl;
using Eigen::VectorXd;//引入 Eigen 库中的 VectorXd 类型，用于表示动态大小的向量

using std::cout;// 引用标准库中的 cout 以打印输出
using std::sort;// 引用标准库中的 sort 用于排序
using Eigen::MatrixXd;// 引用 Eigen 库中的 MatrixXd 类型，用于高精度矩阵运算
using Eigen::Matrix;// 引用 Eigen 库中的 Matrix 类型
using Eigen::VectorXd;// 引用 Eigen 库中的 VectorXd 类型，用于高精度向量运算
using namespace Eigen;// 使用 Eigen 命名空间

/** MPI rank for paired init files (OpenMPI / PMI). */
static inline int macpo_mpi_rank_from_env(void)
{
    const char *e = getenv("OMPI_COMM_WORLD_RANK");
    if (e) return atoi(e);
    e = getenv("PMI_RANK");
    if (e) return atoi(e);
    return 0;
}

// 随机打乱数组
void random_shuffle_array(int* arr, int size) {
    std::random_device rd;
    std::mt19937 g(rd());
    std::shuffle(arr, arr + size, g);
}

/**
 * @brief 交换两个整数的值。
 *
 * 这个函数通过使用一个临时变量来交换两个整数的值。
 *
 * @param a 第一个整数。
 * @param b 第二个整数。
 */
// 交换两个整数变量的值
void swap(int &a, int &b)
{
    int temp = a;
    a = b;
    b = temp;
}

/**
 * @brief 代表优化器的基类。
 *
 * 该类定义了优化器的基本结构，包括初始化、更新和获取最佳粒子的功能。
 */

// 基础类 optimizer，用于定义优化器的基本结构
class optimizer
{
public:
    // 优化器的基本参数
        /**
     * @brief 粒子群的大小和最佳粒子的索引。
     *
     * 这两个变量分别代表粒子群的大小和最佳粒子的索引。
     */
    int swarmSize, bestParIndex; // 粒子群大小和最佳粒子索引

    /** @brief 用于评估粒子的评估器。 */
    evaluator *Evaluator;       // 指向评估器的指针

    /** @brief 优化器的维度和边界。 */
    int dimension, minX, maxX, groupSize;// 维度，最小值，最大值和分组大小

    /** @brief 维度分组列表和粒子群。 */
    vector<int> groupDim;// 分组维度列表
    vector<unit*> swarm;// 种群，存储指向 unit 对象的指针
    vector<unit*> swarm_ordered;// 排序后的种群

    /** @brief 虚析构函数，确保正确的多态删除。 */
    virtual ~optimizer() = default;

/**
* @brief 构造函数，初始化优化器的基本参数。
* 该构造函数初始化了粒子群的大小、评估器、维度等基本参数。
* @param swarmSize 粒子群的大小。
* @param Evaluator 评估器的指针。
* @param groupDim 粒子的维度分组列表。
*/
// 构造函数初始化优化器的基本参数
optimizer(int swarmSize, evaluator *Evaluator, vector<int> groupDim)
{
   this->swarmSize = swarmSize;/// 初始化种群大小
   this->Evaluator = Evaluator;/// 初始化评估器
   this->dimension = Evaluator->get_dimension();/// 初始化维度
   this->minX = Evaluator->get_min_x();/// 初始化最小值
   this->maxX = Evaluator->get_max_x();/// 初始化最大值
   this->groupDim = groupDim;/// 初始化分组维度
   this->groupSize = groupDim.size();/// 初始化分组大小
}

/**
       * @brief 纯虚函数，用于初始化优化器。
       *
       * 该函数应该由派生类实现。
       */
// 定义纯虚函数：初始化、生成新的粒子群、获取最佳个体
// 纯虚函数，供子类实现，初始化方法
virtual void init() = 0;

/**
     * @brief 纯虚函数，用于生成新一代粒子。
     *
     * 该函数应该由派生类实现。
     *
     * @param success 用于指示成功与否的标志。
     */
// 纯虚函数，供子类实现，生成新一代
virtual void generation(int &) = 0;

    /**
      * @brief 纯虚函数，用于获取最佳粒子的参数。
      *
      * 该函数应该由派生类实现。
      *
      * @return 返回最佳粒子的参数数组。
      */
// 纯虚函数，供子类实现，获取最佳个体
virtual double *getBestPar() = 0;

    /**
        * @brief 重新排序粒子群，按照适应度排序。
        *
        * 该函数评估粒子群并按照适应度排序粒子。
        */
// 重新排序粒子群，按适应度排序
void resort(){
   Evaluator->total_evaluate(swarm);// 对种群进行评估
   sort(swarm.begin(), swarm.end(),cmp_unit_pointer);// 按适应度排序种群
}

    /**
       * @brief 设置新的分组维度。
       *
       * @param groupDim 新的分组维度列表。
       */
// 设置新的分组维度
void setGroup(vector<int> groupDim){
   this->groupDim=groupDim;
   this->groupSize = groupDim.size();
}
};

/**
 * @brief 用于比较两个三维坐标的粒子。
 *
 * 该函数通过比较三维坐标的各个维度来判断粒子的顺序。
 *
 * @param a 第一个三维坐标。
 * @param b 第二个三维坐标。
 * @return 如果第一个粒子应该排在第二个粒子之前，返回 true。
 */
// 比较函数，用于3D坐标的粒子排序（比较两个三维向量的大小）
bool cmp_3d(double* a, double* b){
double range = 0;// 定义范围值
// 比较第一个维度的差值是否大于范围值
if(fabs(a[0]-b[0]) > range)
   return a[0] < b[0];// 如果是，返回第一个维度的比较结果
// 比较第二个维度的差值是否大于范围值
if(fabs(a[1] - b[1]) > range)
   return a[1] < b[1];// 如果是，返回第二个维度的比较结果
// 最后比较第三个维度的大小
return a[2]<b[2];
}

/**
 * @brief 用于比较两个二维坐标的粒子。
 *
 * 该函数通过比较二维坐标的各个维度来判断粒子的顺序。
 *
 * @param a 第一个二维坐标。
 * @param b 第二个二维坐标。
 * @return 如果第一个粒子应该排在第二个粒子之前，返回 true。
 */
// 比较函数，用于2D坐标的粒子排序（比较两个二维向量的大小）
bool cmp_2d(double* a, double* b){
double range = 5;// 定义范围值
// 比较第一个维度的差值是否大于范围值
if(fabs(a[0]-b[0]) > range)
   return a[0] < b[0];// 如果是，返回第一个维度的比较结果
// 否则比较第二个维度的大小
return a[1]<b[1];
}

/**
 * @brief 竞争性群体优化器（CSO）类，继承自优化器。
 *
 * 该类扩展了基础优化器类，具体实现了竞争性群体优化算法的行为，包括初始化、粒子更新和优化策略。
 */
// 基于竞争的群体优化器类，继承自 optimizer
class optimizer_CSO:public optimizer
{
public:
    using optimizer::optimizer; /// 使用基类optimizer构造函数
    /** @brief 竞争性群体优化器特有的参数。 */
    double phi;/// 调节参数
    double* mean_X;/// 平均位置
    bool if_repair;/// 是否修复标志
    double bestFit;/// 最佳适应度

    /**
 * @brief 设置是否需要修复粒子速度。
 *
 * @param v 如果为 true，则修复速度。
 */
    // 设置是否修复速度
void set_repair(bool v){
   if_repair = v;
}

/**
     * @brief 初始化粒子群的粒子位置和速度。
     *
     * 该函数根据指定的维度分组和其他参数初始化粒子的位置信息和速度。
     */
// 初始化粒子群
void init(){
   if_repair = false;// 初始不修复
   int d=groupDim.size();// 获取分组维度的大小

   // 根据分组维度大小设置 phi 参数
   if(d >= 2000)
       phi = 0.2;
   else if(d >= 1000)
       phi = 0.1;
   else if(d >=250)
       phi = 0.05;
   else
       phi = 0;

   mean_X = new double[dimension]{0};// 初始化 mean_X 数组值为0，数组大小为维度
   bestParIndex = 0;// 初始化最佳粒子索引为 0
   double *zeros = new double[dimension]{0};// 初始化一个零值向量，向量大小为维度

   // 初始化每个粒子的坐标及速度
   for (int i = 0; i < swarmSize; i++)
   {
       particle* newPar = new particle(zeros, dimension);// 创建新粒子

       for (int j = 0; j < groupSize; j++)
       {
           int index = groupDim[j];// 获取当前分组维度的索引
           newPar->X[index] = minX + 1.0 * rand() / RAND_MAX * (maxX - minX);// 初始化粒子位置
           newPar->v[index] = 0;// 初始化粒子速度为 0
       }
       swarm.push_back(newPar);// 将新粒子加入种群
       swarm_ordered.push_back(newPar);// 将新粒子加入有序种群
       repair(i);// 修复粒子位置

       swarm[i]->fitness = Evaluator->evaluate(swarm[i]->X);// 评估粒子的适应度
       if (swarm[i]->fitness < swarm[bestParIndex]->fitness)
           bestParIndex = i;// 更新最佳个体索引
   }
}

    /**
       * @brief 计算粒子群的均值位置。
       */
// 计算种群中所有粒子在分组维度上的平均位置（每个维度）
void compute_mean(){
   for(int d:groupDim){
       mean_X[d] = 0;
       for(int i=0;i<swarmSize;i++){
           mean_X[d] += swarm[i]->X[d];// 累加各粒子在当前维度上的位置
       }
       mean_X[d] /= swarmSize;// 计算平均位置
   }
   return;
}

    /**
      * @brief 获取最佳粒子的位置。
      *
      * @return 返回最佳粒子的位置数组。
      */
// 获取最佳个体位置
double *getBestPar()
{
   double *res = new double[dimension];
   memcpy(res, swarm[bestParIndex]->X, dimension * sizeof(double));// 复制最佳个体位置
   return res;
}

    /**
      * @brief 修复粒子的位置，适用于二维或三维坐标。
      *
      * @param l 粒子的索引。
      * @param coordinate_dim 粒子的维度（2D 或 3D）。
      */
// 修复粒子位置，按2D或3D坐标进行排序
void repair(int l, int coordinate_dim=2){
   if(if_repair == false)
       return;

   // 根据维度创建位置数组
   double **positions = new double*[dimension/coordinate_dim];
   for(int tar=0;tar<dimension/coordinate_dim;tar++){
       if(coordinate_dim == 3)
           positions[tar] = new double[3]{swarm[l]->X[tar*3],swarm[l]->X[tar*3+1],swarm[l]->X[tar*3+2]};
       else if (coordinate_dim == 2)
           positions[tar] = new double[2]{swarm[l]->X[tar*2],swarm[l]->X[tar*2+1]};
   }

   // 根据坐标维度进行排序并修复位置
   if (coordinate_dim == 3){
       sort(positions, positions+dimension/3, cmp_3d);
       for(int tar=0;tar<dimension/3;tar++){
           swarm[l]->X[tar*3] = positions[tar][0];
           swarm[l]->X[tar*3+1] = positions[tar][1];
           swarm[l]->X[tar*3+2] = positions[tar][2];
           delete[] positions[tar];
       }
       delete[] positions;
   }
   else if(coordinate_dim == 2){
       sort(positions, positions+dimension/2, cmp_2d);
       for(int tar=0;tar<dimension/2;tar++){
           swarm[l]->X[tar*2] = positions[tar][0];
           swarm[l]->X[tar*2+1] = positions[tar][1];
           delete[] positions[tar];
       }
       // 释放位置数组内存
       delete[] positions;
   }
}
    /**
        * @brief 根据适应度更新粒子的位置和速度。
        *
        * 该函数使用竞争性群体优化规则来更新粒子的速度和位置。
        *
        * @param success 用于指示成功的标志。
        */
// 一次粒子群迭代更新
void generation(int &success){
   compute_mean();// 计算种群中所有粒子在分组维度上的平均位置
   for(int i=0;i<swarmSize;i++)
       repair(i);// 修复粒子

   int arr[swarmSize];
   for(int i=0;i<swarmSize;i++)
       arr[i] = i;

   random_shuffle_array(arr, swarmSize);// 随机打乱种群顺序
   // for(int i=0;i<10;i++)
   //     cout<<arr[i]<<" ";
   // cout<<endl;
   int half_pos = swarmSize/2;// 计算一半种群大小
   for(int i=0;i<half_pos;i++){
       int j = swarmSize-i-1;// 对称索引
       int a = arr[i];// 数组中的第 i 个索引
       int b = arr[j];// 数组中的倒数第 i 个索引
       int w,l;// 胜者和败者的索引

       // 比较适应度，确定胜者和败者
       if(swarm[a]->fitness<swarm[b]->fitness){
           // 如果 a 的适应度更好，a 为胜者，b 为败者
           w = a;
           l = b;
       }else{
           // 否则，b 为胜者，a 为败者
           w = b;
           l = a;
       }
       // 更新败者位置和速度
       for(int index:groupDim){
           double r1 = rand() * 1.0 / RAND_MAX;// 随机数 r1
           double r2 = rand() * 1.0 / RAND_MAX;// 随机数 r2
           double r3 = rand() * 1.0 / RAND_MAX;// 随机数 r3
           // 计算新的速度
           double new_v = r1 * ((particle *)swarm[l])->v[index] + r2 * (swarm[w]->X[index] - swarm[l]->X[index]) + r3 * phi * (mean_X[index] - swarm[l]->X[index]);

           swarm[l]->X[index] = swarm[l]->X[index] + new_v;// 更新位置
           ((particle *)swarm[l])->v[index] = new_v;// 更新速度

           // 边界检查
           if (swarm[l]->X[index] > maxX)
           {
               swarm[l]->X[index] = maxX;
           }
           if (swarm[l]->X[index] < minX)
           {
               swarm[l]->X[index] = minX;
           }
       }
       repair(l);// 修复粒子

       swarm[l]->fitness = Evaluator->evaluate(swarm[l]->X);// 评估粒子的适应度
       if(swarm[l]->fitness<swarm[bestParIndex]->fitness){
           bestParIndex = l;// 更新最佳个体索引
       }

       if (swarm[l]->fitness < bestFit)
           bestFit = swarm[l]->fitness;  // 更新 bestFit
   }
}
};

/**
 * @class optimizer_LLSO
 * @brief 基于等级的粒子群优化算法（Level-wise Swarm Optimization, LLSO）类。
 *
 * 该类继承自优化器（optimizer）类，定义了基于等级的优化器，使用粒子群优化算法（PSO）优化问题。
 * 优化器在不同层级间进行协同优化，并根据层级的适应度选择最合适的粒子群参数。
 */
// 定义基于等级的优化器类 optimizer_LLSO
class
optimizer_LLSO : public optimizer
{
public:
    /**
     * @brief 继承父类构造函数。
     */
using optimizer::optimizer;// 继承父类构造函数

    /**
     * @brief 优化器的基础参数
     *
     * NL: 层级数量
     * LS: 每个层级中的粒子数
     * NL_index: 当前选择的层级索引
     * epsilon: 控制参数
     * bestFit: 当前最佳适应度
     * rand_level_set: 随机层级集合（层级的大小池）
     * rand_level_size: 随机层级集合的大小
     * level_size_performance: 各层级性能
     * fopt: 最优适应度
     */
//优化器基础参数
int NL, LS, NL_index=0;// 层级数量，层级大小，层级索引
double epsilon = 0.5;// 控制参数
double bestFit;// 最佳适应度
int *rand_level_set; // 随机层级集合  the pool of the number of levels层数池
int rand_level_size;// 随机层级大小
double *level_size_performance;// 各层级性能
double fopt=0;// 最优适应度

    /**
        * @brief 设置最优适应度
        *
        * @param f 最优适应度值
        */
// 设置最优适应度
void setFopt(double f){
   this->fopt = f;
}

/**
     * @brief 设置控制参数
     *
     * @param phi 控制参数
     */
// 设置控制参数
void setPhi(double phi){
   this->epsilon = phi;
}

    /**
        * @brief 选择层级大小
        *
        * 该函数基于层级的性能选择一个层级大小。层级大小的选择依据其在性能上的表现。
        *
        * @param a 各层级的性能数组
        * @return 选择的层级索引
        */
// 选择层级大小
int select_level_size(double *a)
{
   double total = 0;
   // 计算 a 数组每个元素的指数值之和，用于归一化处理，便于按性能选择层级
   for (int i = 0; i < rand_level_size; i++)
   {
       total += exp(7 * a[i]);
   }

   double *pro = new double[rand_level_size + 1];
   pro[0] = 0;
   // 计算累积概率数组 pro，pro[i+1] 表示第 i 个层级的累积概率
   for (int i = 0; i < rand_level_size; i++)
   {
       pro[i + 1] = pro[i] + exp(7 * a[i]) / total;
   }

   // 生成一个 [0, 1) 之间的随机数 tmp
   double tmp = rand() * 1.0 / RAND_MAX;
   int selected = -1;
   // 根据随机数 tmp 在累积概率数组 pro 中的位置，确定选中的层级
   for (int i = 0; i < rand_level_size; i++)
   {
       if (tmp <= pro[i + 1])
       {
           selected = i;
           break;
       }
   }

   // 错误处理，如果没有选中任何层级，则输出错误信息，并随机选择一个层级
   if (selected == -1)
   {
       cout << "select level size error" << endl;
       for (int i = 0; i <= rand_level_size; i++)
       {
           cout << pro[i] << " ";
       }
       cout << endl;
       for (int i = 0; i < rand_level_size; i++)
       {
           cout << a[i] << " ";
       }
       cout << endl;
       for (int i = 0; i < rand_level_size; i++)
       {
           cout << level_size_performance[i] << " ";
       }
       cout << endl;
       selected = rand() % rand_level_size;
       cout << "total:" << total << " bestFit:" << bestFit << endl;
   }
   // 释放内存
   delete[] pro;
   return selected;
}

    /**
      * @brief 初始化粒子群
      *
      * 根据种群大小设置随机层级集合和大小，并初始化粒子群。
      * 粒子群的初始化包括生成粒子的初始位置和速度，并对种群进行评估。
      */
// 初始化粒子群
void init()
{
   // 根据种群大小设置随机层级集合和大小
   if (swarmSize >= 300)
   {
       rand_level_size = 6;
       rand_level_set = new int[6]{4, 6, 8, 10, 20, 50};
   }
   else if(swarmSize >= 20)
   {
       rand_level_size = 4;
       rand_level_set = new int[4]{4, 6, 8, 10};
   }else{
       rand_level_size = 2;
       rand_level_set = new int[2]{2,3};
   }
   const char *load_env = getenv("MACPO_PAIR_INIT_LOAD");
   const char *dump_env = getenv("MACPO_PAIR_INIT_DUMP");
   int rank = macpo_mpi_rank_from_env();
   bool loaded = false;
   if (load_env && load_env[0])
   {
       char path[4096];
       snprintf(path, sizeof(path), "%s/rank_%d.bin", load_env, rank);
       FILE *fp = fopen(path, "rb");
       if (fp)
       {
           fseek(fp, 0, SEEK_END);
           long sz = ftell(fp);
           fseek(fp, 0, SEEK_SET);
           size_t expected = 4u + 4u * 4u + (size_t)swarmSize * (size_t)groupSize * sizeof(double);
           if (sz == (long)expected)
           {
               char magic[4];
               if (fread(magic, 1, 4, fp) == 4 && memcmp(magic, "MACP", 4) == 0)
               {
                   std::int32_t ver, ss, gs, dim;
                   if (fread(&ver, 4, 1, fp) == 1 && fread(&ss, 4, 1, fp) == 1
                       && fread(&gs, 4, 1, fp) == 1 && fread(&dim, 4, 1, fp) == 1
                       && ver == 1 && ss == swarmSize && gs == (std::int32_t)groupSize && dim == dimension)
                   {
                       double *zeros = new double[dimension]{0};
                       for (int p = 0; p < swarmSize; p++)
                       {
                           particle *newPar = new particle(zeros, dimension);
                           for (int i = 0; i < groupSize; ++i)
                           {
                               double v;
                               fread(&v, sizeof(double), 1, fp);
                               int index = groupDim[i];
                               newPar->X[index] = v;
                               newPar->v[index] = 0;
                           }
                           swarm.push_back(newPar);
                           swarm_ordered.push_back(newPar);
                       }
                       delete[] zeros;
                       loaded = true;
                   }
               }
           }
           fclose(fp);
       }
       if (!loaded && rank == 0)
           cout << "[MACPO_PAIR_INIT_LOAD] failed; using random init." << endl;
   }
   if (!loaded)
   {
       double *zeros = new double[dimension]{0};
       for (int p = 0; p < swarmSize; p++)
       {
           particle* newPar = new particle(zeros, dimension);
           for (int i = 0; i < groupSize; ++i)
           {
               int index = groupDim[i];
               newPar->X[index] = (rand() * 1.0 / RAND_MAX) * (maxX - minX) + minX;
               newPar->v[index] = 0;
           }
           swarm.push_back(newPar);// 将新粒子加入种群
           swarm_ordered.push_back(newPar);// 将新粒子加入有序种群
       }
       delete[] zeros;
   }
   Evaluator->total_evaluate(swarm);// 评估整个种群
   sort(swarm.begin(), swarm.end(),cmp_unit_pointer);// 根据适应度排序种群
   bestFit = swarm[0]->fitness;// 记录最佳适应度

   level_size_performance = new double[rand_level_size];// 初始化层级性能数组
   for (int i = 0; i < rand_level_size; i++)
       level_size_performance[i] = 1;

   bestParIndex = 0;// 初始化最佳个体索引

   if (dump_env && dump_env[0])
   {
       char path[4096];
       snprintf(path, sizeof(path), "%s/rank_%d.bin", dump_env, rank);
       FILE *fp = fopen(path, "wb");
       if (fp)
       {
           fwrite("MACP", 1, 4, fp);
           std::int32_t ver = 1;
           fwrite(&ver, 4, 1, fp);
           std::int32_t ss = (std::int32_t)swarmSize, gs = (std::int32_t)groupSize, dim = (std::int32_t)dimension;
           fwrite(&ss, 4, 1, fp);
           fwrite(&gs, 4, 1, fp);
           fwrite(&dim, 4, 1, fp);
           for (int p = 0; p < swarmSize; p++)
           {
               particle *par = (particle *)swarm[p];
               for (int i = 0; i < groupSize; ++i)
               {
                   int idx = groupDim[i];
                   double v = par->X[idx];
                   fwrite(&v, sizeof(double), 1, fp);
               }
           }
           fclose(fp);
       }
   }
}

    /**
        * @brief 获取最佳粒子的参数
        *
        * 该函数返回当前种群中适应度最好的粒子的参数。
        *
        * @return 最佳粒子的参数数组
        */
// 获取最佳粒子
double *getBestPar()
{
   double *res = new double[dimension];
   memcpy(res, swarm[0]->X, dimension * sizeof(double));// 复制最佳个体的位置
   return res;
}

/**
     * @brief 一次迭代更新
     *
     * 在不同层级上更新粒子的位置和速度，并根据粒子适应度进行评估。
     *
     * @param not_evaluate 是否评估种群，如果为 1，则跳过评估过程
     */
// 一次迭代更新
void generation(int &not_evaluate)
{
   bestFit = swarm[0]->fitness;// 获取当前最佳适应度
   // 选择当前使用的层级大小，根据层级表现情况选择最合适的层级数
   NL_index = select_level_size(level_size_performance);
   NL = rand_level_set[NL_index];// 使用选定的层级数设置层级大小
   LS = swarmSize / NL;// 层级粒子数
   // cout<<"NL="<<NL<<endl;

   // 遍历每个层级，从高层级向低层级逐层优化
   for (int level_index = NL - 1; level_index >= 1; level_index--)
   {
       int NUM = LS;// 当前层级的粒子数量
       // 若是最顶层（最高层级），需额外添加余数粒子，以确保所有粒子都在当前层级的某一层内
       if(level_index == NL-1){
           NUM += swarmSize%NL;
       }
       // cout<<"level_index: "<<level_index<<" "<<NUM<<endl;
       // 遍历当前层级的每个粒子，对当前层级的粒子进行优化
       for (int p_index = 0; p_index < NUM; p_index++)
       // for (int p_index = 0; p_index < LS; p_index++)
       {
           int p_cur = (level_index)*LS + p_index;// 当前粒子的索引
           // printf("level %d particle %d\n",level_index, p_cur);
           int p1, p2;// 存储选定的两个对比粒子的索引

           // 如果层级高于 1，则选择两个不同随机层级中的粒子
           if (level_index >= 2)
           {
               int rl1 = rand() % (level_index);// 随机选择第一个层级
               int rl2 = rand() % (level_index);// 随机选择第二个层级
               while (rl1 == rl2) // 确保选择的两个层级不同
               {
                   rl2 = rand() % (level_index);
               }
               if (rl1 > rl2)
               {
                   swap(rl1, rl2);// 保证层级索引 rl1 小于 rl2
               }
               //对于level rl1, 元素的index在 [ LS*(rl1-1），LS*rl1-1]
               p1 = rand() % LS + LS * rl1;// 在第一个层级中选择一个粒子
               p2 = rand() % LS + LS * rl2;// 在第二个层级中选择一个粒子
           }
           else if (level_index == 1)// 若是底层（层级数为 1），直接在当前层中随机选择两个粒子
           {
               p1 = rand() % LS;// 在L1层级中选择一个粒子
               p2 = rand() % LS;// 在L1层级中选择另一个粒子
               while (p1 == p2)// 确保选择的两个粒子不同
               {
                   p2 = rand() % LS;
               }

               if (swarm[p2]->fitness < swarm[p1]->fitness)
               {
                   swap(p1, p2);// 确保 p1 的适应度大于 p2
               }
           }
           // cout<<p1<<" "<<p2<<" ";
           // printf("particle %d fitness %f\n", p_cur, swarm[p_cur]->fitness);
           // particle* newPar = new particle(swarm[p_cur]->X, dimension);
           // 对于粒子 p_cur 的每个维度，更新其位置和速度
           //groupSize 是该粒子群的维度大小（也就是每个粒子的维度数）groupDim 是维度的索引数组
           // index 表示当前维度的索引，确保每次更新一个维度的数据
           for (int d = 0; d < groupSize; d++)
           {
               double r1 = rand() * 1.0 / RAND_MAX; // 随机因子 r1
               double r2 = rand() * 1.0 / RAND_MAX; // 随机因子 r2
               double r3 = rand() * 1.0 / RAND_MAX; // 随机因子 r3
               int index = groupDim[d];             // 获取当前维度索引
               // r1=0.5;r2=0.5;r3=0.5;
               // 计算更新向量，公式基于 p_cur 的速度以及两个对比粒子位置的差异
               //vertical 表示当前粒子沿该维度的速度更新量，这个值通过自身的速度、与 p1 和 p2 的距离加权得到
               //epsilon 是控制因子，用来调整对 p2 距离的影响权重
               double vertical = r1 * ((particle *)swarm[p_cur])->v[index]
                               + r2 * (swarm[p1]->X[index] - swarm[p_cur]->X[index])
                               + r3 * epsilon * (swarm[p2]->X[index] - swarm[p_cur]->X[index]);
               // newPar->X[index] = swarm[p_cur]->X[index] + vertical;
               // newPar->v[index] = vertical;
               // 更新粒子位置和速度
               swarm[p_cur]->X[index] = swarm[p_cur]->X[index] + vertical;
               ((particle *)swarm[p_cur])->v[index] = vertical;

               // 边界检查 限制粒子的位置在允许范围内 [minX, maxX]
               if (swarm[p_cur]->X[index] > maxX)
               {
                   swarm[p_cur]->X[index] = maxX;
               }
               if (swarm[p_cur]->X[index] < minX)
               {
                   swarm[p_cur]->X[index] = minX;
               }
           }
           // newPar->fitness = Evaluator->evaluate(newPar->X);
           // if (newPar->fitness < swarm[p_cur]->fitness)
           // {
           //     success++;
           // }

           // if (newPar->fitness < swarm[p_cur]->fitness)
           // {
           //     // cout<<"success\n";
           //     delete (particle *)swarm[p_cur];
           //     swarm[p_cur] = newPar;
           //     success++;
           // }
           // else
           // {
           //     // cout<<"fail\n";
           //     delete newPar;
           // }

           // delete (particle *)swarm[p_cur];
           // swarm[p_cur] = newPar;
       }
   }


   // 如果 not_evaluate 不为 1，则对更新后的粒子群进行评估和排序
   if(not_evaluate != 1){
       Evaluator->total_evaluate(swarm);// 评估整个种群
       sort(swarm.begin(), swarm.end(),cmp_unit_pointer);// 按适应度排序粒子
   }
   if (bestFit == 0)
   {
       cout << "bestFit:" << bestFit << " " << swarm[0]->fitness << endl;

       for (int i = 0; i < dimension; i++)
       {
           cout << swarm[0]->X[i] << "  ";
       }
       cout << endl
            << endl;
   }
   else// 更新当前层级的表现值，以适应新一代的优化情况
   {
       // cout << "bestFit:" << bestFit  << endl;
       if(bestFit>swarm[0]->fitness)// 若找到更优的适应度
           // 更新当前层级表现
           level_size_performance[NL_index] = (bestFit - swarm[0]->fitness) /
                   (bestFit-fopt);
       else{
           // cout<<"no progress\n";
           level_size_performance[NL_index] = 0; // 若未取得进展，将当前层级表现置为 0
       }
       bestFit = swarm[0]->fitness;// 更新最佳适应度
   }
}
};



#endif