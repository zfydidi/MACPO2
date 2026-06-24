
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

#include <ctime>
#include <iomanip>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <vector>
#include <unistd.h>
#include <mpi.h>

#include "./Benchmarks/Benchmarks.h"
#include "./components/optimizer.h"
#include "./components/evaluator.h"
#include "./components/competition.h"
#include "./components/sharing.h"
using namespace std;

long getCurrentTime()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

double global_average(double value, vector<int> neighbor_id);
int main(int argc, char* argv[])
{    
    std::time_t t2 = std::time(nullptr);
    // MPI初始化
    int myrank, nprocs, name;
    char proc_name[MPI_MAX_PROCESSOR_NAME];

    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Get_processor_name(proc_name, &name);
    MPI_Status stat;

    double distrub = 0.1; // according to Sec. III-D, distrub = theta(b-a) = 0.05% * 200 = 0.1
    
    double gen_per_d = 0.4; // See Sec. IV-A
    int eva_per_d = 3000; // See Sec. IV-D
    string funcID = argv[1];
    string exID = (argc >= 3) ? argv[2] : "ex01";
    string optimizer_type = (argc >= 4) ? argv[3] : "LLSO";
    string method = "MACPO";
    string outDir = (argc >= 5) ? string(argv[4]) : "./output/";
    if (!outDir.empty() && outDir.back() != '/') outDir += "/";

    string filename = outDir + funcID + "_" + optimizer_type + "_" + exID + ".txt";
    
    double penalty_weight = 0;
    double dynamic_weight = 512;
    int swarm_size = 300;

    // 随机种子：配对实验设 MACPO_PAIR_SEED，使 DUMP/LOAD 两次运行中 LLSO 的 rand() 序列一致
    {
        const char* pair_seed = getenv("MACPO_PAIR_SEED");
        if (pair_seed != nullptr && pair_seed[0] != '\0') {
            unsigned long sd = strtoul(pair_seed, nullptr, 10);
            srand((unsigned)(sd & 0xffffffffu));
            if (myrank == 0) {
                cout << "[MACPO] MACPO_PAIR_SEED=" << sd << " (paired trace RNG)" << endl;
            }
        } else {
            srand(getCurrentTime());
        }
    }
    
    // 写入表头
    if (myrank == 0) {
        ofstream outfile(filename);
        if (outfile.is_open()) {
            outfile << "# Algorithm: " << optimizer_type << endl;
            outfile << "# Version: baseline" << endl;
            outfile << setw(4) << "iter" 
                   << setw(12) << "eval" 
                   << setw(12) << "f_penalty" 
                   << setw(12) << "f_pure" 
                   << setw(12) << "penalty"
                   << setw(12) << "improvement" 
                   << setw(12) << "reward" 
                   << setw(12) << "conflict" 
                   << setw(12) << "weight" << endl;
            outfile.close();
        }
    }

    Benchmarks *pFunc= new Benchmarks(funcID,0,true);
    int dimension = pFunc->getDimension();
    vector<int> groupDim = pFunc->getGroupDim(myrank);
    pFunc->max_eva_times = eva_per_d*groupDim.size();
    //演化参数
    int gen_times = groupDim.size()*gen_per_d;

    double *globalBest = new double[dimension];
    memset(globalBest, 0, sizeof(double) * dimension);
    //组件注册
    evaluator *Evaluator = new evaluator_variable_wise_penalty(pFunc, myrank, penalty_weight, globalBest);
    optimizer *Optimizer = nullptr;
    if (optimizer_type == "CSO") {
        Optimizer = new optimizer_CSO(swarm_size, Evaluator, groupDim);
    } else {
        Optimizer = new optimizer_LLSO(swarm_size, Evaluator, groupDim);
    }
    competition *Competition = new competition_variable_independent_2(pFunc,&(Optimizer->swarm),((evaluator_variable_wise_penalty*)Evaluator)->variable_switch);
    sharing *Sharing =  new sharing_variable_wise(pFunc,((competition_variable_wise*)Competition)->compete_result);

    Optimizer->init();
    
    vector<int> overlapDim;    
    vector<vector<int>> overlapDimForEach;
    vector<int> overlap_groups = pFunc->getOverlapGroup(myrank);
    for(int i:overlap_groups){
        vector<int> overlap = pFunc->getOverlapDim(myrank,i);
        overlapDim.insert(overlapDim.end(),overlap.begin(),overlap.end());
        overlapDimForEach.push_back(overlap);
    }
    vector<int> commu_object= pFunc->getOverlapGroup(myrank);

    int iter = 0;
    double best_fitness = 0;
    double prev_global_fit = 1e10;
    while (!pFunc->reachMaxEva())
    {
        int success = 0;
        int gen_count = 0;
        for(int gen=0;gen<gen_times;gen++)
        {
            Optimizer->generation(success);
            gen_count++;
            if (pFunc->reachMaxEva())
                break;        
        }


        //异步共享信息
        double *localBestPar = Optimizer->getBestPar();
        vector<double*> fitii,fitij;
        vector<double*> neighborVec;
        MPI_Request req[commu_object.size()];
        MPI_Request req2[commu_object.size()];
        MPI_Request req3[commu_object.size()];
        MPI_Request req4[commu_object.size()];
        MPI_Request req5[commu_object.size()];

        int rank_index=0;
        for (int rank : commu_object)
        {
            MPI_Isend(localBestPar, dimension, MPI_DOUBLE, rank, 0, MPI_COMM_WORLD, &req[rank_index]);
            rank_index++;
        }
        
        rank_index=0;
        for (int rank : commu_object)
        {
            double *neighbor = new double[dimension];
            MPI_Recv(neighbor, dimension, MPI_DOUBLE, rank, 0, MPI_COMM_WORLD, &stat);

            int hostID=myrank, neighborID=rank;
            double* host = localBestPar;
            double* gb = new double[pFunc->getDimension()];
            memcpy(gb,host,pFunc->getDimension()*sizeof(double));
            if(hostID>neighborID){
                for(int d:overlapDimForEach[rank_index]){
                    gb[d] = neighbor[d];
                }
            }

            double localfit = pFunc->local_eva(gb,hostID);
            int len = overlapDimForEach[rank_index].size();
            double* fij=new double[len]{0};
            double* fii=new double[len]{0};
            for(int i=0;i<len;i++){
                int d = overlapDimForEach[rank_index][i];
                gb[d] = (hostID<neighborID)?neighbor[d]:host[d];
                double newfit = pFunc->local_eva(gb,hostID);
                fii[i] = (hostID<neighborID)?localfit:newfit;
                fij[i] = (hostID<neighborID)?newfit:localfit;
                gb[d] = (hostID<neighborID)?host[d]:neighbor[d];
            }

            MPI_Isend(fij,len,MPI_DOUBLE,rank,1,MPI_COMM_WORLD,&req2[rank_index]);
            MPI_Isend(fii,len,MPI_DOUBLE,rank,2,MPI_COMM_WORLD,&req3[rank_index]);
            
            fitii.push_back(fii);
            fitij.push_back(fij);
            neighborVec.push_back(neighbor);
            rank_index ++;
        }

        vector<double*> fit1p,fit1n;
        rank_index=0;
        memcpy(globalBest, localBestPar, dimension * sizeof(double));
        for (int rank : commu_object)
        {
            int len = overlapDimForEach[rank_index].size();
            double *fji = new double[len];
            double *fjj = new double[len];
            MPI_Recv(fji, len, MPI_DOUBLE, rank, 1, MPI_COMM_WORLD, &stat);
            MPI_Recv(fjj, len, MPI_DOUBLE, rank, 2, MPI_COMM_WORLD, &stat);

            int hostID=myrank;
            double* fii = fitii[rank_index];
            double* fij = fitij[rank_index];
            
            for(int i=0;i<len;i++){
                int d = overlapDimForEach[rank_index][i];  
                if(fii[i]+fji[i] > fij[i]+fjj[i]){
                    ((competition_variable_independent_2*)Competition)->compete_result[d]=1;
                    globalBest[d] = neighborVec[rank_index][d];
                }
                else
                    ((competition_variable_independent_2*)Competition)->compete_result[d]=0;
            }
            

            int sharing_succ = 0;
            Sharing->share(Optimizer->swarm, swarm_size, globalBest, myrank,rank,sharing_succ);

            double* f1p=new double[len];
            double* f1n=new double[len];
            for(int i=0;i<len;i++){
                int d = overlapDimForEach[rank_index][i];  

                double dt = distrub;
                // double dt = new_dt;
                double* gb=globalBest;
                double localfit = pFunc->local_eva(gb,myrank);
                if(gb[d]+dt>=pFunc->getMaxX())
                    dt = pFunc->getMaxX() - gb[d];
                if(gb[d]-dt<=pFunc->getMinX())
                    dt = gb[d] - pFunc->getMinX();
                
                double ov = gb[d];
                gb[d] = min(ov+dt, pFunc->getMaxX());
                f1p[i] = pFunc->local_eva(gb,hostID)-localfit;
                gb[d] = max(ov - dt, pFunc->getMinX());
                f1n[i] = pFunc->local_eva(gb,hostID)-localfit;
                gb[d] = ov;

            }
            MPI_Isend(f1p,len,MPI_DOUBLE,rank,3,MPI_COMM_WORLD,&req4[rank_index]);
            MPI_Isend(f1n,len,MPI_DOUBLE,rank,4,MPI_COMM_WORLD,&req5[rank_index]);
            fit1p.push_back(f1p);
            fit1n.push_back(f1n);

            rank_index ++;
        }

        rank_index=0;
        for (int rank : commu_object)
        {
            int len = overlapDimForEach[rank_index].size();
            double *f2p = new double[len];
            double *f2n = new double[len];
            MPI_Recv(f2p, len, MPI_DOUBLE, rank, 3, MPI_COMM_WORLD, &stat);
            MPI_Recv(f2n, len, MPI_DOUBLE, rank, 4, MPI_COMM_WORLD, &stat);

            double* f1p = fit1p[rank_index];
            double* f1n = fit1n[rank_index];
            for(int i=0;i<len;i++){
                int d = overlapDimForEach[rank_index][i];  
                if( f1p[i]*f2p[i] > 0 && f1n[i]*f2n[i]>0){
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] = 0;
                }else{
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] = ((competition_variable_independent_2*)Competition)->compete_result[d];                    
                }
            }
            rank_index ++;
        }
            
        if (dynamic_cast<evaluator_biasing_local_penalty*>(Evaluator) != nullptr)
        {
            ((evaluator_biasing_local_penalty *)Evaluator)->setGlobalBest(globalBest);
        }
        Optimizer->Evaluator->total_evaluate(Optimizer->swarm);
        sort(Optimizer->swarm.begin(),Optimizer->swarm.end(),cmp_unit_pointer);
        if (optimizer_type == "LLSO") {
            ((optimizer_LLSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        } else if (optimizer_type == "CSO") {
            ((optimizer_CSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        }
        
        MPI_Status Istats[commu_object.size()];
        MPI_Waitall(commu_object.size(), req, Istats);  
        MPI_Waitall(commu_object.size(), req2, Istats); 
        MPI_Waitall(commu_object.size(), req3, Istats); 
        MPI_Waitall(commu_object.size(), req4, Istats); 
        MPI_Waitall(commu_object.size(), req5, Istats); 

        // ===== 保持原始计算逻辑 =====
        double local_fit = Optimizer->Evaluator->evaluate(globalBest);
        double global_fit = global_average(local_fit,commu_object) * nprocs;
        
        // 为了输出对比，也计算纯适应度
        double local_fit_pure = pFunc->local_eva(globalBest, myrank);
        MPI_Barrier(MPI_COMM_WORLD);
        double local_sum_pure = local_fit_pure;
        double global_sum_pure;
        MPI_Allreduce(&local_sum_pure, &global_sum_pure, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        double global_fit_pure = global_sum_pure / nprocs;

        // 配对曲线：首轮 f_pure 标量写入文件，供 RL-MACPO 首轮日志与基线完全一致（同一定义、同一点）
        if (iter == 0) {
            const char* dump_dir = getenv("MACPO_PAIR_INIT_DUMP");
            if (dump_dir != nullptr && dump_dir[0] != '\0' && myrank == 0) {
                char path[4096];
                snprintf(path, sizeof(path), "%s/f_pure_iter0.txt", dump_dir);
                FILE* pfp = fopen(path, "w");
                if (pfp != nullptr) {
                    fprintf(pfp, "%.17e\n", global_fit_pure);
                    fclose(pfp);
                }
            }
        }
        
        // 计算冲突度
        double conflict_now = 0.0;
        if (dynamic_cast<evaluator_variable_wise_penalty*>(Evaluator) != nullptr) {
            evaluator_variable_wise_penalty *eva = (evaluator_variable_wise_penalty*)Evaluator;
            for (int d : overlapDim) {
                if (eva->variable_switch[d] == 1) {
                    conflict_now += fabs(globalBest[d] - localBestPar[d]);
                }
            }
        }

        //判断是否结束

        int reach_max_eva = pFunc->reachMaxEva();
        double if_any_reach_max_eva = global_average(reach_max_eva,commu_object);
        if(if_any_reach_max_eva > 0){
            break;
        }

        evaluator_biasing_local_penalty *eva = dynamic_cast<evaluator_biasing_local_penalty*>(Optimizer->Evaluator);
        if( eva != nullptr){
            penalty_weight = fabs(global_fit)/dynamic_weight;
            eva->setAlpha(penalty_weight);            
        }
        
        // 计算improvement和reward
        double improvement_rate = 0.0;
        if (abs(prev_global_fit) > 1e-8) {
            improvement_rate = (prev_global_fit - global_fit) / abs(prev_global_fit);
        }
        
        double reward = 0.0;
        if (global_fit > 0) {
            reward = -log(global_fit);
        } else {
            reward = -100.0;
        }
        
        if(myrank == 0) {
            cout << "Evaluations: " << pFunc->eva_count
                 << ", Global Fitness: " << global_fit << endl;
                 
            ofstream outfile(filename, ios::app);
            if (outfile.is_open()) {
                outfile << scientific << uppercase << setprecision(2);
                outfile << iter << "\t"
                       << pFunc->eva_count << "\t"
                       << global_fit << "\t"                 // f_penalty (使用原始计算的global_fit)
                       << global_fit_pure << "\t"            // f_pure
                       << (global_fit - global_fit_pure) << "\t"  // penalty
                       << improvement_rate << "\t"
                       << reward << "\t"
                       << conflict_now << "\t"
                       << penalty_weight << endl;
                outfile.close();
            }
        }
        
        prev_global_fit = global_fit;
        iter ++;
    }
    if (myrank == 0) {
        ofstream outfile(filename, ios::app);
        if (outfile.is_open()) {
            outfile << "# Completed [MACPO_" << optimizer_type << "]: iterations=" << iter
                    << ", evals=" << pFunc->eva_count
                    << ", final fitness=" << scientific << prev_global_fit
                    << ", total time=" << (std::time(nullptr) - t2) << "s" << endl;
            outfile.close();
        }
    }
    MPI_Barrier(MPI_COMM_WORLD);
    MPI_Finalize();
}


double global_average(double value, vector<int> neighbor_id){
    MPI_Status stat;
    double gval = value;
    int nei_num = neighbor_id.size();
    int rounds = 20;
    for(int i=0;i<rounds;i++){
        MPI_Request req[neighbor_id.size()];
        for (int rank_index = 0 ; rank_index < nei_num; rank_index ++)
        {
            MPI_Isend(&gval, 1, MPI_DOUBLE, neighbor_id[rank_index], 0, MPI_COMM_WORLD, &req[rank_index]);
        }
        double nval_sum = 0;
        for (int rank_index = 0 ; rank_index < nei_num; rank_index ++)
        {
            double nval;
            MPI_Recv(&nval, 1, MPI_DOUBLE, neighbor_id[rank_index], 0, MPI_COMM_WORLD, &stat);
            nval_sum += nval;
        }
        gval = (gval + nval_sum)/(nei_num+1);
    }

    return gval;
}