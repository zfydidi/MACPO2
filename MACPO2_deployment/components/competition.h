#ifndef COMPETITION_H
#define COMPETITION_H

#include <vector>
#include <algorithm>
#include <fstream>
#include "../Benchmarks/Benchmarks.h"
#include "./struct.h"

using std::vector;
using std::find;
using std::min;
using std::fstream;
using std::ios;
using std::endl;

/**
 * @class competition
 * @brief 基础竞争类，定义竞争方法接口。
 */
class competition{
public:    
    Benchmarks* pFunc;
    string log_path;

    competition(Benchmarks* pFunc){
        this->pFunc = pFunc;        
    }
    
    /** @brief 虚析构函数，确保正确的多态删除。 */
    virtual ~competition() = default;
    
    void set_path(string path){
        log_path = path;
    }
    
    virtual double* compete(int hostID,int neighborID, double* host, double* neighbor, bool &success,double& v1, double& v2) = 0;
};

/**
 * @class competition_variable_wise
 * @brief 变量级竞争基类，提供变量级竞争机制。
 */
class competition_variable_wise: public competition{
public:
    int* compete_result;
    using competition::competition;
};

/**
 * @class competition_variable_independent_2
 * @brief 变量独立的竞争实现类，继承自 `competition_variable_wise`。
 */
class competition_variable_independent_2: public competition_variable_wise{
public:
    int* variable_switch;
    vector<unit*> *swarm;

    competition_variable_independent_2(Benchmarks* pFunc,vector<unit*> *swarm,int* variable_switch=nullptr):
    competition_variable_wise(pFunc){
        this->variable_switch = variable_switch;
        this->swarm = swarm;
        compete_result = new int[pFunc->getDimension()]{0};
    }

    double* compete(int hostID,int neighborID, double* host, double* neighbor, bool &success,double& v1, double& v2){
        vector<int> neighbor_dim = pFunc->getGroupDim(neighborID);
        vector<int> overlap = pFunc->getOverlapDim(hostID,neighborID);

        double* gb = new double[pFunc->getDimension()];
        memcpy(gb,host,pFunc->getDimension()*sizeof(double));

        // 更新非重叠维度的变量值
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

        // 初始适应值计算
        double fitness = pFunc->local_eva(gb,hostID)+pFunc->local_eva(gb,neighborID);

        // 遍历重叠维度，评估变量竞争结果
        for(int d:overlap){
            double origin_val = gb[d];
            gb[d] = (hostID<neighborID) ? neighbor[d]:host[d];

            double newFit = pFunc->local_eva(gb,hostID)+pFunc->local_eva(gb,neighborID);
            gb[d] = origin_val;

            compete_result[d] = ((newFit > fitness) + (hostID < neighborID))%2;
        }

        // 应用竞争结果，选择最终解
        for(int d:overlap){
            if(compete_result[d]==1)
                gb[d] = neighbor[d];
        }

        // 计算适应值
        double fit1 = pFunc->local_eva(gb,hostID);
        double fit2 = pFunc->local_eva(gb,neighborID);

        // 简化的冲突检测
        if(variable_switch != nullptr){
            for(int d:overlap){
                double dt = 0.1;

                if(gb[d]+dt>=pFunc->getMaxX())
                    dt = pFunc->getMaxX() - gb[d];
                if(gb[d]-dt<=pFunc->getMinX())
                    dt = gb[d] - pFunc->getMinX();

                double f1p, f1n, f2p, f2n;
                double ov = gb[d];
                
                gb[d] = std::min(ov + dt, pFunc->getMaxX());
                f1p = pFunc->local_eva(gb,hostID);
                f2p = pFunc->local_eva(gb,neighborID);
                
                gb[d] = std::max(ov - dt, pFunc->getMinX());
                f1n = pFunc->local_eva(gb,hostID);
                f2n = pFunc->local_eva(gb,neighborID);

                gb[d] = ov;
                
                double grad1 = (f1p - f1n) / (2.0 * dt);
                double grad2 = (f2p - f2n) / (2.0 * dt);
                
                double grad1_norm = std::abs(grad1) + 1e-10;
                double grad2_norm = std::abs(grad2) + 1e-10;
                double cos_sim = (grad1 * grad2) / (grad1_norm * grad2_norm);
                
                if (cos_sim > 0.7) {
                    variable_switch[d] = 0;
                } else {
                    variable_switch[d] = compete_result[d];
                }
            }
        }

        v1 = 0.0;
        return gb;
    }
};

#endif 