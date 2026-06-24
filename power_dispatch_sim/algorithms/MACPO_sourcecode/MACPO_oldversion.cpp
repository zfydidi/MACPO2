
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

    // sleep(myrank);

    //读取运行参数
    // double dt_frac = stod(argv[argc-7]);
    double distrub = 0.1;
    // cout<<distrub<<endl;
    int delay = 0;
    double gen_per_d = 0.4;
    int eva_per_d = 3000;
    string exID = "ex01";
    string method = "MACPO";
    string funcID = argv[argc - 1];
    string outDir = "./output/";

    string filename;
    int fileIndex;
    fstream f;
    if(myrank == 0){        
        cout<<"main function "<<std::put_time(std::localtime(&t2), "%Y-%m-%d %H.%M.%S")<<endl;
        //程序输出文件
        fileIndex=0;
        stringstream s;
        while (true) {
            s.str("");
            s << outDir << exID<<"/"<<exID<<"_" << method <<"_"<<funcID << "_" << fileIndex;
            f.open(s.str(), ios::in);
            if (!f.good()) {
                cout << s.str() << endl;
                f.open(s.str(), fstream::out);
                f.close();
                s >> filename;
                break;
            }
            else {
                f.close();
                fileIndex++;
            }
        } 
    }
    MPI_Bcast(&fileIndex,1,MPI_INT,0,MPI_COMM_WORLD);
    string res_file =outDir+ exID +"/"+exID+"_"+method+"_"+funcID+"_"+to_string(fileIndex); 
    string total_filename = outDir + exID +"/total/"+exID+"_"+method+"_"+funcID;
    string log_file = outDir+ exID +"/"+exID+"_"+method+"_"+funcID+"_log_"+to_string(myrank);

    double penalty_weight = 0;
    double dynamic_weight = 512;
    // int sync_interval;
    int max_eva = 3000;
    // int iter_times=200;
    // int iter_times = 100;
    int swarm_size = 300;

    //初始化随机引擎
    srand(getCurrentTime());

    Benchmarks *pFunc= new Benchmarks(funcID,max_eva,true);
    //演化参数
    int dimension = pFunc->getDimension();
    vector<int> groupDim = pFunc->getGroupDim(myrank);
    pFunc->max_eva_times = eva_per_d*groupDim.size();
    // sync_interval = pFunc->max_eva_times/iter_times;
    // int gen_times = groupDim.size() /5 *2;
    int gen_times = groupDim.size()*gen_per_d;

    double *globalBest = new double[dimension];
    memset(globalBest, 0, sizeof(double) * dimension);
    //组件注册
    evaluator *Evaluator = new evaluator_variable_wise_penalty(pFunc, myrank, penalty_weight, globalBest);
    // optimizer *Optimizer = new optimizer_LLSO(swarm_size, Evaluator, groupDim);
    optimizer *Optimizer = new optimizer_CSO(swarm_size, Evaluator, groupDim);
    competition *Competition = new competition_variable_independent_2(pFunc,&(Optimizer->swarm),((evaluator_variable_wise_penalty*)Evaluator)->variable_switch);
    sharing *Sharing =  new sharing_variable_wise(pFunc,((competition_variable_wise*)Competition)->compete_result);

    Competition->set_path(filename +"_competition_log");
    Optimizer->init();
    
    vector<int> overlapDim;    
    vector<vector<int>> overlapDimForEach;
    vector<int> overlap_groups = pFunc->getOverlapGroup(myrank);
    for(int i:overlap_groups){
        vector<int> overlap = pFunc->getOverlapDim(myrank,i);
        overlapDim.insert(overlapDim.end(),overlap.begin(),overlap.end());
        overlapDimForEach.push_back(overlap);
    }

    int iter = 0;
    // int pre_eva_count = 0;
    double best_fitness = 0;
    double product_accumlate = 0;
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

        vector<int> commu_object= pFunc->getOverlapGroup(myrank);

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
            usleep(delay);
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
            usleep(delay);
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
            usleep(delay);
            fit1p.push_back(f1p);
            fit1n.push_back(f1n);

            rank_index ++;
        }

        vector<double> product;
        vector<double> gradient_sum_vec;
        vector<int> conflict_count_vec;
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
            double product_sum=0;
            double f1_sum=0,f2_sum=0;
            double gradient_sum = 0;
            int conflict_count = 0;
            for(int i=0;i<len;i++){
                int d = overlapDimForEach[rank_index][i];  
                if( f1p[i]*f2p[i] > 0 && f1n[i]*f2n[i]>0){
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] = 0;
                }else{
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] = ((competition_variable_independent_2*)Competition)->compete_result[d];
                    conflict_count ++;
                }
                f1_sum+=f1p[i]*f1p[i];
                f2_sum+=f2p[i]*f2p[i];
                product_sum+=f1p[i]*f2p[i];
                gradient_sum += (f1p[i]+f2p[i])*(f1p[i]+f2p[i]);
            }
            product_sum/=sqrt(f1_sum*f2_sum);      
            product.push_back(product_sum);
            product_accumlate += product_sum;
            gradient_sum = sqrt(gradient_sum/len);
            gradient_sum_vec.push_back(gradient_sum);
            conflict_count_vec.push_back(conflict_count);
            

            rank_index ++;
        }
            

        if (dynamic_cast<evaluator_biasing_local_penalty*>(Evaluator) != nullptr)
        {
            ((evaluator_biasing_local_penalty *)Evaluator)->setGlobalBest(globalBest);
        }
        Optimizer->Evaluator->total_evaluate(Optimizer->swarm);
        sort(Optimizer->swarm.begin(),Optimizer->swarm.end(),cmp_unit_pointer);
        ((optimizer_LLSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        
        MPI_Status Istats[commu_object.size()];
        MPI_Waitall(commu_object.size(), req, Istats);  
        MPI_Waitall(commu_object.size(), req2, Istats); 
        MPI_Waitall(commu_object.size(), req3, Istats); 
        MPI_Waitall(commu_object.size(), req4, Istats); 
        MPI_Waitall(commu_object.size(), req5, Istats); 

        //记录
        double *recv = nullptr;
        if (myrank == 0)
        {
            recv = new double[dimension * nprocs]{0};
        }

        MPI_Gather(globalBest, dimension, MPI_DOUBLE, recv, dimension, MPI_DOUBLE, 0, MPI_COMM_WORLD);
        double fitness = 0;
        double *globalSolution = nullptr;
        if (myrank == 0)
        {
            globalSolution = new double[dimension];
            for (int rank = 0; rank < nprocs; rank++)
            {
                vector<int> dim = pFunc->getGroupDim(rank);
                for (int d : dim)
                {
                    globalSolution[d] = recv[rank * dimension + d];
                }
            }
            delete[] recv;
    
            fitness = pFunc->global_eva(globalSolution);
            cout << " iteration " << iter << ": " << fitness << endl;

            f.open(filename, ios::app | ios::out);
            f << fitness << endl;
            f.close();
            
            if(iter == 0)
                best_fitness = fitness;
            else
                best_fitness = min(best_fitness,fitness);                
        }
        
        //判断是否结束
        int *recv2 = nullptr;
        if (myrank == 0)
        {
            recv2 = new int[nprocs]{0};
        }

        int reach_max_eva = pFunc->reachMaxEva();
        MPI_Gather(&reach_max_eva,1,MPI_INT,recv2,1,MPI_INT,0,MPI_COMM_WORLD);
        int finish_process = 0;
        if(myrank == 0){
            bool finish = false;
            for(int rank=0;rank<nprocs;rank++){
                if(recv2[rank] != 0){
                    finish = true;
                    break;
                }
            }
            if(finish == true){
                // cout<<"rank 0 final shot "<<total_filename<<endl;
                std::time_t t3 = std::time(nullptr);
                cout<<"main function "<<std::put_time(std::localtime(&t3), "%Y-%m-%d %H.%M.%S")<<endl;
                cout<<"cost time: "<<difftime(t3,t2)<<"s"<<endl<<endl;
                
                f.open(total_filename, ios::app | ios::out);
                f << best_fitness <<" "<<difftime(t3,t2)<< endl;
                f.close();            
                finish_process = 1;
            }
        }
        MPI_Bcast(&finish_process,1,MPI_INT,0,MPI_COMM_WORLD);

        if(finish_process == 1){
            product_accumlate /= (iter+1);  
            break;
        }

        evaluator_biasing_local_penalty *eva = dynamic_cast<evaluator_biasing_local_penalty*>(Optimizer->Evaluator);
        if( eva != nullptr){
            if(myrank == 0){
                penalty_weight = fabs(fitness)/dynamic_weight;
            }
            MPI_Bcast(&penalty_weight,1,MPI_DOUBLE,0,MPI_COMM_WORLD);
            // penalty_weight = fabs(Optimizer->swarm[0]->fitness)/dynamic_weight;
            eva->setAlpha(penalty_weight);            
        }

        iter ++;
        if(myrank == 0 && (iter == 25 || iter == 50 || iter == 75 || iter ==150 || iter == 360)){
            std::time_t t3 = std::time(nullptr);
            cout<<iter<<" cost time: "<<difftime(t3,t2)<<"s"<<endl;
        }
    }
    MPI_Barrier(MPI_COMM_WORLD);
    MPI_Finalize();
}