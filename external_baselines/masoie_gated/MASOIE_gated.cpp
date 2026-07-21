/*
Conflict-gated MASOIE (A2): attach the paper's three-layer conflict gate to a
STRUCTURALLY DIFFERENT negotiation paradigm than MACPO.

Baseline MASOIE (T.-Y. Chen et al., IEEE TEVC 2024, doi:10.1109/TEVC.2024.3380436)
negotiates on EVERY outer loop: each loop it exchanges subswarms with neighbors
and performs an "external learning" consensus pull
    external_swarm_v += (nei_buffer_k - swarm_x) * w_k .
This file inserts the conflict gate (Eq. local_gate of conference_new_ready.tex)
BEFORE that exchange+external-learning block, so negotiation happens only when the
local conflict index CI exceeds a phase-relative threshold or a fail-safe fires.

Deadlock-free design: MASOIE's original per-agent asynchronous termination (tag 5)
cannot coexist with a global gate, so we run a GLOBAL LOCKSTEP gate. Every outer
loop each agent contributes one MPI_Allreduce:
  * gate  = MAX_i(local_want)        -> communicate iff ANY agent requests (g_global = max_i g_i)
  * done  = MIN_i(local_reachMaxEva) -> all agents terminate together
Communication (send/recv + external learning) runs only when g_global = 1; all
agents are in the same branch, so no rank ever blocks on a message that is not sent.

Gate parameters are read from env (defaults match the paper): MASOIE_LAMBDA (lambda),
MASOIE_K (fail-safe), MASOIE_DMIN (min interval), MASOIE_GAMMA (CI EMA), MASOIE_BETA
(per-dim gap EMA). Set MASOIE_LAMBDA to a huge value to recover always-on behavior
(the gate then fires every loop via the relative threshold being trivially met only
through fail-safe K=1); prefer the separate original binary for the always-on baseline.
*/
#include "framework.h"
#include "internal_optimizer.h"
#include <mpi.h>
#include <iostream>
#include <cstdlib>
#include <cfloat>
#include <Eigen/Dense>
using namespace std;
using namespace Eigen;

// parameter setting (identical to baseline MASOIE)
int swarmSize = 300;
int interval = 4;
int no_improve_tolerant = 10;
double termination_threshold = 1E-5;

static double envd(const char* k, double d) { const char* v = getenv(k); return v ? atof(v) : d; }
static int    envi(const char* k, int d)    { const char* v = getenv(k); return v ? atoi(v) : d; }

void agent_function(Framework* handler) {
    int dim = handler->get_problem_dim();
    double lb = handler->get_lower_bound();
    double ub = handler->get_upper_bound();
    double R = (ub - lb) > 0 ? (ub - lb) : 1.0;   // search range for gap normalization
    vector<int> nei_list = handler->get_neighbor_id();
    vector<double> nei_weight = handler->get_adjacent_weights();
    int nei_num = nei_list.size();
    int self_id = handler->get_self_id();

    // three-layer gate parameters (defaults align with conference_new_ready.tex)
    double lam_thr = envd("MASOIE_LAMBDA", 1.2);
    int    K       = envi("MASOIE_K", 10);
    int    dmin    = envi("MASOIE_DMIN", 1);
    double gamma   = envd("MASOIE_GAMMA", 0.8);
    double beta    = envd("MASOIE_BETA", 0.5);

    // population initialization
    MatrixXd swarm_x = (MatrixXd::Random(swarmSize, dim).array() / 2 + 0.5).array() * (ub - lb) + lb;
    MatrixXd external_swarm_v = MatrixXd::Zero(swarmSize, dim);
    VectorXd swarm_fit = VectorXd::Zero(swarmSize);
    for (int j = 0; j < swarmSize; j++) {
        VectorXd inv = swarm_x.row(j);
        swarm_fit(j) = handler->local_evaluation(inv.data());
    }
    LLSO* internal_opt = new LLSO();
    internal_opt->bestFit = swarm_fit.minCoeff();

    vector<MatrixXd> nei_buffers(nei_num, MatrixXd::Zero(swarmSize, dim));

    // gate state (Eq. ci_dim / ci_ema)
    VectorXd delta = VectorXd::Zero(dim);   // per-dim smoothed normalized gap
    double mu = -1.0;                        // phase-relative EMA baseline (uninitialized)
    int t_last = -1000000000;                // forces communication on the first loop (fail-safe)
    VectorXd r_ref = swarm_x.colwise().mean().transpose();  // consensus reference

    double best_inv_fit = DBL_MAX;
    int no_improve_count = 0;
    long comm_rounds = 0, total_rounds = 0;

    for (int iter = 0; ; iter++) {
        // ---- internal learning (unchanged) ----
        MatrixXd swarm_v = external_swarm_v.array();
        for (int i = 0; i < interval; i++) {
            internal_opt->step(&swarm_x, &swarm_v, swarm_fit);
            swarm_x = swarm_x.cwiseMin(ub).cwiseMax(lb);
            for (int j = 0; j < swarmSize; j++) {
                VectorXd inv = swarm_x.row(j);
                swarm_fit(j) = handler->local_evaluation(inv.data());
            }
            internal_opt->update_performance(swarm_fit);
        }

        // ---- conflict index CI (Eq. ci_dim, ci_agent) ----
        VectorXd x_mean = swarm_x.colwise().mean().transpose();
        VectorXd e = (x_mean - r_ref).cwiseAbs() / R;         // e_d = |x_d - r_d| / R_d
        delta = beta * delta + (1 - beta) * e;                // smoothed gap
        double CI = delta.mean();
        if (mu < 0) mu = CI; else mu = gamma * mu + (1 - gamma) * CI;  // phase-relative baseline

        // ---- three-layer local gate (Eq. local_gate; phase layer disabled, p_phase=1) ----
        bool c_int = (iter - t_last) >= dmin;                             // Layer 1: min interval
        bool c_thr = (CI > lam_thr * mu) || ((iter - t_last) >= K);       // Layer 2: rel-thr or fail-safe
        int local_want = (c_int && c_thr) ? 1 : 0;

        // ---- global gate + global termination (deadlock-free lockstep) ----
        int g_global = 0;
        MPI_Allreduce(&local_want, &g_global, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);  // g_global = max_i g_i
        int local_done = handler->reachMaxEva() ? 1 : 0;
        int all_done = 0;
        MPI_Allreduce(&local_done, &all_done, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);  // stop when all done
        total_rounds++;
        if (all_done) break;

        if (g_global) {
            comm_rounds++;
            // exchange subswarms: every agent is in this branch -> no deadlock
            double* trans = swarm_x.data();
            MPI_Request* sreq = new MPI_Request[nei_num];
            for (int k = 0; k < nei_num; k++)
                handler->Message_Isend(trans, swarmSize * dim, MPI_DOUBLE, nei_list[k], 1, &sreq[k]);
            for (int k = 0; k < nei_num; k++) {
                MPI_Status st;
                handler->Message_Recv(nei_buffers[k].data(), swarmSize * dim, MPI_DOUBLE, nei_list[k], 1, &st);
            }
            if (nei_num > 0) MPI_Waitall(nei_num, sreq, MPI_STATUSES_IGNORE);
            delete[] sreq;

            // external learning (the negotiation / consensus pull)
            MatrixXd randmtx = (MatrixXd::Random(swarmSize, 1).array() / 2 + 0.5).replicate(1, dim);
            external_swarm_v = external_swarm_v.cwiseProduct(randmtx);
            for (int k = 0; k < nei_num; k++)
                external_swarm_v += (nei_buffers[k] - swarm_x) * nei_weight[k];
            swarm_x += external_swarm_v;
            swarm_x = swarm_x.cwiseMin(ub).cwiseMax(lb);
            for (int j = 0; j < swarmSize; j++) {
                VectorXd inv = swarm_x.row(j);
                swarm_fit(j) = handler->local_evaluation(inv.data());
            }

            // refresh consensus reference from freshly received neighbor means
            VectorXd rsum = VectorXd::Zero(dim);
            for (int k = 0; k < nei_num; k++)
                rsum += nei_buffers[k].colwise().mean().transpose();
            r_ref = (nei_num > 0) ? (rsum / nei_num).eval() : x_mean;
            t_last = iter;
        }
        // else: skip negotiation, keep stale r_ref (paper's skip branch)

        // ---- adaptive communication interval (unchanged) ----
        double curmin = swarm_fit.minCoeff();
        if (curmin < best_inv_fit) { best_inv_fit = curmin; no_improve_count = 0; }
        else no_improve_count++;
        if (no_improve_count > no_improve_tolerant && interval > 2) {
            interval -= 1; no_improve_count = 0; best_inv_fit = curmin;
        }
    }

    VectorXd final_x = swarm_x.colwise().mean();
    handler->submit_final_solution(final_x.data());
    if (self_id == 0) {
        double tr = total_rounds > 0 ? (double)comm_rounds / total_rounds : 0.0;
        fprintf(stderr, "gate: [trigger_rate:%.4f, comm_rounds:%ld, total_rounds:%ld, lambda:%.2f, K:%d]\n",
                tr, comm_rounds, total_rounds, lam_thr, K);
    }
    return;
}
