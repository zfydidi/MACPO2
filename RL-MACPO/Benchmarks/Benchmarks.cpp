#include <sstream>
#include <fstream>
#include <iostream>
#include<cstring>
#include<cmath>
#include<algorithm>
#include <random>
// #include<regex>
#include "Benchmarks.h"
#include "BaseFunction.h"
using namespace std;
using json = nlohmann::json;

// 日志记录函数：将日志字符串写入指定文件
void log_str(string str, int rank){
    string log_filename = "../log/rank"+to_string(rank)+".txt";
    fstream ft(log_filename, ios::out);
    ft<<str<<endl;
    ft.close();
}

// 随机打乱两个数组的顺序，保证两个数组的对应关系
void shuffleArrays(double* array1, double* array2, int length) {
    // Create a vector of indices from 0 to length-1
    //创建一个从 0 到 length-1 的索引数组
    std::vector<int> indices(length);
    for (int i = 0; i < length; ++i) {
        indices[i] = i;
    }

    // Create a random number generator
    // 创建随机数生成器
    std::random_device rd;
    std::mt19937 gen(rd());

    // Shuffle the indices
    // 随机打乱索引顺序
    std::shuffle(indices.begin(), indices.end(), gen);

    // Create temporary arrays to hold the shuffled values
    // 临时存储打乱后的数组值
    std::vector<double> tempArray1(length);
    std::vector<double> tempArray2(length);

    // Reorder the original arrays based on the shuffled indices
    // 根据打乱的索引重排原数组
    for (int i = 0; i < length; ++i) {
        tempArray1[i] = array1[indices[i]];
        tempArray2[i] = array2[indices[i]];
    }

    // Copy the shuffled values back to the original arrays
    // 将打乱的值复制回原数组
    for (int i = 0; i < length; ++i) {
        array1[i] = tempArray1[i];
        array2[i] = tempArray2[i];
    }
}
/**
 * @brief Benchmarks 类的构造函数。
 * @param ID 基准函数的标识符（例如 "F1"、"F2"）。
 * @param max_eva_times 最大评估次数。
 * @param overlap 共享变量（分组）。
 *
 * 初始化基准函数，读取配置文件，设置相关参数，读取维度数据，加载旋转矩阵、分组数据和最优值等信息。
 */
// 构造函数：初始化Benchmarks类的成员变量
Benchmarks::Benchmarks(string ID,int max_eva_times,bool overlap){
    
    string config_path = "./Benchmarks/default_config.json";
    string data_path = "./Benchmarks/data/";
    this->funcID = ID;

    json config;
    std::ifstream config_file(config_path);
    if (!config_file.is_open()) {
        std::cerr << "Error: Could not open config file: " << config_path << std::endl;
        exit(1);
    }
    config_file >> config;

    // 初始化各个配置参数
    this->func_config = config["benchmarks"][ID];
    this->group_num = func_config["group_num"];

    this->max_eva_times = max_eva_times;
    this->eva_count = 0;
    this->reach_max_eva_times = false;
    this->overlap_grouping = overlap;

    this->if_rotate = true;
    this->if_shift = false;
    this->if_heterogeneous = false;
    this->scaling_factor = 1;


    // 读取维度数据,并将取值范围由1-1000变为0-999
    group = read_data<int>(data_path+"group_"+ID+".txt");
    for (int i = 0; i < group_num; i++) {
        int size =func_config["subproblems"][i]["dimension"];
        for (int j = 0; j < size; j++) {
            group[i][j] -= 1;
        }
    }
    
    // 读取最优值数据
    xopt = read_data<double>(data_path+"xopt_"+ID+".txt");

    // 读取是否为旋转矩阵
    try
    {
        if_rotate = func_config["if_rotate"];
        if(if_rotate==false){
            return;
        }
    }
    catch(...)
    {
    }
    
    // 读取旋转矩阵
    // 初始化旋转矩阵R
    R = new double**[group_num];
    double** testPtr = read_data<double>(data_path+"R"+to_string(1)+"_"+ID+".txt");
    if(testPtr == nullptr){
        // double** R100 = read_data<double>(data_path+ "R100_"+ID+".txt");
        // double** R250 = read_data<double>(data_path+ "R250_"+ID+".txt");
        // double** R500 = read_data<double>(data_path+ "R500_"+ID+".txt");
        
        // for(int i=0;i<group_num;i++){
        //     if(func_config["subproblems"][i]["dimension"] == 100)
        //         R[i] = R100;
        //     else if(func_config["subproblems"][i]["dimension"] == 250)
        //         R[i] = R250;
        //     else if(func_config["subproblems"][i]["dimension"] == 500)
        //         R[i] = R500;
        // }
        for(int i=0;i<group_num;i++){
            string d = to_string(func_config["subproblems"][i]["dimension"]);
            R[i] = read_data<double>(data_path+ "R"+d+"_"+ID+".txt");
        }
    }else{
        for(int i=0;i<group_num;i++){
            R[i] = read_data<double>(data_path+"R"+to_string(i+1)+"_"+ID+".txt");
        }
    }

}

/**
 * @brief Benchmarks 类的析构函数。
 *
 * 释放动态分配的内存，包括分组数据、最优值和旋转矩阵，以避免内存泄漏。
 */
// 析构函数：释放动态分配的内存，避免内存泄漏
Benchmarks::~Benchmarks() {
    vector<double**> trash;
    for (int i = 0; i < group_num; i++) {
        delete[] group[i];
        delete[] xopt[i];
        int size = func_config["subproblems"][i]["dimension"];
        if(if_rotate == true){
            if(find(trash.begin(),trash.end(),R[i]) == trash.end()){
                for(int j=0;j<size;j++){
                    delete[] R[i][j];
                }
                delete[] R[i];
                trash.push_back(R[i]);
            }
        }
    }
    delete[] group;
    delete[] xopt;
    
    if(if_rotate == true)
        delete[] R;
    
}

/**
 * @brief 检查是否已达到最大评估次数。
 * @return 如果达到最大评估次数，返回 true；否则返回 false。
 */
// 判断是否达到最大评估次数
bool Benchmarks::reachMaxEva(){
    if(eva_count>=max_eva_times){
        if(!reach_max_eva_times){
            // cout<<"The time of evaluation has reached the maximum bound. Later evaluation results would not be recorded.\n"; 
            reach_max_eva_times = true;
        }
        return true;
    }
    return false;
}

/**
 * @brief 评估指定agent下特定一组解的局部适应度。
 * @param x 解向量。
 * @param groupIndex 指定一组解的索引（组号）。
 * @return 给指定agent下一组解的适应度值。
 */
// 局部评估函数，计算指定分组的适应度
double Benchmarks::local_eva(double* x, int groupIndex) {
    if (groupIndex < 0 || groupIndex >= group_num) {
		cout << "groupIndex error\n";
		return 0;
	}
    int len = func_config["subproblems"][groupIndex]["dimension"];
    double ub = func_config["upper_bound"];
    double lb = func_config["lower_bound"];

    double res = 0;
    string funcType = func_config["subproblems"][groupIndex]["base_function"];
    double *shftx;
    double *rotate_x;

    // 计算移位后的值
    shftx = new double[len];
    for (int j = 0; j < len; j++) {
        int index = group[groupIndex][j];
        if (x[index] > ub || x[index] < lb) {
            cout << "solution out of range;" << endl;
            return 0;
        }
        shftx[j] = x[index] - xopt[groupIndex][j];
    }

    // 根据旋转配置决定是否旋转
    if(if_rotate==true)
        rotate_x = multiply(shftx, R[groupIndex], len);
    else
        rotate_x = shftx;

    // 根据函数类型计算适应度
    if(funcType=="elliptic"){
        res = elliptic(rotate_x, len);
    }
    else if(funcType=="rastrigin"){
        res = rastrigin(rotate_x, len);
    }
    else if(funcType=="schwefel"){
        res = schwefel(rotate_x, len);
    }
    else if(funcType=="ackley"){
        res = ackley(rotate_x, len);
    }
    else if(funcType=="rosenbrock"){
        res = rosenbrock(rotate_x, len);
    }
    else if(funcType=="griewank"){
        res = griewank(rotate_x, len);
    }


	delete[] shftx;
    if(if_rotate)
    	delete[] rotate_x;

    eva_count += 1;

    return res;

}

/**
 * @brief 评估解的全局适应度（对agent的所有解进行评估）。
 * @param x 解向量。
 * @return 解的全局适应度值。
 */
// 全局评估函数，汇总所有分组的局部评估结果
double Benchmarks::global_eva(double* x) {
	double res = 0;
    for(int i=0;i<group_num;i++){
        double r = local_eva(x,i);
        res += r;
    }
	return res;
}

// 获取分组的局部最优值
double Benchmarks::getLocalOpt(int groupIndex){
    double fopt = 0;
    try{
        fopt = func_config["subproblems"][groupIndex]["fopt"];
    }catch(...){
    }
    
    return fopt;

}

/**
 * @brief 获取允许的最低取值。
 * @return 返回当前基准问题允许的解向量的最低边界值。
 */
// 获取允许的最低取值
double Benchmarks::getMinX() {
	return func_config["lower_bound"];
}

/**
 * @brief 获取允许的最高取值。
 * @return 返回当前基准问题允许的解向量的最高边界值。
 */
// 获取允许的最高取值
double Benchmarks::getMaxX() {
	return func_config["upper_bound"];
}

/**
 * @brief 获取分组数量。
 * @return 返回当前基准问题中的分组数量（子问题的个数）。
 */
// 获取分组数量
int Benchmarks::getGroupNum() {
	return func_config["group_num"];
}

/**
 * @brief 获取问题的总维度。
 * @return 返回当前基准问题的全局维度（解向量的长度）。
 */
// 获取问题维度
int Benchmarks::getDimension(){
    return func_config["dimension"];
}

/**
 * @brief 从指定文件读取数据并返回二维数组。
 * @tparam T 读取的数据类型（例如 `int`、`double`）。
 * @param fileName 数据文件的路径。
 * @return 返回一个动态分配的二维数组，包含从文件读取的数据。
 */
// 从指定文件读取数据并存储为二维数组
template<typename T>
T** Benchmarks::read_data(string fileName) {
	// cout << fileName<<endl;
    T** res = nullptr;
    ifstream file(fileName);

    // 打开文件并读取数据到data二维向量中
	if (file.is_open()) {
		// cout << " is opened;\n";
        vector<vector<T>> data;
		string line;
        while(getline(file,line)){
    // cout<<"1"<<endl;
            stringstream ss(line);
            vector<T> rowData;
            T x;
            while(ss>>x){
                rowData.push_back(x);
            }
            data.push_back(rowData);
        }
		file.close();
    // cout<<"1"<<endl;

        // 将data vector内容转存为二维数组格式并返回
        res = new T*[data.size()];
        int count = 0;
        for(auto rowData:data){
    // cout<<"1"<<endl;
            // cout<<rowData.size()<<endl;
            T* row = new T[rowData.size()];
            memcpy(row,&rowData[0],rowData.size()*sizeof(T));
            res[count]=row;
            count++;
        }
	}
	else {
		// cout << " can not be opened;\n";
	}
	return res;
}

/**
 * @brief 获取指定两个分组的重叠维度（共享变量）。
 * @param g1 第一个分组的索引。
 * @param g2 第二个分组的索引。
 * @return 返回一个包含两个分组重叠维度（共享变量）的向量。
 *
 * 通过计算两个分组维度的交集，确定它们之间的重叠变量索引。
 */
// 获取指定两个分组的重叠维度
vector<int> Benchmarks::getOverlapDim(int g1,int g2){
    vector<int> dim1 = getGroupDim(g1);
    vector<int> dim2 = getGroupDim(g2);
    vector<int> overlap;
    sort(dim1.begin(),dim1.end());
    sort(dim2.begin(),dim2.end());

    // 获取dim1和dim2的交集，表示重叠维度
    set_intersection(dim1.begin(),dim1.end(),dim2.begin(),dim2.end(),back_inserter(overlap));
    return overlap;
}

// 获取分组重叠维度的索引（g1中重叠部分在自身中的索引位置）
vector<int> Benchmarks::getOverlapDimIndex(int g1,int g2){
    vector<int> overlap = getOverlapDim(g1,g2);
    vector<int> groupDim = getGroupDim(g1);
    vector<int> dimIndex;
    dimIndex.resize(overlap.size());
    for(unsigned int i=0;i<overlap.size();i++){
        for(unsigned int j=0;j<groupDim.size();j++){
            if(overlap[i] == groupDim[j]){
                dimIndex[i] = j;
                break;
            }
        }
    }
    return dimIndex;
}

/**
 * @brief 获取指定分组的维度索引向量。
 * @param groupIndex 目标分组的索引。
 * @return 返回包含目标分组维度的索引向量。
 *
 * 根据是否使用重叠分组策略，分别处理获取当前分组的维度索引。
 */
vector<int> Benchmarks::getGroupDim(int groupIndex){
    // 检查当前是否使用重叠分组策略
    if(this->overlap_grouping){
        // 获取当前分组的维度大小
        int size = func_config["subproblems"][groupIndex]["dimension"];
        // 构造目标分组的维度索引向量
        // 使用 group[groupIndex] 作为起点，连续提取 size 个元素
        vector<int> v(group[groupIndex],group[groupIndex]+size);
        // 直接返回维度索引向量
        return v;
    }else{
        // 如果未使用重叠分组策略
        // 获取当前分组的维度大小
        int size = func_config["subproblems"][groupIndex]["dimension"];
        // 构造目标分组的维度索引向量
        vector<int> v(group[groupIndex],group[groupIndex]+size);
        // 获取当前分组的所有重叠分组
        vector<int> overlap = getOverlapGroup(groupIndex);

        // 遍历所有与当前分组重叠的分组
        for(int g:overlap){
            // 仅处理索引小于当前分组的重叠分组，避免重复操作
            if(g<groupIndex){
                // 获取重叠分组的维度大小
                int s = func_config["subproblems"][g]["dimension"];
                // 构造重叠分组的维度索引向量
                vector<int> neighbor(group[g],group[g]+s);
                // 从当前分组维度索引向量中移除与重叠分组重复的索引
                for(vector<int>::iterator it = v.begin();it!=v.end();){
                    // 检查当前维度索引是否存在于重叠分组中
                    if(find(neighbor.begin(),neighbor.end(),*it)!=neighbor.end()){
                        // 如果存在，移除该索引
                        it = v.erase(it);
                    }else{
                        // 如果不存在，继续检查下一个索引
                        it++;
                    }
                }
            }
        }
        return v;
    }
}

// 获取当前分组中不与其他分组重叠的维度
vector<int> Benchmarks::getGroupExcluDim(int groupIndex){
    int size = func_config["subproblems"][groupIndex]["dimension"];
    vector<int> v(group[groupIndex],group[groupIndex]+size);
    vector<int> overlap = getOverlapGroup(groupIndex);
    for(int g:overlap){
        int s = func_config["subproblems"][g]["dimension"];
        vector<int> neighbor(group[g],group[g]+s);
        for(vector<int>::iterator it = v.begin();it!=v.end();){
            if(find(neighbor.begin(),neighbor.end(),*it)!=neighbor.end()){
                it = v.erase(it);
            }else{
                it++;
            }
        }
    }
    return v;
}

/**
 * @brief 获取当前分组的重叠分组索引。
 * @param groupIndex 当前分组的索引。
 * @return 返回一个包含与当前分组有重叠关系的分组索引的向量。
 *
 * 通过判断当前分组与其他分组的重叠关系，返回所有重叠分组的索引。
 */
// 获取当前分组的重叠分组索引
vector<int> Benchmarks::getOverlapGroup(int groupIndex){
    vector<int> groups;
    if(W){
        for(int i=0;i<group_num;i++){
            if(i == groupIndex)
                continue;
            if(W[groupIndex][i]>0)
                groups.push_back(i);
        }
    }else{
        vector<int> overlap = func_config["subproblems"][groupIndex]["overlap"];
        for(int i=0;i<group_num;i++){
            if(i == groupIndex)
                continue;
            if(overlap[i]>0)
                groups.push_back(i);
        }
    }
    return groups;
}

// 获取分组间的网络图，如果W还未定义则读取文件内容初始化
double** Benchmarks::getNetworkGraph(){
    if(W==nullptr){
        string data_path = "./Benchmarks/data/";
        W=read_data<double>(data_path+"W_"+funcID);
    }
    return W;
}