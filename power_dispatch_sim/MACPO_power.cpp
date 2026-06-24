/**
 * MACPO_power.cpp — MACPO × IEEE 标准算例区域互联经济调度
 *
 * 用法:
 *   mpirun -n <R> ./build/MACPO_power <CASE> [LLSO|CSO] [outDir/]
 *
 * CASE: IEEE14 | IEEE30 | IEEE57 | IEEE118  (或 POWER14 等别名)
 * R = 区域数 (14/30/57→4, 118→8)
 */

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
#include "./scenarios/power_grid/PowerGridBenchmarks.h"
#include "./scenarios/power_grid/power_grid_protocol.h"
#include "./scenarios/power_grid/power_grid_init_dispatch.h"
#include "./scenarios/ndo_common/ndo_sync.h"
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
    // MPI 初始化
    int myrank, nprocs, name;
    char proc_name[MPI_MAX_PROCESSOR_NAME];

    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);
    MPI_Comm_rank(MPI_COMM_WORLD, &myrank);
    MPI_Get_processor_name(proc_name, &name);
    MPI_Status stat;

    string caseName = (argc >= 2) ? argv[1] : "IEEE14";
    IeeeGridCaseId caseId = parse_ieee_grid_case(caseName.c_str());
    const IeeeGridCaseDesc* caseDesc = ieee_grid_case_desc(caseId);
    if (!caseDesc) {
        if (myrank == 0) {
            cerr << "Error: unknown CASE '" << caseName
                 << "'. Use IEEE14 | IEEE30 | IEEE57 | IEEE118" << endl;
        }
        MPI_Finalize();
        return 1;
    }

    if (nprocs != caseDesc->n_regions) {
        if (myrank == 0) {
            cerr << "Error: " << caseDesc->name << " requires "
                 << caseDesc->n_regions << " MPI ranks, got " << nprocs << endl;
        }
        MPI_Finalize();
        return 1;
    }

    double distrub = 0.1;
    PowerGridProtocol proto = power_grid_protocol(caseId);
    double gen_per_d = proto.gen_per_d;
    int eva_per_d = proto.eva_per_d;

    string optimizer_type = (argc >= 3) ? argv[2] : "LLSO";
    string outDir = (argc >= 4) ? string(argv[3]) : "./output/";
    if (!outDir.empty() && outDir.back() != '/') outDir += "/";

    string funcID = string("POWER") + string(caseDesc->name).substr(4);
    string exID   = "ex01";

    string filename = outDir + funcID + "_" + optimizer_type + "_" + exID + ".txt";

    double penalty_weight = 0;
    int swarm_size = 100;

    // 随机种子
    {
        const char* pair_seed = getenv("MACPO_PAIR_SEED");
        if (pair_seed != nullptr && pair_seed[0] != '\0') {
            unsigned long sd = strtoul(pair_seed, nullptr, 10);
            srand((unsigned)(sd & 0xffffffffu));
            if (myrank == 0) {
                cout << "[MACPO_power] MACPO_PAIR_SEED=" << sd << " (paired trace RNG)" << endl;
            }
        } else {
            srand(getCurrentTime());
        }
    }

    // 启动计时
    long t_start = getCurrentTime();

    // 写入表头（专利格式：通信触发率 / 最优目标 / 墙钟时间）
    if (myrank == 0) {
        ofstream outfile(filename);
        if (outfile.is_open()) {
            outfile << "# Algorithm: MACPO (baseline)" << endl;
            outfile << "# Scenario: " << caseDesc->label << endl;
            outfile << "# Optimizer: " << optimizer_type << endl;
            outfile << "# COLUMNS: iter eval f_penalty f_pure penalty "
                       "improvement comm_trigger wall_ms" << endl;
            outfile << setw(4)  << "iter"
                   << setw(12) << "eval"
                   << setw(12) << "f_penalty"
                   << setw(12) << "f_pure"
                   << setw(12) << "penalty"
                   << setw(12) << "improvement"
                   << setw(12) << "comm"
                   << setw(12) << "wall_ms" << endl;
            outfile.close();
        }
    }

    // ========================================================================
    // 核心变更: 用 PowerGridBenchmarks 替代 Benchmarks
    // ========================================================================
    PowerGridBenchmarks *pFunc = new PowerGridBenchmarks(caseId);
    int dimension = pFunc->getDimension();
    vector<int> groupDim = pFunc->getGroupDim(myrank);
    // 所有 rank 统一评估预算（R0 有 4 维, R1-R3 有 3 维，取最大保证同步退出）
    int my_dim = (int)groupDim.size();
    int max_dim = my_dim;
    MPI_Allreduce(&my_dim, &max_dim, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    pFunc->max_eva_times = eva_per_d * max_dim;

    int gen_times = std::max(2, (int)(groupDim.size() * gen_per_d));

    double *globalBest = new double[dimension];
    double *globalBestReport = new double[dimension];
    memset(globalBest, 0, sizeof(double) * dimension);
    power_grid_init_feasible(caseDesc, globalBest);

    // 组件注册（与原版完全一致，虚函数调度保证正确行为）
    evaluator *Evaluator = new evaluator_variable_wise_penalty(
        pFunc, myrank, penalty_weight, globalBest);
    optimizer *Optimizer = nullptr;
    if (optimizer_type == "CSO") {
        Optimizer = new optimizer_CSO(swarm_size, Evaluator, groupDim);
    } else {
        Optimizer = new optimizer_LLSO(swarm_size, Evaluator, groupDim);
    }
    competition *Competition = new competition_variable_independent_2(
        pFunc, &(Optimizer->swarm),
        ((evaluator_variable_wise_penalty*)Evaluator)->variable_switch);
    sharing *Sharing = new sharing_variable_wise(
        pFunc, ((competition_variable_wise*)Competition)->compete_result);

    Optimizer->init();
    power_grid_seed_swarm_from_feasible(Optimizer, globalBest, groupDim);

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
    double best_fitness = 1e300;
    double prev_global_fit = 1e10;
    int comm_trigger_loops = 0;

    int global_continue = 1;
    while (global_continue)
    {
        int success = 0;
        int gen_count = 0;
        for (int gen = 0; gen < gen_times; gen++)
        {
            Optimizer->generation(success);
            gen_count++;
            if (pFunc->reachMaxEva())
                break;
        }

        // 全体同步: 所有 rank 是否都达到 max_eva?
        int local_done = pFunc->reachMaxEva() ? 1 : 0;
        int all_done = 0;
        MPI_Allreduce(&local_done, &all_done, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
        if (all_done == 1) { global_continue = 0; break; }  // 全体完成，干净退出

        // 异步共享信息
        double *localBestPar = Optimizer->getBestPar();
        vector<double*> fitii, fitij;
        vector<double*> neighborVec;
        MPI_Request req[commu_object.size()];
        MPI_Request req2[commu_object.size()];
        MPI_Request req3[commu_object.size()];

        int rank_index = 0;
        for (int rank : commu_object)
        {
            MPI_Isend(localBestPar, dimension, MPI_DOUBLE, rank, 0, MPI_COMM_WORLD, &req[rank_index]);
            rank_index++;
        }

        rank_index = 0;
        for (int rank : commu_object)
        {
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
            rank_index++;
        }

        // ---- 协商阶段（内联 compete 逻辑，与原版 MACPO.cpp 一致） ----
        vector<double*> fit1p, fit1n;
        rank_index = 0;
        memcpy(globalBest, localBestPar, dimension * sizeof(double));

        MPI_Request req4[commu_object.size()];
        MPI_Request req5[commu_object.size()];

        for (int rank : commu_object)
        {
            int len = overlapDimForEach[rank_index].size();
            double *fji = new double[len];
            double *fjj = new double[len];
            MPI_Recv(fji, len, MPI_DOUBLE, rank, 1, MPI_COMM_WORLD, &stat);
            MPI_Recv(fjj, len, MPI_DOUBLE, rank, 2, MPI_COMM_WORLD, &stat);

            int hostID = myrank;
            double* fii = fitii[rank_index];
            double* fij = fitij[rank_index];

            for (int i = 0; i < len; i++) {
                int d = overlapDimForEach[rank_index][i];
                if (fii[i] + fji[i] > fij[i] + fjj[i]) {
                    ((competition_variable_independent_2*)Competition)->compete_result[d] = 1;
                    globalBest[d] = neighborVec[rank_index][d];
                } else {
                    ((competition_variable_independent_2*)Competition)->compete_result[d] = 0;
                }
            }

            int sharing_succ = 0;
            Sharing->share(Optimizer->swarm, swarm_size, globalBest,
                           myrank, rank, sharing_succ);

            double* f1p = new double[len];
            double* f1n = new double[len];
            for (int i = 0; i < len; i++) {
                int d = overlapDimForEach[rank_index][i];
                double dt = distrub;
                double* gb = globalBest;
                double localfit = pFunc->local_eva(gb, myrank);
                if (gb[d] + dt >= pFunc->getMaxX()) dt = pFunc->getMaxX() - gb[d];
                if (gb[d] - dt <= pFunc->getMinX()) dt = gb[d] - pFunc->getMinX();
                double ov = gb[d];
                gb[d] = std::min(ov + dt, pFunc->getMaxX());
                f1p[i] = pFunc->local_eva(gb, hostID) - localfit;
                gb[d] = std::max(ov - dt, pFunc->getMinX());
                f1n[i] = pFunc->local_eva(gb, hostID) - localfit;
                gb[d] = ov;
            }
            MPI_Isend(f1p, len, MPI_DOUBLE, rank, 3, MPI_COMM_WORLD, &req4[rank_index]);
            MPI_Isend(f1n, len, MPI_DOUBLE, rank, 4, MPI_COMM_WORLD, &req5[rank_index]);
            fit1p.push_back(f1p);
            fit1n.push_back(f1n);
            rank_index++;
        }

        // 接收扰动响应，更新 variable_switch
        rank_index = 0;
        for (int rank : commu_object)
        {
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
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] = 0;
                } else {
                    ((competition_variable_independent_2*)Competition)->variable_switch[d] =
                        ((competition_variable_independent_2*)Competition)->compete_result[d];
                }
            }
            delete[] f2p; delete[] f2n;
            rank_index++;
        }

        // 更新 evaluator 全局最优，重新评估种群
        if (dynamic_cast<evaluator_biasing_local_penalty*>(Evaluator) != nullptr) {
            ((evaluator_biasing_local_penalty*)Evaluator)->setGlobalBest(globalBest);
        }
        Optimizer->Evaluator->total_evaluate(Optimizer->swarm);
        sort(Optimizer->swarm.begin(), Optimizer->swarm.end(), cmp_unit_pointer);
        if (optimizer_type == "LLSO") {
            ((optimizer_LLSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        } else if (optimizer_type == "CSO") {
            ((optimizer_CSO*)Optimizer)->bestFit = Optimizer->swarm[0]->fitness;
        }

        // MPI_Waitall for pending requests
        MPI_Status Istats[commu_object.size()];
        MPI_Waitall(commu_object.size(), req, Istats);
        MPI_Waitall(commu_object.size(), req2, Istats);
        MPI_Waitall(commu_object.size(), req3, Istats);
        MPI_Waitall(commu_object.size(), req4, Istats);
        MPI_Waitall(commu_object.size(), req5, Istats);

        // ---- 记录（降频 assemble；不计入 eva 预算） ----
        bool need_report = (iter % kPowerGridReportInterval == 0);
        double f_pure = prev_global_fit;
        double f_penalty = f_pure;
        if (need_report) {
            f_pure = power_grid_report_pure(
                pFunc, myrank, globalBestReport, globalBest, groupDim, dimension);
            f_penalty = f_pure;
            best_fitness = std::min(best_fitness, f_pure);
        }
        comm_trigger_loops++;

        if (myrank == 0 && need_report) {
            double penalty = 0.0;
            double improvement = prev_global_fit - f_penalty;
            prev_global_fit = f_penalty;

            ofstream outfile(filename, ios::app);
            if (outfile.is_open()) {
                outfile << setw(4)  << iter
                       << setw(12) << pFunc->eva_count
                       << setw(12) << f_penalty
                       << setw(12) << f_pure
                       << setw(12) << penalty
                       << setw(12) << improvement
                       << setw(12) << 1
                       << setw(12) << (getCurrentTime() - t_start) << endl;
                outfile.close();
            }
        }

        // 清理
        for (auto p : fitii)  delete[] p;
        for (auto p : fitij)  delete[] p;
        for (auto p : fit1p)  delete[] p;
        for (auto p : fit1n)  delete[] p;
        for (auto p : neighborVec) delete[] p;
        fitii.clear();
        fitij.clear();
        fit1p.clear();
        fit1n.clear();
        neighborVec.clear();

        iter++;
    }

    double final_f = power_grid_report_pure(
        pFunc, myrank, globalBestReport, globalBest, groupDim, dimension);
    best_fitness = std::min(best_fitness, final_f);
    if (myrank == 0) {
        long wall_ms = getCurrentTime() - t_start;
        double comm_rate = (iter > 0) ? 1.0 : 0.0;
        cout << "[MACPO_power] Done. iter=" << iter
             << " eva=" << pFunc->eva_count
             << " best_f=" << best_fitness << endl;
        cout << "[RESULT] algorithm=MACPO f_pure=" << scientific << setprecision(6)
             << final_f << " best_f_pure=" << best_fitness
             << " eva=" << pFunc->eva_count
             << " wall_ms=" << wall_ms
             << " outer_iters=" << iter
             << " comm_triggers=" << comm_trigger_loops
             << " comm_rate=" << fixed << setprecision(4) << comm_rate << endl;
    }

    MPI_Finalize();
    return 0;
}

double global_average(double value, vector<int> neighbor_id)
{
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
