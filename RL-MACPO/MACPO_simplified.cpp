#include <float.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <chrono>
#include <iostream>
#include <fstream>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <mpi.h>

#include "./Benchmarks/Benchmarks.h"
#include "./components/optimizer.h"
#include "./components/sharing.h"
#include "./components/enhanced_evaluator.h"
#include "./components/enhanced_competition.h"

using namespace std;

// 获取当前时间（毫秒），跨平台（Windows / Linux / macOS）
long getCurrentTime() {
    using namespace std::chrono;
    return static_cast<long>(
        duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count());
}

// 简化的全局平均函数（基于原始源码）
double global_average(double value, vector<int> neighbor_id) {
    MPI_Status stat;
    double gval = value;
    int nei_num = neighbor_id.size();
    int rounds = 20;
    
    for (int i = 0; i < rounds; i++) {
        MPI_Request req[neighbor_id.size()];
        for (int rank_index = 0; rank_index < nei_num; rank_index++) {
            MPI_Isend(&gval, 1, MPI_DOUBLE, neighbor_id[rank_index], 0, MPI_COMM_WORLD, &req[rank_index]);
        }
        
        double nval_sum = 0;
        for (int rank_index = 0; rank_index < nei_num; rank_index++) {
            double nval;
            MPI_Recv(&nval, 1, MPI_DOUBLE, neighbor_id[rank_index], 0, MPI_COMM_WORLD, &stat);
            nval_sum += nval;
        }
        gval = (gval + nval_sum) / (nei_num + 1);
    }
    return gval;
}

int main(int argc, char* argv[]) {
    long start_time = getCurrentTime();
    
    // MPI初始化
    int myrank, nprocs;
    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Status stat;
    
    
    // 算法参数（与原始源码一致）
    double distrub = 0.1;
    double gen_per_d = 0.4;
    int eva_per_d = 3000;
    
    // 从命令行参数获取funcID、exID、实验配置
    // 用法: mpirun -n 20 ./MACPO_simplified F1 ex01 [config] [outDir/]
    // config: RL_Only|NoGating|Layer1|Layer1_2|Full|NoPhase|Phase_60_30_15|Phase_80_50_15|NoSelection|Selection_0.9_0.6_0.3|Selection_0.9_0.7_0.5
    // mechanism variants: AlwaysOn|FixedThreshold|RelativeThreshold|RelativeThresholdFailSafe|PeriodicK2|PeriodicK3|PeriodicK5
    // outDir: optional, default ./output/
    string funcID = argv[1];
    string exID = (argc >= 3) ? argv[2] : "ex01";
    string expConfig = (argc >= 4) ? argv[3] : "Full";
    string outDir = "./output/";
    if (argc >= 5) {
        outDir = string(argv[4]);
        if (!outDir.empty() && outDir.back() != '/') outDir += "/";
    }
    bool debug_gate = false;
    const char* dbg_env = getenv("MACPO_DEBUG_GATE");
    if (dbg_env != nullptr && string(dbg_env) == "1") debug_gate = true;
    int debug_max_loops = -1;
    const char* dbg_loops_env = getenv("MACPO_DEBUG_MAX_LOOPS");
    if (dbg_loops_env != nullptr) debug_max_loops = atoi(dbg_loops_env);
    bool force_fixed_loops = (debug_max_loops > 0);
    
    if (myrank == 0) {
        cout << "=====================================" << endl;
        cout << "Reward: Final penalty-efficiency reward (dimensionless tanh)" << endl;
        cout << endl;
        cout << "=====================================" << endl;
    }
    
    string method = "RL-MACPO-LLSO";  // 使用LLSO优化器
    
    double initial_penalty = 0;
    int swarm_size = 300;
    double prev_global_fit = 1e10;
    double ema_fitness = 1e6;
    
    {
        const char* pair_seed = getenv("MACPO_PAIR_SEED");
        if (pair_seed != nullptr && pair_seed[0] != '\0') {
            unsigned long sd = strtoul(pair_seed, nullptr, 10);
            srand((unsigned)(sd & 0xffffffffu));
            if (myrank == 0) {
                cout << "[RL-MACPO] MACPO_PAIR_SEED=" << sd << " (paired trace RNG)" << endl;
            }
        } else {
            srand(getCurrentTime());
        }
    }
    
    // 输出文件名: output/F1_LLSO_final_ex01.txt
    string filename = outDir + funcID + "_LLSO_final_" + exID + ".txt";
    
    // 写入表头（只在文件开始时写入一次）
    // 数据行：tab 分隔；列含义见 # COLUMNS（供 plot_rl_metrics_curves.py / utils/rl_macpo_runlog.py 解析）
    if (myrank == 0) {
        ofstream outfile(filename);
        if (outfile.is_open()) {
            outfile << "# Algorithm: LLSO" << endl;
            outfile << "# RL-MACPO with multi-agent alpha aggregation (sum of all agents' alpha)" << endl;
            outfile << "# COLUMNS(tab): iter eval f_penalty f_pure penalty improvement reward conflict "
                       "sum_alpha avg_alpha alpha_rank0 alpha_min alpha_max "
                       "gate_comm base_alpha_avg rho_avg rho_r0 rho_min rho_max f_pure_bsf"
                    << endl;
            outfile.close();
        }
    }
    
    // 创建基准函数和组件（基于原始逻辑）
    Benchmarks *pFunc = new Benchmarks(funcID, 0, true);
    int dimension = pFunc->getDimension();
    vector<int> groupDim = pFunc->getGroupDim(myrank);
    pFunc->max_eva_times = eva_per_d * groupDim.size();
    int gen_times = groupDim.size() * gen_per_d;
    
    // 初始化数组
    double *globalBest = new double[dimension];
    int* variable_switch = new int[dimension];
    int* compute_result = new int[dimension];
    memset(globalBest, 0, sizeof(double) * dimension);
    memset(variable_switch, 0, sizeof(int) * dimension);
    memset(compute_result, 0, sizeof(int) * dimension);
    
    // 创建组件
    evaluator *Evaluator = new EnhancedRLPenaltyEvaluator(variable_switch, compute_result, dimension, globalBest, initial_penalty, pFunc, myrank);
    
    // 设置消融实验配置
    {
        ExperimentConfig cfg;
        if (expConfig == "RL_Only" || expConfig == "NoGating") {
            cfg.gating_mode = 0;
            cfg.use_variable_filter = false;
        } else if (expConfig == "AlwaysOn") {
            cfg.gating_mode = 0;
            cfg.use_variable_filter = false;
        } else if (expConfig == "FixedThreshold") {
            cfg.gating_mode = 3;
            cfg.threshold_mode = 0;
            cfg.use_variable_filter = false;
        } else if (expConfig == "FixedThresholdNoFailSafe") {
            cfg.gating_mode = 3;
            cfg.threshold_mode = 0;
            cfg.enable_fail_safe = false;
            cfg.use_variable_filter = false;
        } else if (expConfig == "RelativeThreshold") {
            cfg.gating_mode = 3;
            cfg.threshold_mode = 1;
            cfg.relative_lambda = 1.2;
            cfg.ci_ema_beta = 0.9;
            cfg.use_variable_filter = false;
        } else if (expConfig == "RelativeThresholdFailSafe") {
            cfg.gating_mode = 3;
            cfg.threshold_mode = 1;
            cfg.relative_lambda = 1.2;
            cfg.ci_ema_beta = 0.9;
            cfg.enable_fail_safe = true;
            cfg.fail_safe_k = 10;
            cfg.use_variable_filter = false;
        } else if (expConfig == "Layer1") {
            cfg.gating_mode = 1;
            cfg.use_variable_filter = false;
        } else if (expConfig == "Layer1_2") {
            cfg.gating_mode = 2;
            cfg.use_variable_filter = false;
        } else if (expConfig == "NoPhase") {
            cfg.gating_mode = 3;
            cfg.phase_early = cfg.phase_mid = cfg.phase_late = 0.5;
        } else if (expConfig == "Phase_60_30_15") {
            cfg.gating_mode = 3;
            cfg.phase_early = 0.6; cfg.phase_mid = 0.3; cfg.phase_late = 0.15;
        } else if (expConfig == "Phase_80_50_15") {
            cfg.gating_mode = 3;
            cfg.phase_early = 0.8; cfg.phase_mid = 0.5; cfg.phase_late = 0.15;
        } else if (expConfig == "NoSelection") {
            cfg.gating_mode = 3;
            cfg.use_variable_filter = false;
        } else if (expConfig == "Selection_0.9_0.6_0.2") {
            cfg.gating_mode = 3;
            cfg.selection_early = 0.9; cfg.selection_mid = 0.6; cfg.selection_late = 0.2;
        } else if (expConfig == "Selection_0.9_0.6_0.3") {
            cfg.gating_mode = 3;
            cfg.selection_early = 0.9; cfg.selection_mid = 0.6; cfg.selection_late = 0.3;
        } else if (expConfig == "Selection_0.9_0.7_0.5") {
            cfg.gating_mode = 3;
            cfg.selection_early = 0.9; cfg.selection_mid = 0.7; cfg.selection_late = 0.5;
        } else if (expConfig == "Sanity_A_NoThreshold") {
            // A: interval + phase (threshold恒真)
            cfg.gating_mode = 3;
            cfg.force_disable_threshold = true;
            cfg.use_variable_filter = false;
        } else if (expConfig == "Sanity_B_NoPhase") {
            // B: interval + threshold (phase恒真)
            cfg.gating_mode = 3;
            cfg.force_disable_phase = true;
            cfg.use_variable_filter = false;
        } else if (expConfig == "Sanity_C_AllOn") {
            // C: 三层恒真（强制每轮通信）
            cfg.gating_mode = 0;
            cfg.use_variable_filter = false;
        } else if (expConfig.rfind("PeriodicK", 0) == 0) {
            cfg.gating_mode = 3;
            cfg.force_periodic = true;
            cfg.periodic_k = std::max(1, atoi(expConfig.c_str() + 9));
            cfg.use_variable_filter = false;
        }
        // Optional env overrides for sensitivity tests
        const char* env_lambda = getenv("MACPO_REL_LAMBDA");
        if (env_lambda != nullptr) {
            cfg.threshold_mode = 1;
            cfg.relative_lambda = atof(env_lambda);
        }
        const char* env_beta = getenv("MACPO_CI_EMA_BETA");
        if (env_beta != nullptr) {
            cfg.threshold_mode = 1;
            cfg.ci_ema_beta = atof(env_beta);
        }
        const char* env_fs = getenv("MACPO_FAILSAFE_K");
        if (env_fs != nullptr) {
            cfg.enable_fail_safe = true;
            cfg.fail_safe_k = atoi(env_fs);
        }
        const char* env_no_fs = getenv("MACPO_DISABLE_FAILSAFE");
        if (env_no_fs != nullptr && (env_no_fs[0] == '1' || env_no_fs[0] == 'y' || env_no_fs[0] == 'Y')) {
            cfg.enable_fail_safe = false;
        }
        // Full 或未知配置使用默认
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_experiment_config(cfg);
    }
    
    optimizer *Optimizer = new optimizer_LLSO(swarm_size, Evaluator, groupDim);
    competition *Competition = new EnhancedCompetition(pFunc, &(Optimizer->swarm), variable_switch);
    sharing *Sharing = new sharing_variable_wise(pFunc, ((competition_variable_wise*)Competition)->compete_result);
    
    Optimizer->init();
    
    // 获取重叠信息（与原始逻辑一致）
    vector<int> overlapDim;
    vector<vector<int>> overlapDimForEach;
    vector<int> overlap_groups = pFunc->getOverlapGroup(myrank);
    for (int i : overlap_groups) {
        vector<int> overlap = pFunc->getOverlapDim(myrank, i);
        overlapDim.insert(overlapDim.end(), overlap.begin(), overlap.end());
        overlapDimForEach.push_back(overlap);
    }
    
    vector<int> commu_object = pFunc->getOverlapGroup(myrank);
    
    int iter = 0;
    int total_loops = 0;
    int comm_trigger_loops = 0;
    int enter_negotiation_branch_loops = 0;
    long long total_negotiation_dims = 0;

    // Gate-by-gate debug counters (local per-rank, aggregate at end)
    long long gate_interval_pass = 0;
    long long gate_threshold_pass = 0;
    long long gate_phase_pass = 0;
    long long gate_local_pass = 0;
    long long gate_global_pass = 0;
    long long ci_gt_tau_count = 0;
    std::vector<double> ci_values;
    std::vector<double> tau_values;
    std::vector<double> ci_minus_tau_values;
    std::vector<double> ci_ema_values;
    std::vector<double> iter_global_mean_ci;
    std::vector<int> iter_global_gate;
    long long fail_safe_fire_count = 0;
    
    // === 简化的主循环（基于原始源码结构） ===
    while (force_fixed_loops || !pFunc->reachMaxEva()) {
        total_loops++;
        // 1. 粒子群优化（与原始完全一致）
        int success = 0;
        for (int gen = 0; gen < gen_times; gen++) {
            Optimizer->generation(success);
            if (!force_fixed_loops && pFunc->reachMaxEva()) break;
        }
        
        // 2. 获取当前最优解
        double *localBestPar = Optimizer->getBestPar();
        
        // 3. 计算冲突和通信决策
        double conflict_now = ((EnhancedRLPenaltyEvaluator*)Evaluator)->calculate_enhanced_conflict(localBestPar);
        bool should_communicate = ((EnhancedRLPenaltyEvaluator*)Evaluator)->should_communicate(localBestPar, iter);
        auto gate_decision = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_last_gate_decision();

        // 配对初值公平曲线：首轮必须与 MACPO 基线一样走完整协商（基线无门控跳过），否则 globalBest 与首行 f_pure 不可比
        {
            const char* pair_load = getenv("MACPO_PAIR_INIT_LOAD");
            if (pair_load != nullptr && pair_load[0] != '\0' && iter == 0) {
                should_communicate = true;
            }
        }

        if (gate_decision.interval_ok) gate_interval_pass++;
        if (gate_decision.threshold_ok) gate_threshold_pass++;
        if (gate_decision.phase_ok) gate_phase_pass++;
        if (gate_decision.local_gate) gate_local_pass++;
        if (gate_decision.conflict_index > gate_decision.threshold) ci_gt_tau_count++;
        if (gate_decision.fail_safe_fired) fail_safe_fire_count++;

        ci_values.push_back(gate_decision.conflict_index);
        tau_values.push_back(gate_decision.threshold);
        ci_minus_tau_values.push_back(gate_decision.conflict_index - gate_decision.threshold);
        ci_ema_values.push_back(gate_decision.ci_ema);
        
        // 4. 全局通信同步
        int communicate_int = should_communicate ? 1 : 0;
        int global_communicate_int = 0;
        MPI_Allreduce(&communicate_int, &global_communicate_int, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
        should_communicate = (global_communicate_int > 0);
        if (should_communicate) gate_global_pass++;

        // Global mean CI per iteration (for CI-bin -> trigger probability)
        double local_ci_for_mean = gate_decision.conflict_index;
        double sum_ci_for_mean = 0.0;
        MPI_Allreduce(&local_ci_for_mean, &sum_ci_for_mean, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        if (myrank == 0) {
            iter_global_mean_ci.push_back(sum_ci_for_mean / (double)nprocs);
            iter_global_gate.push_back(should_communicate ? 1 : 0);
        }
        
        // 5. 记录信息（删除不必要的日志）
        if (debug_gate && myrank == 0 && iter < 20) {
            cout << "[GATE_DEBUG] iter=" << iter
                 << " CI=" << gate_decision.conflict_index
                 << " tau=" << gate_decision.threshold
                 << " diff=" << (gate_decision.conflict_index - gate_decision.threshold)
                 << " C_int=" << (gate_decision.interval_ok ? 1 : 0)
                 << " C_thr=" << (gate_decision.threshold_ok ? 1 : 0)
                 << " C_phase=" << (gate_decision.phase_ok ? 1 : 0)
                 << " u=" << gate_decision.phase_u
                 << " p_phase=" << gate_decision.phase_freq
                 << " ci_ema=" << gate_decision.ci_ema
                 << " g_local=" << (gate_decision.local_gate ? 1 : 0)
                 << " g_global=" << (should_communicate ? 1 : 0)
                 << " fs=" << (gate_decision.fail_safe_fired ? 1 : 0)
                 << " last_comm=" << gate_decision.last_comm_iter
                 << endl;
        }
        
        // 6. 协商过程（大幅简化，基于原始源码逻辑）
        if (should_communicate) {
            comm_trigger_loops++;
            enter_negotiation_branch_loops++;
            long long dims_this_round = 0;
            for (const auto& ov : overlapDimForEach) dims_this_round += (long long)ov.size();
            total_negotiation_dims += dims_this_round;

            vector<double*> fitii, fitij;
            vector<double*> neighborVec;
            
            // === 使用动态分配避免可变长度数组栈溢出问题 ===
            int num_neighbors = commu_object.size();
            MPI_Request* req = new MPI_Request[num_neighbors];
            MPI_Request* req2 = new MPI_Request[num_neighbors];
            MPI_Request* req3 = new MPI_Request[num_neighbors];
            MPI_Request* req4 = new MPI_Request[num_neighbors];
            MPI_Request* req5 = new MPI_Request[num_neighbors];
            
            // 发送本地最优解
            int rank_index = 0;
            for (int rank : commu_object) {
                MPI_Isend(localBestPar, dimension, MPI_DOUBLE, rank, 0, MPI_COMM_WORLD, &req[rank_index]);
                rank_index++;
            }
            
            // 接收邻居解并计算竞争适应度
            rank_index = 0;
            for (int rank : commu_object) {
                double *neighbor = new double[dimension];
                MPI_Recv(neighbor, dimension, MPI_DOUBLE, rank, 0, MPI_COMM_WORLD, &stat);
                
                int hostID = myrank, neighborID = rank;
                double* host = localBestPar;
                double* gb = new double[dimension];
                memcpy(gb, host, dimension * sizeof(double));
                
                if (hostID > neighborID) {
                    for (int d : overlapDimForEach[rank_index]) {
                        gb[d] = neighbor[d];
                    }
                }
                
                double localfit = pFunc->local_eva(gb, hostID);
                int len = overlapDimForEach[rank_index].size();
                double* fij = new double[len]{0};
                double* fii = new double[len]{0};
                
                for (int i = 0; i < len; i++) {
                    int d = overlapDimForEach[rank_index][i];
                    gb[d] = (hostID < neighborID) ? neighbor[d] : host[d];
                    double newfit = pFunc->local_eva(gb, hostID);
                    fii[i] = (hostID < neighborID) ? localfit : newfit;
                    fij[i] = (hostID < neighborID) ? newfit : localfit;
                    gb[d] = (hostID < neighborID) ? host[d] : neighbor[d];
                }
                
                MPI_Isend(fij, len, MPI_DOUBLE, rank, 1, MPI_COMM_WORLD, &req2[rank_index]);
                MPI_Isend(fii, len, MPI_DOUBLE, rank, 2, MPI_COMM_WORLD, &req3[rank_index]);
                
                fitii.push_back(fii);
                fitij.push_back(fij);
                neighborVec.push_back(neighbor);
                delete[] gb;
                rank_index++;
            }
            
            // 初始化扰动适应度
            vector<double*> fit1p, fit1n;
            rank_index = 0;
            memcpy(globalBest, localBestPar, dimension * sizeof(double));
            
            for (int rank : commu_object) {
                int len = overlapDimForEach[rank_index].size();
                double *fji = new double[len];
                double *fjj = new double[len];
                MPI_Recv(fji, len, MPI_DOUBLE, rank, 1, MPI_COMM_WORLD, &stat);
                MPI_Recv(fjj, len, MPI_DOUBLE, rank, 2, MPI_COMM_WORLD, &stat);
                
                double* fii = fitii[rank_index];
                double* fij = fitij[rank_index];
                
                for (int i = 0; i < len; i++) {
                    int d = overlapDimForEach[rank_index][i];
                    if (fii[i] + fji[i] > fij[i] + fjj[i]) {
                        ((EnhancedCompetition*)Competition)->compete_result[d] = 1;
                        globalBest[d] = neighborVec[rank_index][d];
                    } else {
                        ((EnhancedCompetition*)Competition)->compete_result[d] = 0;
                    }
                }
                delete[] fji;
                delete[] fjj;

                int sharing_succ = 0;
                Sharing->share(Optimizer->swarm, swarm_size, globalBest, myrank, rank, sharing_succ);
                
                double* f1p = new double[len];
                double* f1n = new double[len];
                
                for (int i = 0; i < len; i++) {
                    int d = overlapDimForEach[rank_index][i];
                    double dt = distrub;
                    double* gb = globalBest;
                    double localfit = pFunc->local_eva(gb, myrank);
                    
                    if (gb[d] + dt >= pFunc->getMaxX()) 
                    dt = pFunc->getMaxX() - gb[d];
                    if (gb[d] - dt <= pFunc->getMinX()) 
                    dt = gb[d] - pFunc->getMinX();
                    
                    double ov = gb[d];
                    gb[d] = min(ov + dt, pFunc->getMaxX());
                    f1p[i] = pFunc->local_eva(gb, myrank) - localfit;
                    gb[d] = max(ov - dt, pFunc->getMinX());
                    f1n[i] = pFunc->local_eva(gb, myrank) - localfit;
                    gb[d] = ov;
                }
                
                MPI_Isend(f1p, len, MPI_DOUBLE, rank, 3, MPI_COMM_WORLD, &req4[rank_index]);
                MPI_Isend(f1n, len, MPI_DOUBLE, rank, 4, MPI_COMM_WORLD, &req5[rank_index]);
                fit1p.push_back(f1p);
                fit1n.push_back(f1n);
                rank_index++;
            }
            
            // 接收扰动结果并进行冲突检测
            rank_index = 0;
            for (int rank : commu_object) {
                int len = overlapDimForEach[rank_index].size();
                double *f2p = new double[len];
                double *f2n = new double[len];
                MPI_Recv(f2p, len, MPI_DOUBLE, rank, 3, MPI_COMM_WORLD, &stat);
                MPI_Recv(f2n, len, MPI_DOUBLE, rank, 4, MPI_COMM_WORLD, &stat);
                
                double* f1p = fit1p[rank_index];
                double* f1n = fit1n[rank_index];
                
                for (int i = 0; i < len; i++) {
                    int d = overlapDimForEach[rank_index][i];
                    if (f1p[i] * f2p[i] > 0 && f1n[i] * f2n[i] > 0) {
                        ((EnhancedCompetition*)Competition)->variable_switch[d] = 0;
                    } else {
                        ((EnhancedCompetition*)Competition)->variable_switch[d] = ((EnhancedCompetition*)Competition)->compete_result[d];
                    }
                }
                
                delete[] f2p;
                delete[] f2n;
                rank_index++;
            }
            
            // 等待所有异步通信完成
            MPI_Status* Istats = new MPI_Status[num_neighbors];
            MPI_Waitall(num_neighbors, req, Istats);
            MPI_Waitall(num_neighbors, req2, Istats);
            MPI_Waitall(num_neighbors, req3, Istats);
            MPI_Waitall(num_neighbors, req4, Istats);
            MPI_Waitall(num_neighbors, req5, Istats);
            
            // 清理内存
            for (auto ptr : neighborVec) delete[] ptr;
            for (auto ptr : fitii) delete[] ptr;
            for (auto ptr : fitij) delete[] ptr;
            for (auto ptr : fit1p) delete[] ptr;
            for (auto ptr : fit1n) delete[] ptr;
            
            // 清理动态分配的MPI数组
            delete[] req;
            delete[] req2;
            delete[] req3;
            delete[] req4;
            delete[] req5;
            delete[] Istats;
            
        } else {
            // 跳过通信时直接使用本地最优解
            memcpy(globalBest, localBestPar, dimension * sizeof(double));
        }
        
        // 7. 更新评估器和重新评估
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_global_best(globalBest);
        Evaluator->total_evaluate(Optimizer->swarm);
        sort(Optimizer->swarm.begin(), Optimizer->swarm.end(), cmp_unit_pointer);
        ((optimizer_LLSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        
        // 8. 计算全局适应度和RL更新
        // ===== 与Baseline保持一致的计算方式 =====
        // 计算带惩罚项的目标函数值，使用global_average()（与Baseline一致）
        double local_fit_with_penalty = Evaluator->evaluate(globalBest);
        double global_fit_with_penalty = global_average(local_fit_with_penalty, commu_object) * nprocs;
        
        // 计算真实目标函数值(不含惩罚项)，使用MPI_Allreduce()精确计算（与Baseline一致）
        double local_fit_pure = pFunc->local_eva(globalBest, myrank);
        MPI_Barrier(MPI_COMM_WORLD);
        double local_sum_pure = local_fit_pure;
        double global_sum_pure;
        MPI_Allreduce(&local_sum_pure, &global_sum_pure, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
        double global_fit_pure = global_sum_pure / nprocs;
        // 配对实验：首轮 f_pure 与 MACPO 基线完全一致（读入基线首轮写出的标量）
        {
            const char* pair_dir = getenv("MACPO_PAIR_INIT_LOAD");
            if (iter == 0 && pair_dir != nullptr && pair_dir[0] != '\0' && myrank == 0) {
                char ppath[4096];
                snprintf(ppath, sizeof(ppath), "%s/f_pure_iter0.txt", pair_dir);
                FILE* pfp = fopen(ppath, "r");
                if (pfp != nullptr) {
                    double v = global_fit_pure;
                    if (fscanf(pfp, "%lf", &v) == 1) {
                        global_fit_pure = v;
                    }
                    fclose(pfp);
                }
            }
        }
        MPI_Bcast(&global_fit_pure, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
        
        // 使用带惩罚的适应度作为主要评价指标（与Baseline一致）
        double global_fit = global_fit_with_penalty;

        // 激活学习机制：更新适应度历史、变量重要性、通信效率
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->update_system_state(
            localBestPar, prev_global_fit, global_fit_pure, overlapDim);

        // ========== 设置基准α并动态调整以适应实际conflict规模 ==========
        // ✅ 正确设计：每次迭代都更新base_alpha，让penalty随fitness自动缩放
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_base_alpha(global_fit);
        
        if (iter == 0) {
            // 第一次迭代后：测量实际conflict并动态调整α
            double base_alpha = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_base_alpha();
            
            // 测量实际conflict（使用基类的calculate_conflict）
            double measured_conflict = ((RLPenaltyEvaluator*)Evaluator)->calculate_conflict(localBestPar);
            
            if (myrank == 0) {
                cout << "[LLSO] 第一次迭代完成 - 动态α调整" << endl;
                cout << "  - global_fit = " << global_fit << endl;
                cout << "  - base_alpha = |f| / 512 = " << base_alpha << endl;
                cout << "  - measured_conflict = " << measured_conflict << endl;
            }
            
            // 动态调整：如果conflict较大（>1.0），则缩小α
            if (measured_conflict > 1.0) {
                // 计算α的动态缩放因子
                // 目标：使 penalty/f ≈ 0.195% = 1/512
                // 公式：α_adjusted = base_alpha / measured_conflict
                double scaling_factor = 1.0 / measured_conflict;
                double adjusted_alpha = base_alpha * scaling_factor;
                
                // 直接设置调整后的α
                ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_alpha(adjusted_alpha);
                
                if (myrank == 0) {
                    cout << "  - scaling_factor = 1.0 / conflict = " << scaling_factor << endl;
                    cout << "  - adjusted_alpha = base_alpha × scaling = " << adjusted_alpha << endl;
                    cout << "  - 预期 penalty/f ≈ 0.195%" << endl;
                }
            } else if (myrank == 0) {
                cout << "  - conflict ≤ 1.0，不需要调整α" << endl;
            }
        }
        
        // RL权重更新 + 轨迹记录（与 MACPO baseline 对齐：每个外循环含 iter==0 写一行）
        {
            static double historical_best = 1e10;
            static double best_f_pure_bsf = 1e300;
            static bool ema_initialized = false;
            
            double improvement_rate = 0.0;
            if (abs(prev_global_fit) > 1e-8) {
                improvement_rate = (prev_global_fit - global_fit) / abs(prev_global_fit);
            }
            
            double reward = 0.0;
            if (iter > 0) {
                historical_best = min(historical_best, global_fit);
                if (!ema_initialized) {
                    ema_fitness = global_fit;
                    ema_initialized = true;
                }
                ema_fitness = 0.8 * ema_fitness + 0.2 * global_fit;
                // reward由evaluator内部的最终reward函数计算
                ((EnhancedRLPenaltyEvaluator*)Evaluator)->update_rl_weight(localBestPar, 0.0);
                reward = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_last_rl_reward();
            }
            // iter==0：不写 RL 经验，reward 记 0（尚未发生策略更新）
            
            double local_alpha = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_alpha();
            double sum_alpha = 0.0;
            double avg_alpha = 0.0;
            double min_alpha = 0.0;
            double max_alpha = 0.0;
            MPI_Allreduce(&local_alpha, &sum_alpha, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            MPI_Allreduce(&local_alpha, &max_alpha, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
            MPI_Allreduce(&local_alpha, &min_alpha, 1, MPI_DOUBLE, MPI_MIN, MPI_COMM_WORLD);
            avg_alpha = sum_alpha / nprocs;

            double local_rho = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_weight_ratio();
            double local_base_alpha = ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_base_alpha();
            double sum_rho = 0.0;
            double avg_rho = 0.0;
            double min_rho = 0.0;
            double max_rho = 0.0;
            MPI_Allreduce(&local_rho, &sum_rho, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            MPI_Allreduce(&local_rho, &max_rho, 1, MPI_DOUBLE, MPI_MAX, MPI_COMM_WORLD);
            MPI_Allreduce(&local_rho, &min_rho, 1, MPI_DOUBLE, MPI_MIN, MPI_COMM_WORLD);
            avg_rho = sum_rho / nprocs;

            double sum_ba = 0.0;
            double avg_base_alpha = 0.0;
            MPI_Allreduce(&local_base_alpha, &sum_ba, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
            avg_base_alpha = sum_ba / nprocs;

            int gate_comm_int = should_communicate ? 1 : 0;

            if (myrank == 0) {
                best_f_pure_bsf = std::min(best_f_pure_bsf, global_fit_pure);
                ofstream outfile(filename, ios::app);
                if (outfile.is_open()) {
                    outfile << scientific << uppercase << setprecision(8);
                    outfile << iter << "\t"
                           << pFunc->eva_count << "\t"
                           << global_fit_with_penalty << "\t"
                           << global_fit_pure << "\t"
                           << (global_fit_with_penalty - global_fit_pure) << "\t"
                           << improvement_rate << "\t"
                           << reward << "\t"
                           << conflict_now << "\t"
                           << sum_alpha << "\t"
                           << avg_alpha << "\t"
                           << local_alpha << "\t"
                           << min_alpha << "\t"
                           << max_alpha << "\t"
                           << gate_comm_int << "\t"
                           << avg_base_alpha << "\t"
                           << avg_rho << "\t"
                           << local_rho << "\t"
                           << min_rho << "\t"
                           << max_rho << "\t"
                           << best_f_pure_bsf << endl;
                    outfile.close();
                }
            }
            prev_global_fit = global_fit;
        }
        
        // 9. 检查终止条件
        MPI_Barrier(MPI_COMM_WORLD);
        if (!force_fixed_loops) {
            double reach_max_eva = pFunc->reachMaxEva() ? 1.0 : 0.0;
            double if_any_reach_max_eva = global_average(reach_max_eva, commu_object);
            if (if_any_reach_max_eva > 0) break;
        }
        
        // 10. 记录进度（已在上面的RL更新部分记录，这里删除重复输出）
        
        MPI_Barrier(MPI_COMM_WORLD);
        iter++;

        // Debug快速定位模式：限制迭代轮次，避免长时间运行
        if (debug_max_loops > 0 && iter >= debug_max_loops) {
            break;
        }
    }

    auto* ee = (EnhancedRLPenaltyEvaluator*)Evaluator;
    int active_switch = 0;
    for (int d = 0; d < dimension; d++) {
        if (variable_switch[d] != 0) active_switch++;
    }
    double comm_rate = total_loops > 0 ? (double)comm_trigger_loops / (double)total_loops : 0.0;
    double avg_nego_dims = comm_trigger_loops > 0
        ? (double)total_negotiation_dims / (double)comm_trigger_loops
        : 0.0;
    double active_switch_ratio = dimension > 0 ? (double)active_switch / (double)dimension : 0.0;

    // Aggregate gate debug counters across all ranks (must be called by all ranks)
    long long local_samples = (long long)total_loops;
    long long global_samples = 0;
    long long global_interval_pass = 0, global_threshold_pass = 0, global_phase_pass = 0;
    long long global_local_pass = 0, global_global_pass = 0;
    long long global_enter_neg_branch = 0, global_comm_trigger = 0;
    long long global_ci_gt_tau = 0, global_fail_safe_fire = 0;
    long long local_enter_neg_branch = (long long)enter_negotiation_branch_loops;
    long long local_comm_trigger = (long long)comm_trigger_loops;
    MPI_Allreduce(&local_samples, &global_samples, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&gate_interval_pass, &global_interval_pass, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&gate_threshold_pass, &global_threshold_pass, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&gate_phase_pass, &global_phase_pass, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&gate_local_pass, &global_local_pass, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&gate_global_pass, &global_global_pass, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&local_enter_neg_branch, &global_enter_neg_branch, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&local_comm_trigger, &global_comm_trigger, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&ci_gt_tau_count, &global_ci_gt_tau, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);
    MPI_Allreduce(&fail_safe_fire_count, &global_fail_safe_fire, 1, MPI_LONG_LONG, MPI_SUM, MPI_COMM_WORLD);

    // Gather CI / tau / (CI-tau) samples for quantiles
    int local_n = (int)ci_values.size();
    std::vector<int> recv_counts;
    if (myrank == 0) recv_counts.resize(nprocs, 0);
    MPI_Gather(&local_n, 1, MPI_INT, myrank == 0 ? recv_counts.data() : nullptr, 1, MPI_INT, 0, MPI_COMM_WORLD);

    std::vector<int> displs;
    int total_n = 0;
    if (myrank == 0) {
        displs.resize(nprocs, 0);
        for (int i = 0; i < nprocs; i++) {
            displs[i] = total_n;
            total_n += recv_counts[i];
        }
    }

    std::vector<double> all_ci, all_tau, all_diff, all_ci_ema;
    if (myrank == 0) {
        all_ci.resize(total_n);
        all_tau.resize(total_n);
        all_diff.resize(total_n);
        all_ci_ema.resize(total_n);
    }
    MPI_Gatherv(ci_values.data(), local_n, MPI_DOUBLE,
                myrank == 0 ? all_ci.data() : nullptr,
                myrank == 0 ? recv_counts.data() : nullptr,
                myrank == 0 ? displs.data() : nullptr,
                MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Gatherv(tau_values.data(), local_n, MPI_DOUBLE,
                myrank == 0 ? all_tau.data() : nullptr,
                myrank == 0 ? recv_counts.data() : nullptr,
                myrank == 0 ? displs.data() : nullptr,
                MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Gatherv(ci_minus_tau_values.data(), local_n, MPI_DOUBLE,
                myrank == 0 ? all_diff.data() : nullptr,
                myrank == 0 ? recv_counts.data() : nullptr,
                myrank == 0 ? displs.data() : nullptr,
                MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Gatherv(ci_ema_values.data(), local_n, MPI_DOUBLE,
                myrank == 0 ? all_ci_ema.data() : nullptr,
                myrank == 0 ? recv_counts.data() : nullptr,
                myrank == 0 ? displs.data() : nullptr,
                MPI_DOUBLE, 0, MPI_COMM_WORLD);

    auto quantile = [](std::vector<double> v, double q) -> double {
        if (v.empty()) return 0.0;
        std::sort(v.begin(), v.end());
        double pos = q * (double)(v.size() - 1);
        int lo = (int)std::floor(pos);
        int hi = (int)std::ceil(pos);
        if (lo == hi) return v[lo];
        double w = pos - (double)lo;
        return v[lo] * (1.0 - w) + v[hi] * w;
    };
    auto mean_of = [](const std::vector<double>& v) -> double {
        if (v.empty()) return 0.0;
        double s = 0.0;
        for (double x : v) s += x;
        return s / (double)v.size();
    };

    double p_int = global_samples > 0 ? (double)global_interval_pass / (double)global_samples : 0.0;
    double p_thr = global_samples > 0 ? (double)global_threshold_pass / (double)global_samples : 0.0;
    double p_phase = global_samples > 0 ? (double)global_phase_pass / (double)global_samples : 0.0;
    double p_local = global_samples > 0 ? (double)global_local_pass / (double)global_samples : 0.0;
    double p_global = global_samples > 0 ? (double)global_global_pass / (double)global_samples : 0.0;
    double p_ci_gt_tau = global_samples > 0 ? (double)global_ci_gt_tau / (double)global_samples : 0.0;

    // 先写 rank0 调试块（量化统计等），再 Barrier，再记墙钟并追加 COST_STATS（含 total_time_ms）
    if (myrank == 0) {
        ofstream outfile(filename, ios::app);
        if (outfile.is_open()) {
            outfile << "# GATE_DEBUG_SUMMARY"
                    << " total_rounds=" << total_loops
                    << " p_interval=" << p_int
                    << " p_threshold=" << p_thr
                    << " p_phase=" << p_phase
                    << " p_local=" << p_local
                    << " p_global=" << p_global
                    << " enter_negotiation_count=" << global_enter_neg_branch
                    << " avg_active_switch_ratio=" << active_switch_ratio
                    << endl;
            if (!all_ci.empty()) {
                outfile << "# GATE_DEBUG_CI_TAU"
                        << " ci_mean=" << mean_of(all_ci)
                        << " ci_median=" << quantile(all_ci, 0.5)
                        << " ci_min=" << quantile(all_ci, 0.0)
                        << " ci_max=" << quantile(all_ci, 1.0)
                        << " ci_p05=" << quantile(all_ci, 0.05)
                        << " ci_p95=" << quantile(all_ci, 0.95)
                        << " tau_mean=" << mean_of(all_tau)
                        << " tau_median=" << quantile(all_tau, 0.5)
                        << " tau_min=" << quantile(all_tau, 0.0)
                        << " tau_max=" << quantile(all_tau, 1.0)
                        << " tau_p05=" << quantile(all_tau, 0.05)
                        << " tau_p95=" << quantile(all_tau, 0.95)
                        << " ci_ema_mean=" << mean_of(all_ci_ema)
                        << " diff_mean=" << mean_of(all_diff)
                        << " diff_median=" << quantile(all_diff, 0.5)
                        << " diff_min=" << quantile(all_diff, 0.0)
                        << " diff_max=" << quantile(all_diff, 1.0)
                        << " diff_p05=" << quantile(all_diff, 0.05)
                        << " diff_p95=" << quantile(all_diff, 0.95)
                        << " p_ci_gt_tau=" << p_ci_gt_tau
                        << endl;
            }

            if (!iter_global_mean_ci.empty() && iter_global_mean_ci.size() == iter_global_gate.size()) {
                std::vector<double> sorted_ci = iter_global_mean_ci;
                std::sort(sorted_ci.begin(), sorted_ci.end());
                auto edge = [&](double q) {
                    double pos = q * (double)(sorted_ci.size() - 1);
                    int lo = (int)std::floor(pos);
                    int hi = (int)std::ceil(pos);
                    if (lo == hi) return sorted_ci[lo];
                    double w = pos - (double)lo;
                    return sorted_ci[lo] * (1.0 - w) + sorted_ci[hi] * w;
                };
                double e1 = edge(0.2), e2 = edge(0.4), e3 = edge(0.6), e4 = edge(0.8);
                long long bin_cnt[5] = {0, 0, 0, 0, 0};
                long long bin_hit[5] = {0, 0, 0, 0, 0};
                for (size_t i = 0; i < iter_global_mean_ci.size(); i++) {
                    double x = iter_global_mean_ci[i];
                    int b = 4;
                    if (x <= e1) b = 0;
                    else if (x <= e2) b = 1;
                    else if (x <= e3) b = 2;
                    else if (x <= e4) b = 3;
                    bin_cnt[b]++;
                    if (iter_global_gate[i] > 0) bin_hit[b]++;
                }
                outfile << "# CI_BIN_TRIGGER"
                        << " bins=5"
                        << " edges=" << e1 << "," << e2 << "," << e3 << "," << e4;
                for (int b = 0; b < 5; b++) {
                    double prob = bin_cnt[b] > 0 ? (double)bin_hit[b] / (double)bin_cnt[b] : 0.0;
                    outfile << " bin" << b << "_n=" << bin_cnt[b]
                            << " bin" << b << "_p=" << prob;
                }
                outfile << endl;
            }
            outfile.close();
        }
    }

    MPI_Barrier(MPI_COMM_WORLD);
    long end_time = getCurrentTime();
    long total_time = end_time - start_time;

    if (myrank == 0) {
        cout << "Completed [LLSO]: iterations=" << iter
             << ", evals=" << pFunc->eva_count
             << ", final fitness=" << prev_global_fit
             << ", total time=" << total_time << "ms" << endl;
        ofstream outfile(filename, ios::app);
        if (outfile.is_open()) {
            outfile << "# COST_STATS"
                    << " loops=" << total_loops
                    << " comm_loops=" << comm_trigger_loops
                    << " comm_rate=" << comm_rate
                    << " gate_p_interval=" << p_int
                    << " gate_p_threshold=" << p_thr
                    << " gate_p_phase=" << p_phase
                    << " gate_p_local=" << p_local
                    << " gate_p_global=" << p_global
                    << " gate_ci_gt_tau=" << p_ci_gt_tau
                    << " comm_trigger_count=" << global_global_pass
                    << " enter_negotiation_count=" << global_enter_neg_branch
                    << " fail_safe_fire_count=" << global_fail_safe_fire
                    << " comm_eff=" << ee->get_communication_efficiency()
                    << " avg_nego_dims=" << avg_nego_dims
                    << " switch_active_ratio=" << active_switch_ratio
                    << " rl_updates=" << ee->get_rl_update_count()
                    << " filter_select_ratio=" << ee->get_avg_selected_ratio()
                    << " total_time_ms=" << total_time
                    << endl;
            outfile.close();
        }
    }

    // 清理资源
    delete[] globalBest;
    delete[] variable_switch;
    delete[] compute_result;
    delete Evaluator;
    delete Optimizer;
    delete Competition;
    delete Sharing;
    delete pFunc;
    
    MPI_Finalize();
    return 0;
} 