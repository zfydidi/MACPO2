#ifndef COMPETITION_H
#define COMPETITION_H

/*
    TODO: 为重叠域candidate solution 选取一个最优解
    REQUIRE: 评估器、分组维度及重叠情况
    INPUT: 每个 agent的最优solution
    OUTPUT: 一个全局 solution 
    COMMNENT: 把这个类抽离出来是因为我觉得这个可以测试多种方法，目前已知的有FEA的，正交实验，随机正交实验，以及我的。但是要让这几种方法的调用方式完全一样还不是一件简单的事情，例如，随机正交实验是在CC中应用的，输入是全局的各个组的情况。但我的这个方法是用在MA的，输入是两个组的情况。所以还不太一样。我下一个断言：在两个组之间的协商中，我的这个方法会比正交实验好，并且胜率会很高。这个后续做个实验来证明。但是我这个只适用于两两协商，正交实验可能会考虑到当一个变量被三个或以上的组共享式的竞争情形。所以或许这个值得说道说道。
    综上，目前打算在这个文件中写两种，我的方法和正交实验，我的还没有起名字。
    目前打算先写两个组之间的协商，甚至可以只写成一个函数，不过呢，只写一个函数的话不好做多态。
    
    我目前是在函数内部去获取维度情况，因为g1,g2不是固定的，但是考虑到sharing中也会去调用这个类，反复获取维度情况可能过于低效。
*/
#include <vector>
#include <algorithm>
#include <fstream>
// #include <iostream>

#include "../Benchmarks/Benchmarks.h"
using std::vector;
using std::find;
using std::min;
using std::fstream;
using std::ios;
using std::endl;

class competition{
public:    
    Benchmarks* pFunc;
    string log_path;
    competition(Benchmarks* pFunc){
        this->pFunc = pFunc;        
    }
    void set_path(string path){
        log_path = path;
    }
    virtual double* compete(int hostID,int neighborID, double* host, double* neighbor, bool &success,double& v1, double& v2) = 0;
};

class competition_variable_wise: public competition{
public:
    int* compete_result;
    using competition::competition;
};


class competition_variable_independent_2: public competition_variable_wise{
public:
    int* variable_switch;
    vector<unit*> *swarm;
    competition_variable_independent_2(Benchmarks* pFunc,vector<unit*> *swarm,int* variable_switch=nullptr):competition_variable_wise(pFunc){
        this->variable_switch = variable_switch;
        this->swarm = swarm;
        compete_result = new int[pFunc->getDimension()]{0};
    }
    double* compete(int hostID,int neighborID, double* host, double* neighbor, bool &success,double& v1, double& v2){
        vector<int> neighbor_dim = pFunc->getGroupDim(neighborID);
        vector<int> overlap = pFunc->getOverlapDim(hostID,neighborID);
        double* gb = new double[pFunc->getDimension()];
        memcpy(gb,host,pFunc->getDimension()*sizeof(double));

        if(hostID<neighborID){
            for(int d:neighbor_dim){
                if(find(overlap.begin(),overlap.end(),d)==overlap.end()){
                    gb[d] = neighbor[d];
                }
            }
        }else{
            for(int d:neighbor_dim){
                gb[d] = neighbor[d];                
            }
        }

        double fitness = pFunc->local_eva(gb,hostID)+pFunc->local_eva(gb,neighborID);
        for(int d:overlap){
            double origin_val = gb[d];
            gb[d] = (hostID<neighborID)?neighbor[d]:host[d];

            double newFit = pFunc->local_eva(gb,hostID)+pFunc->local_eva(gb,neighborID);
            gb[d] = origin_val;

            compete_result[d] = ((newFit>fitness) + (hostID<neighborID))%2;
        }

        for(int d:overlap){
            if(compete_result[d]==1)
                gb[d] = neighbor[d];
        }

        
        double fit1 = pFunc->local_eva(gb,hostID);
        double fit2 = pFunc->local_eva(gb,neighborID);
        double gradient_inner_product=0,host_gradient_sum=0,neighbor_gradient_sum=0;
        for(int d:overlap){
            // 计算该维度上的种群平均速度，此处就只计算当前节点的速度，因为分布式环境下访问不到其他节点的速度
            // double sum=0;
            // for(unsigned int i=0;i<swarm->size();i++){                
            //     sum += fabs(((particle*)((*swarm)[i]))->v[d]);
            // }
            // double dt = sum/swarm->size();
            // 不同节点的dt是不一样的。。。这。。。
            double dt = 0.1;
            // cout<<dt<<" ";
            // 正负扰动求值，取下降的那个方向作为梯度
            if(gb[d]+dt>=pFunc->getMaxX())
                dt = pFunc->getMaxX() - gb[d];
            if(gb[d]-dt<=pFunc->getMinX())
                dt = gb[d] - pFunc->getMinX();
            double f1p,f1n,f2p,f2n;
            gb[d] += dt;
            f1p = pFunc->local_eva(gb,hostID);
            f2p = pFunc->local_eva(gb,neighborID);
            gb[d] -= 2*dt;
            f1n = pFunc->local_eva(gb,hostID);
            f2n = pFunc->local_eva(gb,neighborID);
            gb[d] += dt;
            

            if( (f1p-fit1)*(f2p-fit2) > 0 && (f1n-fit1)*(f2n-fit2)>0){
                variable_switch[d] = 0;
            }else{
                variable_switch[d] = compete_result[d];
            }

            gradient_inner_product+=(f1p-fit1)*(f2p-fit2);
            host_gradient_sum+=(f1p-fit1)*(f1p-fit1);
            neighbor_gradient_sum+=(f2p-fit2)*(f2p-fit2);
        }

        gradient_inner_product /= sqrt(host_gradient_sum*neighbor_gradient_sum);
        v1=gradient_inner_product;

        return gb;
    }
};

#endif