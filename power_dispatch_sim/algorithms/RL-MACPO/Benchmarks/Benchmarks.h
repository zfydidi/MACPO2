#ifndef BENCHMARKS_H
#define BENCHMARKS_H

#include <string>
#include <vector>
#include "../util/json.hpp"
using json = nlohmann::json;
using std::string;
using std::vector;

class Benchmarks {
protected:
    // 空构造函数，供子类（如 PowerGridBenchmarks）使用，跳过文件读取
    Benchmarks() : group_num(0), if_rotate(false), if_shift(false),
                   group(nullptr), xopt(nullptr), R(nullptr), W(nullptr),
                   overlap_grouping(true) {}

    // 子类可访问的成员
    int group_num;
    int **group;
    double ***R, **xopt;
    double **R_global, **A, **W;
    bool if_rotate;
    bool if_shift;
    bool overlap_grouping;

private:
    json func_config;
    string funcID;
    template<typename T>T** read_data(string);

    double local_eva_for_global_solution(double*, int);
    double local_eva_type1(double* x, int groupIndex);
    double scaling_factor;
    double local_eva_type2(double* x, int groupIndex);
    double global_eva_type2(double* x);
    double local_eva_type3(double* x,int groupIndex);
    int funcClass;
    double weight;
    bool if_heterogeneous;
    double local_eva_type4(double* x,int groupIndex);
    int target_num;
    int source_num;
    int coordinate_dim;
    double **target, **source, **noisy_dis = nullptr;
    double **noisy_elevation = nullptr, **noisy_azimuth = nullptr;
    double local_eva_type5(double* x,int groupIndex);
    bool dfs(int x);
    double KM();
    int **match_truth;
    double **w;
    double *Lx,*Ly;
    bool *VisX,*VisY;
    int *MatchY;
    double* Slack;

public:
    int max_eva_times;
    int eva_count;
    bool reach_max_eva_times;
    Benchmarks(string ID,int max_eva_times = 3000000, bool = true);
    virtual ~Benchmarks();
    virtual double global_eva(double* x);
    /** 纯目标值，默认不计入 eva_count（配对实验记录用） */
    virtual double global_fitness(double* x) { return global_eva(x); }
    virtual double local_eva(double* x, int groupIndex);
    virtual double getMinX();
    virtual double getMaxX();
    virtual int getGroupNum();
    virtual int getDimension();
    virtual vector<int> getOverlapDim(int g1,int g2);
    virtual vector<int> getOverlapDimIndex(int g1,int g2);
    virtual vector<int> getGroupDim(int g);
    virtual vector<int> getGroupExcluDim(int groupIndex);
    virtual vector<int> getOverlapGroup(int g);
    virtual double getBestFitness() { return 0.0; }
    virtual bool reachMaxEva();
    double getLocalOpt(int groupIndex);
    double** getNetworkGraph();
    double getMatchRes(double* x);
    double getRMSE(double* x);
    void reload_target_pos(string, string);
    void reload_track_data(string target_fname, string source_fname, string network_fname, string measurement_fname, string = "");
    void change_target_num(int);
};

#endif
