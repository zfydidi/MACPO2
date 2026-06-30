#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <chrono>
#include <ctime>
#include <iomanip>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <vector>
#include <mpi.h>
#include <Eigen/Dense>


#include "./Benchmarks/Benchmarks.h"
#include "./components/optimizer.h"
#include "./components/evaluator.h"
using namespace std;
using namespace Eigen;

long getCurrentTimeMs()
{
    using namespace std::chrono;
    return static_cast<long>(
        duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count());
}

// 函数声明
void getMethodConfig(json& ,string&, string&, int&, int&, int&);
double diversity(Matrix<Matrix<double,Dynamic,Dynamic>,1,Dynamic> population,int swarmSize,int nodenum,int dimension);
double diversity_2(MatrixXd population,int nodenum,int col);
double diversity_internal(Matrix<Matrix<double,Dynamic,Dynamic>,1,Dynamic> population,int swarmSize,int nodenum,int dimension);

int main(int argc, char* argv[])
{
    MPI_Init(&argc, &argv);
    int mpi_rank = 0, mpi_size = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &mpi_rank);
    MPI_Comm_size(MPI_COMM_WORLD, &mpi_size);
    if (mpi_rank != 0) {
        MPI_Finalize();
        return 0;
    }

    // 获取当前时间
    std::time_t t2 = std::time(nullptr);
    cout<<"Main function start: "<<std::put_time(std::localtime(&t2), "%Y-%m-%d %H.%M.%S")<<endl;

    if (argc < 2) {
        cerr << "Usage: " << argv[0] << " <funcID> [exID] [LLSO|CSO] [outDir/]\n";
        cerr << "Launch like MACPO: mpirun -n <group_num> ./GFPDO_overlap F1 ex01 LLSO ./output/\n";
        MPI_Finalize();
        return 1;
    }
    // 初始化参数
    int max_eva = 150000;// 最大评估次数
    int swarmSize = 300;// 种群大小
    string funcID = argv[1];
    string exID = (argc >= 3) ? argv[2] : "ex01";
    string optimizer_name = (argc >= 4) ? argv[3] : "LLSO";
    string outDir = (argc >= 5) ? argv[4] : "./output/";
    if (!outDir.empty() && outDir.back() != '/') outDir += "/";
    if (optimizer_name != "LLSO" && optimizer_name != "CSO") {
        cerr << "optimizer must be LLSO or CSO, got: " << optimizer_name << endl;
        MPI_Finalize();
        return 1;
    }
    string method = "GFPDO";

    //测试框架注册
    // const int max_eva = 60000;
    // 初始化基准函数
    cout <<"Benchmark construct begin "<<funcID << endl;
    Benchmarks* pFunc = new Benchmarks(funcID);

    // 获取节点数量
    const int nodenum = pFunc->getGroupNum();
    if (mpi_size != nodenum) {
        cerr << "Error: mpirun process count (" << mpi_size
             << ") must equal benchmark group_num (" << nodenum
             << "). For F1--F6 use: mpirun -n 20 ./GFPDO_overlap ...\n";
        delete pFunc;
        MPI_Finalize();
        return 1;
    }
    // 获取网络图（邻接矩阵）
    double **W = pFunc->getNetworkGraph();

    // 将权重矩阵转换为 Eigen 格式
    MatrixXd Weight(nodenum,nodenum);
    for(int i=0;i<nodenum;i++){
        Weight.row(i) = VectorXd::Map(W[i],nodenum);
    }

    // return 0;
    //演化参数
    // 设置最大评估次数
    pFunc->max_eva_times = max_eva * nodenum;
    // 获取维度信息
    int dimension = pFunc->getDimension();    

    //评估器注册
    cout <<" evaluator construct begin" << endl;

    // 初始化评估器
    vector<evaluator*> EvaSet;
    for(int i=0;i<nodenum;i++){
        evaluator* eva = new evaluator_local(pFunc,i);
        // evaluator* eva = new evaluator_neighbor(pFunc,i,pFunc->getOverlapGroup(i));
        // evaluator* eva = new evaluator_global(pFunc);
        EvaSet.push_back(eva);
    }
    
    // 与 MACPO.cpp 一致：非固定种子（毫秒时间），仅 rank0 执行主体
    std::srand(static_cast<unsigned>(getCurrentTimeMs()));

    // vector<int> DimSet;
    // for(int i=0;i<dimension;i++){
    //     DimSet.push_back(i);
    // }

    // 全局评估器
    evaluator_global geva(pFunc);
    cout <<" optimizer construct begin" << endl;
    vector<optimizer*> OptSet;
    vector<vector<int>> total_dim_set;
    for(int i=0;i<nodenum;i++){
        vector<int> DimSet = pFunc->getGroupDim(i);
        optimizer* opt;
        if(optimizer_name == "LLSO"){
            opt = new optimizer_LLSO(swarmSize,EvaSet[i],DimSet);
            ((optimizer_LLSO*)opt)->setFopt(pFunc->getLocalOpt(i));
        }
        else if(optimizer_name == "CSO")
            opt = new optimizer_CSO(swarmSize,EvaSet[i],DimSet);

        OptSet.push_back(opt);
        opt->init();// 全局评估器
        // cout<<pFunc->getLocalOpt(i)<<endl;
        total_dim_set.push_back(DimSet);
    }

    // 初始化邻居和重叠维度
    vector<vector<int>> neighbors;
    vector<vector<vector<int>>> overlap_dims;
    for(int myrank=0;myrank<nodenum;myrank++){
        vector<vector<int>> overlapDimForEach;
        vector<int> overlap_groups = pFunc->getOverlapGroup(myrank);
        for(int i:overlap_groups){
            vector<int> overlap = pFunc->getOverlapDim(myrank,i);
            overlapDimForEach.push_back(overlap);
        }
        neighbors.push_back(overlap_groups);
        overlap_dims.push_back(overlapDimForEach);
    }

    cout<<"data initialization"<<endl;
    // 关键的数据记录

    // 初始化种群和适应度矩阵
    Matrix<Matrix<double,Dynamic,Dynamic>,1,Dynamic> population;
    population.resize(1,nodenum);
    for(int i=0;i<nodenum;i++){
        population(0,i).setZero(swarmSize,dimension);
    }
    
    MatrixXd fitness(nodenum,swarmSize);

    // double fitness=DBL_MAX;
    double best_fit = DBL_MAX; // 全局最优适应度
    double curr_fit = DBL_MAX;// 当前适应度
    double commu_1_total =0, commu_2_total=0;// 通信计数
    int iter=0;// 迭代次数

    const string iter_log_path = outDir + "iter_" + method + "_" + funcID + "_" + optimizer_name + "_" + exID + ".txt";
    ofstream log_file(iter_log_path);
    log_file << "Iteration, BestFitness" << endl;
    cout<<"evolution begin"<<endl;

    const auto wall_t0 = std::chrono::steady_clock::now();

    // for(;iter<1;){
    // 迭代优化过程
    while( !pFunc->reachMaxEva()) {        
    // while(true){
        int not_evaluate = 1;

        // 每个节点进行一次优化
        for(int n=0;n<nodenum;n++){
            OptSet[n]->generation(not_evaluate);
        }
        // for(int i=0;i<swarmSize;i++){
        //     for(int n=0;n<nodenum;n++){
        //         population(0,i).row(n) = VectorXd::Map(OptSet[n]->swarm_ordered[i]->X,dimension);
        //     }
        // }

        // 更新种群位置
        for(int n=0;n<nodenum;n++){
            for(int i=0;i<swarmSize;i++){
                population(0,n).row(i) = VectorXd::Map(OptSet[n]->swarm_ordered[i]->X,dimension);
            }
        }
        // for(int i=0;i<swarmSize;i++){
        //     cout<<population(0,i)<<endl<<endl;
        // }

        int commu_1 = 0;
        // double dvs = DBL_MAX;
        // while(dvs > 0.001){
        //     for(int i=0;i<swarmSize;i++){
        //         population(0,i) = Weight*population(0,i);
        //     }
        //     dvs = diversity(population,swarmSize,nodenum,dimension);
        //     commu_1 ++;
        // }

        // 邻居通信，交换重叠维度
        for(int n=0;n<nodenum;n++){
            for(int nei_num = 0; nei_num < neighbors[n].size(); nei_num++){
                int nei_idx = neighbors[n][nei_num];
                if(n < nei_idx){                    
                    vector<int> idxs = {1,3,5};
                    for (int od : overlap_dims[n][nei_num]) {
                        VectorXd tmp = population(0,n).col(od) + population(0,nei_idx).col(od);
                        population(0,n).col(od) = tmp / 2.0;
                        population(0,nei_idx).col(od) = tmp / 2.0;
                    }
                }
            }
        }

        // 计算适应度
        for(int i=0;i<swarmSize;i++){
            for(int n=0;n<nodenum;n++){
                double a = EvaSet[n]->evaluate(population(0,n).row(i));
                fitness(n,i) = a;
                // cout<<a<<" "<<fitness(n,i)<<endl;
            }
        }

        // if(iter%20==0)
        //     cout<<fitness<<endl<<endl;

        // 第二阶段通信：基于权重矩阵更新适应度分布
        int commu_2 = 0;
        double van = DBL_MAX;
        // 基于权重矩阵传播适应度，直到多样性 van 小于阈值停止通信
        while(van>0.001){
            fitness = Weight*fitness;// 使用权重矩阵更新适应度
            VectorXd avg = fitness.colwise().mean();// 计算适应度的列平均值
            van = diversity_2(fitness,nodenum,swarmSize);// 计算适应度分布的多样性
            commu_2 ++;
        }
        // 更新优化器种群信息，包括位置、适应值，以及对 LLSO 优化器进行排序
        for(int n=0;n<nodenum;n++){
            for(int i=0;i<swarmSize;i++){                
                for(int d=0;d<dimension;d++){
                    OptSet[n]->swarm_ordered[i]->X[d] = population(0,n)(i,d);
                }
                OptSet[n]->swarm_ordered[i]->fitness = fitness(n,i);
            }
            if(dynamic_cast<optimizer_LLSO*>(OptSet[0])!=nullptr){
                // 排序种群
                sort(OptSet[n]->swarm.begin(),OptSet[n]->swarm.end(),cmp_unit_pointer);
                // 更新最优适应值
                ((optimizer_LLSO*)OptSet[n])->bestFit = OptSet[n]->swarm[0]->fitness;
            }
        }


        // 聚合各节点的最优解并评估全局适应值，更新全局最优值
        // curr_fit = fitness.minCoeff();
        VectorXd agg_solution = VectorXd::Zero(dimension);
        for(int n=0;n<nodenum;n++){
            for (int d : total_dim_set[n]) {
                agg_solution(d) = population(0,n)(0, d);
            }
        }

        //评估聚合解
        curr_fit = geva.evaluate(agg_solution);
        best_fit = min(curr_fit,best_fit);// 更新全局最优适应值

        // 统计第一阶段和第二阶段的通信次数
        commu_1_total += commu_1;
        commu_2_total += commu_2;

        // 检查多样性
        double idvs = diversity_internal(population,swarmSize,nodenum,dimension);

//        cout<<curr_fit<<" ";
        // cout<<commu_1<<" "<<commu_2<<" "<<pFunc->eva_count*1.0/nodenum<<" ";
        // cout<<idvs<<" ";
//        cout<<endl;
        // 多样性过低时提前停止
        if(idvs < pow(10,-8))
            break;

        log_file << iter << ", " << best_fit << endl;

        cout << "Iteration: " << iter << " Best Fitness: " << best_fit << endl;
        
        iter++;
    }
    log_file.close();
    const auto wall_t1 = std::chrono::steady_clock::now();
    const long wall_ms = static_cast<long>(
        std::chrono::duration_cast<std::chrono::milliseconds>(wall_t1 - wall_t0).count());
    std::time_t t_end = std::time(nullptr);
    cout << "Completed [" << method << "/" << optimizer_name << "]: final fitness=" << best_fit
         << ", total time=" << wall_ms << "ms"
         << ", clock_time=" << difftime(t_end, t2) << "s" << endl;
    {
        std::ofstream flog(outDir + method + "_" + funcID + "_" + optimizer_name + "_" + exID + ".log");
        if (flog.is_open()) {
            flog << "Completed [" << method << "/" << optimizer_name << "]: final fitness=" << best_fit
                 << ", total time=" << wall_ms << "ms" << endl;
        }
    }

    MPI_Finalize();
    return 0;
}

double diversity(Matrix<Matrix<double,Dynamic,Dynamic>,1,Dynamic> population,int swarmSize,int nodenum,int dimension){
    double mean_std = 0;
    for(int i=0;i<swarmSize;i++){
        VectorXd mean_vec_2 = VectorXd::Zero(dimension);
        for(int n=0;n<nodenum;n++){
            mean_vec_2 += population(0,n).row(i);
        }
        mean_vec_2 /= nodenum;
        for(int n=0;n<nodenum;n++)
            mean_std += (population(0,n).row(i).transpose()-mean_vec_2).norm();
    }
    mean_std /= (nodenum*swarmSize);

    return mean_std;
}

double diversity_2(MatrixXd X,int nodenum,int col){    
    MatrixXd a = X.rowwise()-X.colwise().mean();
    return a.colwise().norm().mean();
}

double diversity_internal(Matrix<Matrix<double,Dynamic,Dynamic>,1,Dynamic> population,int swarmSize,int nodenum,int dimension){
    double mean_std = 0;
    for(int n=0;n<nodenum;n++){
        VectorXd mean_vec_2 = VectorXd::Zero(dimension);
        for(int i=0;i<swarmSize;i++){
            mean_vec_2 += population(0,n).row(i);
        }
        mean_vec_2 /= swarmSize;
        for(int i=0;i<swarmSize;i++)
            mean_std += (population(0,n).row(i).transpose()-mean_vec_2).norm();
    }
    mean_std /= (nodenum*swarmSize);

    return mean_std;
}

void getMethodConfig(json &ex ,string &log_filename, string &total_filename, int& method_index, int& func_index, int& file_index){
    string exID = ex["ID"];
    int run_times = ex["run_times"];
    string output_dir = ex["output_dir"];
    vector<string> func_id = ex["funcID"];
    vector<json> methods = ex["methods"];
    stringstream s;
    fstream f;
    for(int index = 0; index < run_times; index++){
        for(unsigned int f_index = 0; f_index < func_id.size();f_index++){
            string func = func_id[f_index];
            for(unsigned int m_index=0;m_index<methods.size();m_index++){
                try{
                    string var = ex["variable"];
                    vector<double> paras = ex["paras"];
                    for(double p : paras){
                        ex["methods"][m_index][var] = p;

                        json method = methods[m_index];
                        s.str("");
                        string basename = method["file_basename"];
                        s << output_dir << exID <<"/"<<exID <<"_"<< basename <<"_"<<p << "_" << func << "_" << index;
                        f.open(s.str(), ios::in);
                        if (!f.good()){
                            cout << s.str() << endl;
                            f.open(s.str(), fstream::out);
                            f.close();
                            s >> log_filename;
                            stringstream tf;
                            tf.str("");
                            tf<<output_dir<<exID<<"/total/"<<exID<<"_"<<basename<<"_"<<p<<"_"<<func;
                            // total_filename = output_dir + "total/" + exID + "_" + basename + "_" + to_string(p) + "_" + func;
                            tf>>total_filename;
                            method_index = m_index;
                            func_index = f_index;
                            file_index = index;
                            return;
                        }else{
                            f.close();
                        }
                    }
                }catch(...){
                    json method = methods[m_index];
                    s.str("");
                    string basename = method["file_basename"];
                    if(basename.find("GFPDO") == string::npos){
                        continue;
                    }
                    s << output_dir << exID <<"/"<<exID <<"_"<< basename << "_" << func << "_" << index;
                    f.open(s.str(), ios::in);
                    if (!f.good()){
                        cout << s.str() << endl;
                        f.open(s.str(), fstream::out);
                        // f<<s.str()<<endl;
                        f.close();
                        s >> log_filename;
                        total_filename = output_dir + exID + "/total/" + exID + "_" + basename + "_" + func;
                        method_index = m_index;
                        func_index = f_index;
                        file_index = index;
                        return;
                    }else{
                        f.close();
                    }
                }
            }
        }
    }
}
