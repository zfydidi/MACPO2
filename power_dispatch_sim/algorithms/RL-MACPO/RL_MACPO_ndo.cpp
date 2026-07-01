/**
 * RL_MACPO_ndo.cpp — RL-MACPO × 多场景 NDO（附录 V/VI + IEEE14）
 *
 * 用法:
 *   mpirun -n <N> ./build/RL_MACPO_ndo <SCENARIO> [config] [outDir/]
 */

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
#include "./scenarios/scenario_factory.h"
#include "./scenarios/ndo_common/ndo_sync.h"
#include "./scenarios/maed/maed_init_dispatch.h"

using namespace std;

static bool paired_experiment_enabled() {
    const char* paired = getenv("MACPO_PAIRED");
    if (paired && paired[0] == '1') return true;
    const char* seed = getenv("MACPO_PAIR_SEED");
    return seed != nullptr && seed[0] != '\0';
}

static void apply_paired_rl_config(ExperimentConfig& cfg) {
    cfg.gating_mode = 3;
    cfg.use_variable_filter = true;
    cfg.enable_fail_safe = true;
    cfg.fail_safe_k = 2;
    const char* env_fs = getenv("MACPO_FAILSAFE_K");
    if (env_fs != nullptr && env_fs[0] != '\0') {
        cfg.fail_safe_k = atoi(env_fs);
    }
    cfg.phase_early = 0.90;
    cfg.phase_mid = 0.70;
    cfg.phase_late = 0.50;
}

long getCurrentTime() {
    using namespace std::chrono;
    return static_cast<long>(
        duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count());
}

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

    int myrank, nprocs;
    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Status stat;

    string scenario = (argc >= 2) ? argv[1] : "RESOURCE";
    string expConfig = (argc >= 3) ? argv[2] : "Full";
    string outDir = "./output/";
    if (argc >= 4) {
        outDir = string(argv[3]);
        if (!outDir.empty() && outDir.back() != '/') outDir += "/";
    }

    ScenarioConfig scfg = scenario_config(scenario);
    if (scfg.id == "UNKNOWN") {
        if (myrank == 0) {
            cerr << "Error: unknown scenario '" << scenario
                 << "'. Use RESOURCE | EVDISPATCH | POWER14" << endl;
        }
        MPI_Finalize();
        return 1;
    }

    if (nprocs != scfg.required_ranks) {
        if (myrank == 0) {
            cerr << "Error: scenario " << scfg.id << " requires "
                 << scfg.required_ranks << " MPI ranks, got " << nprocs << endl;
        }
        MPI_Finalize();
        return 1;
    }

    double distrub = 0.1;
    double gen_per_d = scfg.gen_per_d;
    int eva_per_d = scfg.eva_per_d;

    string funcID = scfg.id;
    string exID   = "ex01";

    if (myrank == 0) {
        cout << "=====================================" << endl;
        cout << "RL-MACPO × NDO Scenario: " << scfg.label << endl;
        cout << "Config: " << expConfig << endl;
        cout << "=====================================" << endl;
    }

    double initial_penalty = 0;
    int swarm_size = scfg.swarm_size;
    double prev_global_fit = 1e10;

    {
        const char* pair_seed = getenv("MACPO_PAIR_SEED");
        if (pair_seed != nullptr && pair_seed[0] != '\0') {
            unsigned long sd = strtoul(pair_seed, nullptr, 10);
            srand((unsigned)(sd & 0xffffffffu));
            if (myrank == 0)
                cout << "[RL-MACPO_ndo] scenario=" << scfg.id
                     << " MACPO_PAIR_SEED=" << sd << endl;
        } else {
            srand(getCurrentTime());
        }
    }

    string filename = outDir + funcID + "_RL_" + expConfig + "_" + exID + ".txt";

    if (myrank == 0) {
        ofstream outfile(filename);
        if (outfile.is_open()) {
            outfile << "# Algorithm: RL-MACPO with Enhanced Evaluator" << endl;
            outfile << "# Scenario: " << scfg.label << endl;
            outfile << "# Config: " << expConfig << endl;
            outfile << "# COLUMNS(tab): iter eval f_penalty f_pure penalty improvement "
                       "reward conflict sum_alpha avg_alpha gate_comm wall_ms" << endl;
            outfile.close();
        }
    }

    // ========================================================================
    // 核心: PowerGridBenchmarks 替代 Benchmarks
    // ========================================================================
    Benchmarks *pFunc = create_scenario_benchmark(scenario);
    if (pFunc == nullptr) {
        if (myrank == 0) cerr << "Error: failed to create benchmark" << endl;
        MPI_Finalize();
        return 1;
    }
    int dimension = pFunc->getDimension();
    vector<int> groupDim = pFunc->getGroupDim(myrank);
    // 所有 rank 统一评估预算
    int my_dim = (int)groupDim.size();
    int max_dim = my_dim;
    MPI_Allreduce(&my_dim, &max_dim, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    pFunc->max_eva_times = eva_per_d * max_dim;
    int gen_times = std::max(2, (int)(groupDim.size() * gen_per_d));

    double *globalBest = new double[dimension];
    int* variable_switch = new int[dimension];
    int* compute_result = new int[dimension];
    memset(globalBest, 0, sizeof(double) * dimension);
    memset(variable_switch, 0, sizeof(int) * dimension);
    memset(compute_result, 0, sizeof(int) * dimension);
    maed_init_dispatch_if_needed(scenario, globalBest, dimension);

    // 使用增强评估器
    evaluator *Evaluator = new EnhancedRLPenaltyEvaluator(
        variable_switch, compute_result, dimension, globalBest,
        initial_penalty, pFunc, myrank);

    // 消融实验配置（配对实验时启用 fail-safe 与统一门控）
    {
        ExperimentConfig cfg;
        if (paired_experiment_enabled()) {
            apply_paired_rl_config(cfg);
        } else if (expConfig == "NoGating") {
            cfg.gating_mode = 0; cfg.use_variable_filter = false;
        } else if (expConfig == "Layer1") {
            cfg.gating_mode = 1; cfg.use_variable_filter = false;
        } else if (expConfig == "Layer1_2") {
            cfg.gating_mode = 2; cfg.use_variable_filter = false;
        } else if (expConfig == "NoPhase") {
            cfg.gating_mode = 3; cfg.phase_early = cfg.phase_mid = cfg.phase_late = 0.5;
        } else if (expConfig == "NoSelection") {
            cfg.gating_mode = 3; cfg.use_variable_filter = false;
        } else if (expConfig == "FixedThreshold") {
            cfg.gating_mode = 3; cfg.threshold_mode = 0; cfg.use_variable_filter = false;
        } else if (expConfig == "RelativeThreshold") {
            cfg.gating_mode = 3; cfg.threshold_mode = 1;
            cfg.relative_lambda = 1.2; cfg.ci_ema_beta = 0.9;
            cfg.use_variable_filter = false;
        }
        // Full / 未知: 使用默认值
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_experiment_config(cfg);
    }

    optimizer *Optimizer = new optimizer_LLSO(swarm_size, Evaluator, groupDim);
    competition *Competition = new EnhancedCompetition(
        pFunc, &(Optimizer->swarm), variable_switch);
    sharing *Sharing = new sharing_variable_wise(
        pFunc, ((competition_variable_wise*)Competition)->compete_result);

    Optimizer->init();

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
    double best_fitness = 1e300;

    // ========================================================================
    // 主循环 — 与原版 RL-MACPO 结构一致
    // ========================================================================
    int global_continue = 1;
    while (global_continue) {
        total_loops++;

        // 1. 局部优化
        int success = 0;
        for (int gen = 0; gen < gen_times; gen++) {
            Optimizer->generation(success);
            if (pFunc->reachMaxEva()) break;
        }

        double *localBestPar = Optimizer->getBestPar();

        // 与 MACPO 对齐：局部搜索后若预算用尽，本轮只记录后退出
        int budget_exhausted = 0;
        {
            int local_done = pFunc->reachMaxEva() ? 1 : 0;
            int all_done = 0;
            MPI_Allreduce(&local_done, &all_done, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
            if (all_done == 1) {
                budget_exhausted = 1;
                global_continue = 0;
            }
        }

        // 2. 冲突检测 + 通信门控
        double conflict_now = ((EnhancedRLPenaltyEvaluator*)Evaluator)
            ->calculate_enhanced_conflict(localBestPar);
        bool should_communicate;
        if (paired_experiment_enabled() && iter == 0) {
            should_communicate = true;
        } else {
            should_communicate = ((EnhancedRLPenaltyEvaluator*)Evaluator)
                ->should_communicate(localBestPar, iter);
        }

        // 3. 全局同步决策
        int communicate_int = should_communicate ? 1 : 0;
        int global_communicate_int = 0;
        MPI_Allreduce(&communicate_int, &global_communicate_int,
                      1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
        should_communicate = (global_communicate_int > 0);

        // 4. 协商过程
        if (should_communicate && !budget_exhausted) {
            comm_trigger_loops++;

            vector<double*> fitii, fitij;
            vector<double*> neighborVec;
            int num_neighbors = commu_object.size();

            MPI_Request* req  = new MPI_Request[num_neighbors];
            MPI_Request* req2 = new MPI_Request[num_neighbors];
            MPI_Request* req3 = new MPI_Request[num_neighbors];
            MPI_Request* req4 = new MPI_Request[num_neighbors];
            MPI_Request* req5 = new MPI_Request[num_neighbors];

            // 发送本地最优
            int rank_index = 0;
            for (int rank : commu_object) {
                MPI_Isend(localBestPar, dimension, MPI_DOUBLE, rank, 0,
                          MPI_COMM_WORLD, &req[rank_index]);
                rank_index++;
            }

            // 接收邻居并计算
            rank_index = 0;
            for (int rank : commu_object) {
                double *neighbor = new double[dimension];
                MPI_Recv(neighbor, dimension, MPI_DOUBLE, rank, 0,
                         MPI_COMM_WORLD, &stat);

                int hostID = myrank, neighborID = rank;
                double* host = localBestPar;
                double* gb = new double[dimension];
                memcpy(gb, host, dimension * sizeof(double));
                if (hostID > neighborID) {
                    for (int d : overlapDimForEach[rank_index]) gb[d] = neighbor[d];
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

            // 协商完成 + 共享
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
                Sharing->share(Optimizer->swarm, swarm_size, globalBest,
                               myrank, rank, sharing_succ);

                double* f1p = new double[len];
                double* f1n = new double[len];
                for (int i = 0; i < len; i++) {
                    int d = overlapDimForEach[rank_index][i];
                    double dt = distrub;
                    double* gb = globalBest;
                    double localfit2 = pFunc->local_eva(gb, myrank);
                    if (gb[d] + dt >= pFunc->getMaxX()) dt = pFunc->getMaxX() - gb[d];
                    if (gb[d] - dt <= pFunc->getMinX()) dt = gb[d] - pFunc->getMinX();
                    double ov = gb[d];
                    gb[d] = std::min(ov + dt, pFunc->getMaxX());
                    f1p[i] = pFunc->local_eva(gb, myrank) - localfit2;
                    gb[d] = std::max(ov - dt, pFunc->getMinX());
                    f1n[i] = pFunc->local_eva(gb, myrank) - localfit2;
                    gb[d] = ov;
                }
                MPI_Isend(f1p, len, MPI_DOUBLE, rank, 3, MPI_COMM_WORLD, &req4[rank_index]);
                MPI_Isend(f1n, len, MPI_DOUBLE, rank, 4, MPI_COMM_WORLD, &req5[rank_index]);
                fit1p.push_back(f1p);
                fit1n.push_back(f1n);
                rank_index++;
            }

            // 接收扰动响应
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
                        ((EnhancedCompetition*)Competition)->variable_switch[d] =
                            ((EnhancedCompetition*)Competition)->compete_result[d];
                    }
                }
                delete[] f2p; delete[] f2n;
                rank_index++;
            }

            // 清理
            for (auto p : fitii)  delete[] p;
            for (auto p : fitij)  delete[] p;
            for (auto p : fit1p)  delete[] p;
            for (auto p : fit1n)  delete[] p;
            for (auto p : neighborVec) delete[] p;
            delete[] req; delete[] req2; delete[] req3; delete[] req4; delete[] req5;
        } else if (!budget_exhausted) {
            merge_local_best(globalBest, localBestPar, groupDim);
            sync_overlap_average(globalBest, pFunc, myrank);
        }

        // 5. 与 MACPO 对齐：更新全局最优并重新评估种群
        ((EnhancedRLPenaltyEvaluator*)Evaluator)->set_global_best(globalBest);
        if (!budget_exhausted) {
            Optimizer->Evaluator->total_evaluate(Optimizer->swarm);
            sort(Optimizer->swarm.begin(), Optimizer->swarm.end(), cmp_unit_pointer);
            ((optimizer_LLSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        }

        // 6. 全局适应度 + RL 学习（与主仓库 MACPO_simplified 对齐）
        double f_pure = pFunc->global_fitness(globalBest);
        double f_penalty = f_pure;
        best_fitness = std::min(best_fitness, f_pure);

        if (!budget_exhausted) {
            ((EnhancedRLPenaltyEvaluator*)Evaluator)->update_system_state(
                localBestPar, prev_global_fit, f_pure, overlapDim);
        }

        double improvement = prev_global_fit - f_penalty;
        prev_global_fit = f_penalty;
        if (!budget_exhausted) {
            ((EnhancedRLPenaltyEvaluator*)Evaluator)->update_rl_weight(
                localBestPar, improvement);
        }

        // 7. 记录
        if (myrank == 0) {
            double sum_alpha = 0, avg_alpha = 0;
            // MPI_Allreduce for alpha aggregation simplified
            ofstream outfile(filename, ios::app);
            if (outfile.is_open()) {
                outfile << iter << "\t"
                       << pFunc->eva_count << "\t"
                       << f_penalty << "\t"
                       << f_pure << "\t"
                       << (f_penalty - f_pure) << "\t"
                       << improvement << "\t"
                       << ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_last_rl_reward() << "\t"
                       << ((EnhancedRLPenaltyEvaluator*)Evaluator)->get_conflict_index() << "\t"
                       << sum_alpha << "\t"
                       << avg_alpha << "\t"
                       << (should_communicate ? 1 : 0) << "\t"
                       << (getCurrentTime() - start_time) << endl;
                outfile.close();
            }
        }

        iter++;
        if (budget_exhausted) {
            break;
        }
    }

    if (myrank == 0) {
        double final_f = pFunc->global_fitness(globalBest);
        best_fitness = std::min(best_fitness, final_f);
        long elapsed = getCurrentTime() - start_time;
        double comm_rate = (total_loops > 0)
            ? static_cast<double>(comm_trigger_loops) / total_loops
            : 0.0;
        cout << "[RL-MACPO_ndo] Done. scenario=" << scfg.id
             << " iter=" << iter
             << " eva=" << pFunc->eva_count
             << " comms=" << comm_trigger_loops
             << " time=" << elapsed << "ms" << endl;
        cout << "[RESULT] algorithm=RL-MACPO f_pure=" << scientific << setprecision(6)
             << final_f << " best_f_pure=" << best_fitness
             << " eva=" << pFunc->eva_count
             << " wall_ms=" << elapsed
             << " outer_iters=" << iter
             << " comm_triggers=" << comm_trigger_loops
             << " comm_rate=" << fixed << setprecision(4) << comm_rate << endl;
    }

    MPI_Finalize();
    return 0;
}
