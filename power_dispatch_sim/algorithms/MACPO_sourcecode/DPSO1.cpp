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
using Eigen::MatrixXd;
using Eigen::VectorXd;
// #include "../Benchmarks/game_model.h"
#include "./components/optimizer.h"
#include "./components/evaluator.h"
using namespace std;
using json = nlohmann::json;

long getCurrentTimeMs()
{
    using namespace std::chrono;
    return static_cast<long>(
        duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count());
}

void getMethodConfig(json& ,string&, string&, int&, int&, int&);

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

    std::time_t t2 = std::time(nullptr);
    cout<<"main function "<<std::put_time(std::localtime(&t2), "%Y-%m-%d %H.%M.%S")<<endl;

    if (argc < 2) {
        cerr << "Usage: " << argv[0] << " <funcID> [exID] [LLSO|CSO] [outDir/]\n";
        cerr << "Launch like MACPO: mpirun -n <group_num> ./DPSO1 F1 ex01 LLSO ./output/\n";
        MPI_Finalize();
        return 1;
    }

    // Match GFPDO_overlap / MACPO paper total budget: 150000 * group_num global evals (F1--F6).
    int max_eva = 150000;
    int swarmSize = 300;
    int DPSO_type = 1;
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
    string method = "DPSO1";

    //测试框架注册
    // const int max_eva = 60000;
    cout <<"Benchmark construct begin "<<funcID << endl;
    Benchmarks* pFunc = new Benchmarks(funcID);

    int nodenum = pFunc->getGroupNum();
    if (mpi_size != nodenum) {
        cerr << "Error: mpirun process count (" << mpi_size
             << ") must equal benchmark group_num (" << nodenum
             << "). For F1--F6 use: mpirun -n 20 ./DPSO1 ...\n";
        delete pFunc;
        MPI_Finalize();
        return 1;
    }
    double **W = pFunc->getNetworkGraph();

    MatrixXd Weight(nodenum,nodenum);
    for(int i=0;i<nodenum;i++){
        Weight.row(i) = VectorXd::Map(W[i],nodenum);
    }

    // return 0;
    //演化参数
    pFunc->max_eva_times = max_eva * nodenum;
    //pFunc->max_eva_times = 3000 * pFunc->getGroupDim(0).size() * nodenum;
    int dimension = pFunc->getDimension();

    //评估器注册
    cout <<" evaluator construct begin" << endl;

    vector<evaluator*> EvaSet;
    for(int i=0;i<nodenum;i++){
        evaluator* eva = new evaluator_local(pFunc,i);
        // evaluator* eva = new evaluator_neighbor(pFunc,i,pFunc->getOverlapGroup(i));
        // evaluator* eva = new evaluator_global(pFunc);
        EvaSet.push_back(eva);
    }
    evaluator_global geva(pFunc);

    // 与 MACPO.cpp 一致：非固定种子，用当前时间（毫秒）初始化 rand（仅 rank0 执行主体）
    std::srand(static_cast<unsigned>(getCurrentTimeMs()));


    cout <<" optimizer construct begin" << endl;
    vector<optimizer*> OptSet;
    vector<vector<int>> total_dim_set;
//    vector<int> DimSet;
//    for(int i=0;i<dimension;i++){
//        DimSet.push_back(i);
//    }
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
        opt->init();
        // cout<<pFunc->getLocalOpt(i)<<endl;
        total_dim_set.push_back(DimSet);
    }


    cout<<"evolution begin"<<endl;
    // 关键的数据记录
    double** fitMtx=nullptr;
    double** fitMtx_2=nullptr;
    double** last_local_fit = nullptr;
    for(int i=0;i<nodenum;i++){
        fitMtx = new double*[swarmSize];
        for(int p=0;p<swarmSize;p++){
            fitMtx[p] = new double[nodenum]{0};
        }

        fitMtx_2 = new double*[swarmSize];
        for(int p=0;p<swarmSize;p++){
            fitMtx_2[p] = new double[nodenum]{0};
        }

        last_local_fit = new double*[nodenum];
        for(int s=0;s<nodenum;s++){
            last_local_fit[s] = new double[swarmSize]{0};
        }
    }


    vector<double**> nabla;
    for(int i=0;i<nodenum;i++){
        double **nb = new double*[swarmSize];
        for(int s=0;s<swarmSize;s++){
            nb[s] = new double[dimension]{0};
        }
        nabla.push_back(nb);
    }

    // double fitness=DBL_MAX;
    double best_fit = DBL_MAX;
    double curr_fit = DBL_MAX;
    int iter=0;

    for(int i=0;i<nodenum;i++){
        for(int p=0;p<swarmSize;p++){
            double curr_local_fit = EvaSet[i]->evaluate(OptSet[i]->swarm_ordered[p]->X);
            fitMtx[p][i] = curr_local_fit;
            last_local_fit[i][p] = curr_local_fit;
        }
    }

    ofstream log_file(outDir + "iter_" + method + "_" + funcID + "_" + optimizer_name + "_" + exID + ".txt");
    log_file << "Iteration, BestFitness" << endl;

    const auto wall_t0 = std::chrono::steady_clock::now();

    while( !pFunc->reachMaxEva()){
        int not_evaluate = 1;
        // while(true){
        // while(iter<200){
        for(int n=0;n<nodenum;n++){
            for(int i=0;i<swarmSize;i++){
                for(int d=0;d<dimension;d++){
                    nabla[n][i][d] = OptSet[n]->swarm_ordered[i]->X[d];
                }
            }
        }
///目的：通过适应值均化，在全局范围内调整粒子的搜索行为，鼓励所有节点协同优化。
        if(DPSO_type == 1){
            for(int p=0;p<swarmSize;p++){
                // 计算粒子适应值的均值
                double mean_value = getArrMean(fitMtx[p],nodenum);
                for(int i=0;i<nodenum;i++){
                    // 将均值赋给所有节点的适应值
                    fitMtx_2[p][i] = mean_value;
                }
            }
        }
        /*使用网络权重矩阵 W 将适应值进行加权传播。
        考虑节点之间的关系，通过权重矩阵传播适应值更新每个节点的粒子适应值。
         通过权重矩阵考虑节点之间的交互，模拟适应值在网络中的传播，从而增强优化过程的多样性和协作性
        */
        else if(DPSO_type == 2){
            for(int p=0;p<swarmSize;p++){
                delete[] fitMtx_2[p];
                // 使用权重矩阵更新适应值
                fitMtx_2[p] = multiply_vec_mtx(fitMtx[p],W,nodenum);
            }
        }

        for(int i=0;i<nodenum;i++){
            double last_best_fit = OptSet[i]->swarm[0]->fitness;
            if(iter == 0){
                last_best_fit = 0;
            }
            for(int p=0;p<swarmSize;p++){
                OptSet[i]->swarm_ordered[p]->fitness = fitMtx_2[p][i];
                // OptSet[i]->swarm[p]->fitness = pFunc->global_eva(OptSet[i]->swarm[p]->X);
            }
            if(dynamic_cast<optimizer_LLSO*>(OptSet[i])!=nullptr){
                sort(OptSet[i]->swarm.begin(), OptSet[i]->swarm.end(),cmp_unit_pointer);
                if(last_best_fit>OptSet[i]->swarm[0]->fitness){
                    ((optimizer_LLSO*)(OptSet[i]))->level_size_performance[((optimizer_LLSO*)(OptSet[i]))->NL_index] = (last_best_fit - OptSet[i]->swarm[0]->fitness) / (last_best_fit-((optimizer_LLSO*)(OptSet[i]))->fopt);
                }
                else{
                    ((optimizer_LLSO*)(OptSet[i]))->level_size_performance[((optimizer_LLSO*)(OptSet[i]))->NL_index] = 0;
                }
                // cout<<((optimizer_LLSO*)(OptSet[i]))->NL_index<<" "<<((optimizer_LLSO*)(OptSet[i]))->level_size_performance[((optimizer_LLSO*)(OptSet[i]))->NL_index]<<endl;
            }
        }

        for(int n=0;n<nodenum;n++){
            OptSet[n]->generation(not_evaluate);
            // cout<<rand()<<" ";
        }

        // cout<<endl;
        // for(int i=0;i<nodenum;i++){
        //     for(int p=0;p<swarmSize;p++){
        //         cout<<fitMtx[p][i]<<" ";
        //     }
        //     cout<<endl;
        // }
        // cout<<endl;

        for(int i=0;i<nodenum;i++){
            for(int p=0;p<swarmSize;p++){
                double curr_local_fit = EvaSet[i]->evaluate(OptSet[i]->swarm_ordered[p]->X);
                // fitMtx[p][i] = fitMtx_2[p][i] - (last_local_fit[i][p] - curr_local_fit)*W[i][i];
                // fitMtx[p][i] = fitMtx_2[p][i] - last_local_fit[i][p] + curr_local_fit;
                if(DPSO_type == 1)
                    fitMtx[p][i] = curr_local_fit;
                else if(DPSO_type == 2)
                    fitMtx[p][i] = fitMtx_2[p][i] - last_local_fit[i][p] + curr_local_fit;
                last_local_fit[i][p] = curr_local_fit;
            }
        }

        // for(int i=0;i<nodenum;i++){
        //     for(int p=0;p<swarmSize;p++){
        //         cout<<fitMtx_2[p][i]<<" ";
        //     }
        //     cout<<endl;
        // }
        // cout<<endl;

        // for(int i=0;i<nodenum;i++){
        //         for(int p=0;p<nodenum;p++){
        //             OptSet[i]->swarm[p]->fitness =
        //         }
        //         // cout<<fitMtx[i][j]<<" ";
        //     // cout<<endl;
        // }

        // double best_fit = DBL_MAX;
        curr_fit= DBL_MAX;
        // for(int i=0;i<swarmSize;i++)
        //     curr_fit = min(curr_fit,pFunc->global_eva(OptSet[0]->swarm_ordered[i]->X));
        VectorXd mean_vec(dimension);
        mean_vec.setZero(dimension);
        // for(int i=0;i<nodenum;i++){
        //     VectorXd local_x = VectorXd::Map(OptSet[0]->swarm_ordered[i]->X,dimension);
        //     mean_vec += local_x;
        // }
        // mean_vec /= nodenum;
        // double *mean_arr = mean_vec.data();

        for(int n=0;n<nodenum;n++){
            for (int d : total_dim_set[n]) {
                mean_vec(d) = OptSet[n]->swarm_ordered[0]->X[d];
            }
        }
        curr_fit = geva.evaluate(mean_vec);
        best_fit = min(curr_fit,best_fit);

//        if(argc>1){
            // double dvs = diversity_compute_nabla(nabla,swarmSize,nodenum,dimension);
//            fstream ft(log_filename, ios::app | ios::out);
//            ft<<curr_fit<<" "<<best_fit<<" "<<pFunc->eva_count*1.0/nodenum<<" "<<dvs<<endl;
//            ft.close();
//        }else{
            double dvs = diversity_compute_nabla(nabla,swarmSize,nodenum,dimension);
             //cout<<dvs<<" ";
             cout<<curr_fit<<" ";
             //            cout<<curr_fit<<" "<<dvs<<" "<<pFunc->eva_count*1.0/nodenum<<" ";
            // <<gen_times<<" "<<step<<" "<<count<<endl;
//            for(int i=0;i<nodenum;i++){
//                 cout<<((optimizer_PSO*)OptSet[i])->gbest_fit<<" ";
//             }
        // cout<<count<<" ";
        cout<<endl;
        if(dvs < pow(10,-8))
            break;
//        }‘

        // 输出每次迭代的结果到控制台和日志文件
        cout << "Iteration: " << iter << ", Best Fitness: " << best_fit << endl;
        log_file << iter << ", " << best_fit << endl;

        iter++;
    }

    log_file.close();

    const auto wall_t1 = std::chrono::steady_clock::now();
    const long wall_ms = static_cast<long>(
        std::chrono::duration_cast<std::chrono::milliseconds>(wall_t1 - wall_t0).count());
    std::time_t t_end = std::time(nullptr);
    cout << "Completed [" << method << "/" << optimizer_name << "]: final fitness=" << best_fit
         << ", total_time=" << wall_ms << "ms"
         << ", clock_time=" << difftime(t_end, t2) << "s" << endl;
    {
        ofstream flog(outDir + method + "_" + funcID + "_" + optimizer_name + "_" + exID + ".log");
        if (flog.is_open()) {
            flog << "Completed [" << method << "/" << optimizer_name << "]: final fitness=" << best_fit
                 << ", total_time=" << wall_ms << "ms" << endl;
        }
    }
    MPI_Finalize();
    return 0;
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
                    // if(basename != "DPSO"){
                    //     continue;
                    // }
                    if(basename.find("DPSO") == string::npos){
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
