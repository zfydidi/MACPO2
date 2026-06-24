#ifndef SHARING_H
#define SHARING_H

#include "../Benchmarks/Benchmarks.h"
#include "./optimizer.h"
/*
    TODO: 协商后的共享阶段，不同的文章提出了不同的方法，但这一部分和optimizer有一定的耦合性，这一部分需要的是整个种群的solution，以及一个全局最优的solution。但是呢，种群的solution储存在不同演化算法内置的particle下，不太能抽离开。我唯一想到的方法是把particle 下的solution的指针取出来另存，然后传给sharing组件。但这样稍显丑陋。也是没有办法的办法了。
    REQUIRE: pFunc, competition(因为实际上这里也有一个协商的过程，面对全体个体的)
    INPUT: 一个种群的所有solution、一个全局最优解
    OUTPUT: 无（修改直接在指针上修改了）

*/

/**
 * @brief 日志工具函数，用于打印数组内容
 * @param x 指向数组的指针
 */
void log(double* x){
    for(int i=0;i<1000;i++){// 遍历数组 x 的前 1000 个元素
        cout<<x[i]<<" ";// 打印元素值
    }
    cout<<endl;// 打印换行符
}

/**
 * @brief 基类：定义共享机制的接口
 */
// 基础共享类，定义共享机制的接口
class sharing{
public:
    Benchmarks *pFunc;///< 用于存储基准测试函数的指针

    /**
        * @brief 构造函数
        * @param pFunc 基准测试函数对象指针
     */
    // 构造函数
    sharing(Benchmarks *pFunc)
    {
        this->pFunc = pFunc;// 初始化 pFunc 成员变量
    }

    /** @brief 虚析构函数，确保正确的多态删除。 */
    virtual ~sharing() = default;

    /**
   * @brief 虚函数：共享方法
   * @param swarm 群体个体的集合
   * @param swarmSize 群体大小
   * @param globalBest 全局最优解数组
   * @param groupIndex 当前群体索引
   * @param 参数5(int) 预留参数，具体功能待定义
   * @param 参数6(int) 预留参数，具体功能待定义
   */
    // 共享方法的纯虚拟函数，定义了接口，供子类实现
    virtual void share(vector<unit*> &swarm, int swarmSize, double *globalBest, int groupIndex,int,int&)=0;
};

/**
 * @brief 子类：实现变量共享机制
 */
// 变量共享类，继承自`sharing`，用于实现基于变量的共享机制
class sharing_variable_wise:public sharing{
public:
    int* variable_switch;///< 指向整数数组的指针，变量开关，用于控制各个变量是否参与共享

    /**
     * @brief 构造函数
     * @param pFunc 基准测试函数对象指针
     * @param variable_switch 变量开关数组，默认为 nullptr
     */
    // 构造函数，初始化共享机制
    sharing_variable_wise(Benchmarks* pFunc,int* variable_switch=nullptr):sharing(pFunc){
        this->variable_switch=variable_switch;//设置变量开关 }
    }

    /**
   * @brief 实现共享方法
   * @param swarm 群体个体的集合
   * @param swarmSize 群体大小
   * @param globalBest 全局最优解数组
   * @param groupIndex 当前群体索引
   * @param 参数5 预留参数，具体功能待定义
   * @param 参数6 预留参数，具体功能待定义
   */
    // 实现共享方法
    void share(vector<unit*> &swarm, int swarmSize, double *globalBest, int groupIndex,int,int&){
        // 我这里就不去复制其他维度的值了，应该是用不上的。复制重叠域就够了。
        vector<int> overlap_groups = pFunc->getOverlapGroup(groupIndex); // 获取当前群体的重叠群体

        // 遍历重叠群体
        for (int g : overlap_groups)
        {
            vector<int> overlap = pFunc->getOverlapDim(groupIndex, g);// 获取重叠群体的重叠维度
            // 遍历每个重叠维度
            for(int d : overlap){
                // 如果变量开关存在且当前变量开关关闭，跳过当前维度
                if(variable_switch!=nullptr && variable_switch[d] == 0)
                    continue;
                // 共享全局最优解在重叠维度的值
                for(int i=0;i<swarmSize;i++){
                    swarm[i]->X[d] = globalBest[d]; // 将每个个体的当前重叠维度值更新为全局最优解的对应值
                }
            }
        }
    }
};


#endif