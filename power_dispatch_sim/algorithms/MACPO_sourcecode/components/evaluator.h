#ifndef EVALUATOR_H
#define EVALUATOR_H

#include "../Benchmarks/Benchmarks.h"
#include "./struct.h"
#include <iostream>
#include <Eigen/Dense>
using std::vector;
using std::cout;
using std::endl;
using Eigen::VectorXd;

//evaluator
class evaluator {
public:
    Benchmarks* pFunc;
    int computing_cost;
    virtual double evaluate(double*) = 0;
    virtual double evaluate(VectorXd){
        return 0;
    }
    virtual void total_evaluate(vector<unit*>& swarm){
        for(unsigned int i=0;i<swarm.size();i++){
            swarm[i]->fitness = evaluate(swarm[i]->X);
        }
    }
};

class evaluator_global : public evaluator {
public:
    evaluator_global(Benchmarks* pFunc)
    {
        this->computing_cost=pFunc->getGroupNum();
        this->pFunc = pFunc;
    }
    double evaluate(double* v)
    {
        return pFunc->global_eva(v);
    }
    double evaluate(VectorXd v){
        double *arr = v.data();
        double res = pFunc->global_eva(arr);
        return res;
    }
};

class evaluator_local : public evaluator {
public:
    int groupIndex;
    evaluator_local(Benchmarks* pFunc, int index)
    {
        this->pFunc = pFunc;
        this->groupIndex = index;
        computing_cost = 1;
    }
    double evaluate(double* v)
    {
        return pFunc->local_eva(v, groupIndex);
    }
    double evaluate(VectorXd v){
        double *arr = v.data();
        double res = pFunc->local_eva(arr, groupIndex);
        return res;
    }
};


class evaluator_biasing_local_penalty : public evaluator {
public:
    int groupIndex, overlapSize,dimension;
    double alpha;
    vector<int> overlapDim;
    double *globalBest;
    vector<int> whichGroup;
    int* penaltySwitch;

    evaluator_biasing_local_penalty(Benchmarks* pFunc, int groupIndex, double alpha, double* gb)
    {
        this->pFunc = pFunc;
        this->groupIndex = groupIndex;
        this->alpha = alpha;
        this->computing_cost=1;
        this->dimension = pFunc->getDimension();
        this->globalBest = new double[dimension];
        memcpy(this->globalBest,gb,dimension*sizeof(double));
        vector<int> groupDim = pFunc->getGroupDim(groupIndex);

        vector<int> overlap_groups = pFunc->getOverlapGroup(groupIndex);
        overlapSize = 0;
        for(int i:overlap_groups){
            vector<int> overlap = pFunc->getOverlapDim(groupIndex,i);
            overlapSize += overlap.size();
            overlapDim.insert(overlapDim.end(),overlap.begin(),overlap.end());
            for(unsigned int j=0;j<overlap.size();j++)
                whichGroup.push_back(i);
        }

        penaltySwitch = new int[pFunc->getGroupNum()]{0};
    }

    void setAlpha(double alpha)
    {
        this->alpha = alpha;
    }

    void setGlobalBest(double* gb){
        memcpy(this->globalBest,gb,dimension*sizeof(double));
    }

    double evaluate(double* X)
    {
        double res = 0;
        res += pFunc->local_eva(X, groupIndex);
        for (int i = 0; i < overlapSize; ++i) {
            int index = overlapDim[i];
            // cout<<alpha<<" "<<penaltySwitch[1]<<" "<<whichGroup[i]<<" "<<penaltySwitch[whichGroup[i]]<<endl;
            res+=alpha * fabs(X[index] - globalBest[index]) * penaltySwitch[whichGroup[i]];
        }

        return res;
    }

    double getDis(double* X){
        double dis = 0;
        for (int i = 0; i < overlapSize; ++i) {
            int index = overlapDim[i];
            dis += fabs(X[index] - globalBest[index]);
        }

        return dis;        
    }
};

class evaluator_variable_wise_penalty:public evaluator_biasing_local_penalty{
public:
    int* variable_switch;
    // using evaluator_biasing_local_penalty::evaluator_biasing_local_penalty;
    evaluator_variable_wise_penalty(Benchmarks* pFunc, int groupIndex, double alpha, double* gb):
    evaluator_biasing_local_penalty(pFunc, groupIndex, alpha, gb){
        variable_switch = new int[pFunc->getDimension()]{0};
    }
    double evaluate(double* X)
    {
        double res = 0;
        res += pFunc->local_eva(X, groupIndex);
        for (int i = 0; i < overlapSize; ++i) {
            int index = overlapDim[i];
            res+=alpha * fabs(X[index] - globalBest[index]) * variable_switch[index];
        }

        return res;
    }
};


#endif