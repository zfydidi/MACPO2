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

void log(double* x){
    for(int i=0;i<1000;i++){
        cout<<x[i]<<" ";
    }
    cout<<endl;
}

class sharing{
public:
    Benchmarks *pFunc;
    sharing(Benchmarks *pFunc)
    {
        this->pFunc = pFunc;
    }
    virtual void share(vector<unit*> &swarm, int swarmSize, double *globalBest, int groupIndex,int,int&)=0;
};


class sharing_variable_wise:public sharing{
public:
    int* variable_switch;
    sharing_variable_wise(Benchmarks* pFunc,int* variable_switch=nullptr):sharing(pFunc){
        this->variable_switch=variable_switch;
    }
    void share(vector<unit*> &swarm, int swarmSize, double *globalBest, int groupIndex,int,int&){
        // 我这里就不去复制其他维度的值了，应该是用不上的。复制重叠域就够了。
        vector<int> overlap_groups = pFunc->getOverlapGroup(groupIndex);
        for (int g : overlap_groups)
        {
            vector<int> overlap = pFunc->getOverlapDim(groupIndex, g);
            for(int d : overlap){
                if(variable_switch!=nullptr && variable_switch[d] == 0)
                    continue;
                
                for(int i=0;i<swarmSize;i++){
                    swarm[i]->X[d] = globalBest[d];
                }
            }
        }
    }
};


#endif