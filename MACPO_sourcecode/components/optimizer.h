#ifndef OPTIMIZER_H
#define OPTIMIZER_H

#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <algorithm>
#include <iostream>
#include <random>
#include <vector>
#include <stdint.h>
#include <Eigen/Dense>

#include "../Benchmarks/Benchmarks.h"
#include "./evaluator.h"
#include "./struct.h"

using std::cout;
using std::sort;
using Eigen::MatrixXd;
using Eigen::Matrix;
using Eigen::VectorXd;
using namespace Eigen;

/** MPI rank for paired init files (OpenMPI / PMI). */
static inline int macpo_mpi_rank_from_env(void)
{
    const char *e = getenv("OMPI_COMM_WORLD_RANK");
    if (e) return atoi(e);
    e = getenv("PMI_RANK");
    if (e) return atoi(e);
    return 0;
}

void swap(int &a, int &b)
{
    int temp = a;
    a = b;
    b = temp;
}

class optimizer
{
public:
    int swarmSize, bestParIndex;
    evaluator *Evaluator;
    int dimension, minX, maxX, groupSize;
    vector<int> groupDim;
    vector<unit*> swarm;
    vector<unit*> swarm_ordered;

    optimizer(int swarmSize, evaluator *Evaluator, vector<int> groupDim)
    {
        this->swarmSize = swarmSize;
        this->Evaluator = Evaluator;
        this->dimension = Evaluator->pFunc->getDimension();
        this->minX = Evaluator->pFunc->getMinX();
        this->maxX = Evaluator->pFunc->getMaxX();
        this->groupDim = groupDim;
        this->groupSize = groupDim.size();
    }

    virtual void init() = 0;

    virtual void generation(int &) = 0;

    virtual double *getBestPar() = 0;

    void resort(){
        Evaluator->total_evaluate(swarm);
        sort(swarm.begin(), swarm.end(),cmp_unit_pointer);
    }

    void setGroup(vector<int> groupDim){
        this->groupDim=groupDim;
        this->groupSize = groupDim.size();
    }
};
bool cmp_3d(double* a, double* b){
    double range = 0;
    if(fabs(a[0]-b[0]) > range)
        return a[0] < b[0];
    if(fabs(a[1] - b[1]) > range)
        return a[1] < b[1];
    return a[2]<b[2];
}
bool cmp_2d(double* a, double* b){
    double range = 5;
    if(fabs(a[0]-b[0]) > range)
        return a[0] < b[0];
    return a[1]<b[1];
}
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

        std::random_shuffle(arr,arr+swarmSize);// 随机打乱种群顺序
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

class optimizer_LLSO : public optimizer
{
public:
    using optimizer::optimizer;

    //优化器基础参数
    int NL, LS, NL_index=0;
    double epsilon = 0.5;
    double bestFit;
    int *rand_level_set; //the pool of the number of levels
    int rand_level_size;
    double *level_size_performance;
    double fopt=0;

    void setFopt(double f){
        this->fopt = f;
    }

    void setPhi(double phi){
        this->epsilon = phi;
    }

    int select_level_size(double *a)
    {
        double total = 0;
        for (int i = 0; i < rand_level_size; i++)
        {
            total += exp(7 * a[i]);
        }
        double *pro = new double[rand_level_size + 1];
        pro[0] = 0;
        for (int i = 0; i < rand_level_size; i++)
        {
            pro[i + 1] = pro[i] + exp(7 * a[i]) / total;
        }
        double tmp = rand() * 1.0 / RAND_MAX;
        int selected = -1;
        for (int i = 0; i < rand_level_size; i++)
        {
            if (tmp <= pro[i + 1])
            {
                selected = i;
                break;
            }
        }
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
        delete[] pro;
        return selected;
    }

    void init()
    {
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
                        int32_t ver, ss, gs, dim;
                        if (fread(&ver, 4, 1, fp) == 1 && fread(&ss, 4, 1, fp) == 1
                            && fread(&gs, 4, 1, fp) == 1 && fread(&dim, 4, 1, fp) == 1
                            && ver == 1 && ss == swarmSize && gs == (int32_t)groupSize && dim == dimension)
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
                swarm.push_back(newPar);
                swarm_ordered.push_back(newPar);
            }
            delete[] zeros;
        }
        Evaluator->total_evaluate(swarm);
        sort(swarm.begin(), swarm.end(),cmp_unit_pointer);
        bestFit = swarm[0]->fitness;

        level_size_performance = new double[rand_level_size];
        for (int i = 0; i < rand_level_size; i++)
            level_size_performance[i] = 1;
        
        bestParIndex = 0;

        if (dump_env && dump_env[0])
        {
            char path[4096];
            snprintf(path, sizeof(path), "%s/rank_%d.bin", dump_env, rank);
            FILE *fp = fopen(path, "wb");
            if (fp)
            {
                fwrite("MACP", 1, 4, fp);
                int32_t ver = 1;
                fwrite(&ver, 4, 1, fp);
                int32_t ss = (int32_t)swarmSize, gs = (int32_t)groupSize, dim = (int32_t)dimension;
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

    double *getBestPar()
    {
        double *res = new double[dimension];
        memcpy(res, swarm[0]->X, dimension * sizeof(double));
        return res;
    }

    void generation(int &not_evaluate)
    {
        bestFit = swarm[0]->fitness;
        NL_index = select_level_size(level_size_performance);
        NL = rand_level_set[NL_index];
        LS = swarmSize / NL;
        // cout<<"NL="<<NL<<endl;
        for (int level_index = NL - 1; level_index >= 1; level_index--)
        {
            int NUM = LS;
            if(level_index == NL-1){
                NUM += swarmSize%NL;
            }
            // cout<<"level_index: "<<level_index<<" "<<NUM<<endl;
            for (int p_index = 0; p_index < NUM; p_index++)
            // for (int p_index = 0; p_index < LS; p_index++)
            {
                int p_cur = (level_index)*LS + p_index;
                // printf("level %d particle %d\n",level_index, p_cur);
                int p1, p2;

                if (level_index >= 2)
                {
                    int rl1 = rand() % (level_index);
                    int rl2 = rand() % (level_index);
                    while (rl1 == rl2)
                    {
                        rl2 = rand() % (level_index);
                    }
                    if (rl1 > rl2)
                    {
                        swap(rl1, rl2);
                    }
                    //对于level rl1, 元素的index在 [ LS*(rl1-1），LS*rl1-1]
                    p1 = rand() % LS + LS * rl1;
                    p2 = rand() % LS + LS * rl2;
                }
                else if (level_index == 1)
                {
                    p1 = rand() % LS;
                    p2 = rand() % LS;
                    while (p1 == p2)
                    {
                        p2 = rand() % LS;
                    }

                    if (swarm[p2]->fitness < swarm[p1]->fitness)
                    {
                        swap(p1, p2);
                    }
                }
                // cout<<p1<<" "<<p2<<" ";
                // printf("particle %d fitness %f\n", p_cur, swarm[p_cur]->fitness);
                // particle* newPar = new particle(swarm[p_cur]->X, dimension);
                for (int d = 0; d < groupSize; d++)
                {
                    double r1 = rand() * 1.0 / RAND_MAX;
                    double r2 = rand() * 1.0 / RAND_MAX;
                    double r3 = rand() * 1.0 / RAND_MAX;
                    int index = groupDim[d];
                    // r1=0.5;r2=0.5;r3=0.5;
                    double vertical = r1 * ((particle *)swarm[p_cur])->v[index] + r2 * (swarm[p1]->X[index] - swarm[p_cur]->X[index]) + r3 * epsilon * (swarm[p2]->X[index] - swarm[p_cur]->X[index]);
                    // newPar->X[index] = swarm[p_cur]->X[index] + vertical;
                    // newPar->v[index] = vertical;
                    swarm[p_cur]->X[index] = swarm[p_cur]->X[index] + vertical;
                    ((particle *)swarm[p_cur])->v[index] = vertical;

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
        
        if(not_evaluate != 1){
            Evaluator->total_evaluate(swarm);
            sort(swarm.begin(), swarm.end(),cmp_unit_pointer);
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
        else
        {
            // cout << "bestFit:" << bestFit  << endl;
            if(bestFit>swarm[0]->fitness)
                level_size_performance[NL_index] = (bestFit - swarm[0]->fitness) / (bestFit-fopt);
            else{
                // cout<<"no progress\n";
                level_size_performance[NL_index] = 0;
            }
            bestFit = swarm[0]->fitness;
        }
    }
};



#endif