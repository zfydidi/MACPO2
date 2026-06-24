#ifndef STRUCT_H
#define STRUCT_H

#include <string.h>
#include <vector>
#include <algorithm>
#include <cfloat>

// 定义单个个体的结构体，用于存储个体的解向量及适应度
struct unit
{
    double *X;     // 决策变量集合：该代理的解向量，包括私有和共享的决策变量，构成NDO的全局变量
    double fitness;  // 适应度值：该代理在当前局部目标函数f下的目标评估值

    // 构造函数，初始化代理的解和适应度值
    unit(double *globalBest, int dimension)
    {
        X = new double[dimension];// 为解向量分配动态内存（数组）
        memcpy(X, globalBest, sizeof(double) * dimension);   // 用全局最优解初始化决策变量集合X
        fitness = DBL_MAX;  // 初始适应度设为极大值，以便后续优化
    }

    // 重载运算符<，基于适应度值比较代理，用于排序
    bool operator<(const unit &y) const
    {
        return fitness < y.fitness;
    }

    // 重载运算符>，基于适应度值比较代理，用于排序
    bool operator>(const unit &y) const
    {
        return fitness > y.fitness;
    }

    // 析构函数，释放动态分配的解向量内存
    ~unit(){
        // cout<<"destruction of unit object\n";
        delete[] X;
    }
};

// 静态函数：用于排序的比较函数，基于适应度值的升序排列
static inline bool cmp_unit_pointer(unit* a, unit* b){
    return a->fitness < b->fitness;
}

// 节点结构体(particle)：继承自`unit`
struct particle : unit
{
    double *v;// 定义一个指向 double 类型数组的指针，用于存储速度
    particle(double *globalBest, int dimension) : unit(globalBest, dimension)//初始化粒子（节点）的局部最优值和维度
    {
        v = new double[dimension]; // 为速度数组分配内存，大小为维度
        memset(v, 0, sizeof(double) * dimension); // 初始化速度数组为 0
    }
    ~particle(){
        // cout<<"destruction of particle object\n";
        delete[] v;// 释放速度数组所占的内存
    }
};

// 标准化函数：对数组进行标准化（均值为0，标准差为1）
inline void standardization(double* arr, int size){
    double std = 0;
    double mean = 0;

    // 计算均值
    for(int i=0;i<size;i++){
        mean += arr[i];
    }
    mean = mean/size;

    // 计算标准差
    for(int i=0;i<size;i++){
        std += (arr[i]-mean)*(arr[i]-mean);
    }
    std = sqrt(std/size);

    // 标准化：每个元素减去均值，除以标准差
    for(int i=0;i<size;i++){
        if(std == 0)
            arr[i] = 0;// 防止除以零
        else
            arr[i] = (arr[i]-mean)/std;// 标准化公式
    }

    return;
}

// 计算标准差和均值的函数
inline void getStd(double* arr, int size, double &std, double &mean){
    std = 0;
    mean = 0;

    // 计算均值
    for(int i=0;i<size;i++){
        mean += arr[i];
    }
    mean = mean/size;

    // 计算标准差
    for(int i=0;i<size;i++){
        std += (arr[i]-mean)*(arr[i]-mean);
    }
    std = sqrt(std/size);

    return;
}

// 获取特定维度的群体均值
inline double* getMean(std::vector<unit*>& swarm, std::vector<int> groupDim){
    int dim_size = groupDim.size();  // 维度数量
    int swarm_size = swarm.size();  // 群体大小
    double* mean = new double[dim_size]{0};  // 初始化均值数组为0

    // 计算每个维度的均值
    for(int j=0;j<dim_size;j++){
        for(int i=0;i<swarm_size;i++){
            mean[j] += swarm[i]->X[groupDim[j]]; // 累加每个个体在该维度的值
        }
        mean[j] /= swarm_size; // 求均值
    }
    delete[] mean; // 释放内存
    return mean;// 返回均值
}

// 计算数组的均值
inline double getArrMean(double* arr, int size){
    double res = 0;
    for(int i=0;i<size;i++){
        res += arr[i];  // 累加数组元素
    }
    return res/size;  // 返回均值
}

/**
 * @brief 对数组进行归一化操作，将值缩放到 [0, 1] 范围内
 *
 * @param arr 数组
 * @param size 数组大小
 */
// 对数组进行归一化操作（范围：[0, 1]）
/***具体步骤**：

1. **查找最小值和最大值**：首先遍历数组，找到数组中的最小值和最大值。通过更新 `x_min_index` 和 `x_max_index` 来保存最小值和最大值的索引。

2. **归一化**：使用公式对数组中的每个元素进行归一化。如果数组中所有元素相同，避免除以零的错误，将该元素归一化为 0。

**例子**：

假设有一个数组 `arr`：
double arr[] = {3, 5, 8, 2, 7};
int size = 5;

执行归一化操作后，步骤如下：

1. 找到最小值 2 和最大值 8。
2. 使用归一化公式计算每个元素的归一化值

归一化后的数组 `arr` 变为：
arr = {0.167, 0.5, 1, 0, 0.833}

通过这个例子，你可以看到数组的值被缩放到了 [0, 1] 范围内。*/
inline void normalize(double* arr, int size){
    int x_min_index = 0;
    int x_max_index = 0;

    // 查找最小值和最大值的索引
    for(int i=0;i<size;i++){
        if(arr[i] < arr[x_min_index])
            x_min_index = i;
        else if(arr[i] > arr[x_max_index])
            x_max_index = i;
    }

    // 进行归一化
    for(int i=0;i<size;i++){
        if( (arr[x_max_index]-arr[x_min_index])==0 )// 如果数组中所有元素相同，避免除以零的错误，将该元素归一化为 0。
            arr[i] = 0;
        else
            arr[i] = (arr[i]-arr[x_min_index])/(arr[x_max_index]-arr[x_min_index]);// 归一化公式
    }

    return;
}

// 计算群体的标准差
inline double diversity_compute(std::vector<unit*>& swarm, std::vector<int> groupDim){
    int num = swarm.size(); // 群体大小
    int size = groupDim.size(); // 维度大小
    double** swarm_data = new double*[num]; // 存储每个个体的决策变量
    double* mean_vector = new double[size]{0}; // 初始化均值向量为0

    // 累加所有个体的决策变量
    for(int i=0;i<num;i++){
        swarm_data[i] = new double[size];
        for(int j=0;j<size;j++){
            swarm_data[i][j] = swarm[i]->X[groupDim[j]];// 获取个体的特定维度值
            mean_vector[j]+=swarm_data[i][j];// 累加
        }
    }
    //计算均值
    for(int i=0;i<size;i++)
        mean_vector[i] /= num;
    //计算标准差
    double std=0;
    for(int i=0;i<num;i++){
        double dis = 0;
        for(int j=0;j<size;j++){
            dis += (swarm_data[i][j]-mean_vector[j])*(swarm_data[i][j]-mean_vector[j]);
        }
        std +=sqrt(dis);// 累加每个个体的标准差
    }
    std /= num;// 求平均标准差
    delete[] mean_vector;// 释放内存
    for(int i=0;i<num;i++){
        delete[] swarm_data[i];// 释放每个个体的内存
    }
    delete[] swarm_data;// 释放二维数组内存
    return std;// 返回计算出的标准差
}

/**
 * @brief 计算数组的多样性，基于标准差衡量分散程度
 *
 * @param arr 二维数组，表示多个个体的决策变量
 * @param row 行数（个体数量）
 * @param col 列数（决策变量数量）
 * @return double 返回数组的多样性（标准差）
 */
inline double diversity_compute_array(double** arr, int row, int col){
    // 初始化均值向量
    double* mean_vector = new double[col]{0};

    // 计算每列（维度）的均值
    for(int i=0;i<row;i++){
        for(int j=0;j<col;j++){
            mean_vector[j]+=arr[i][j];
        }
    }

    for(int i=0;i<col;i++)
        mean_vector[i] /= row;//均值

    //计算标准差，衡量数据的分散度
    double std=0;
    for(int i=0;i<row;i++){
        double dis = 0;
        for(int j=0;j<col;j++){
            dis += (arr[i][j]-mean_vector[j])*(arr[i][j]-mean_vector[j]);
        }
        std +=sqrt(dis);// 求解欧几里得距离
    }
    std /= row;  // 平均标准差

    delete[] mean_vector;// 释放均值向量内存
    return std;// 返回标准差作为多样性度量
}

/**计算一组矩阵的多样性，遍历多个矩阵并计算每个的标准差
 输入：nabla：一个二维矩阵的向量，表示多个解向量的集合；pop：解向量的数量；row：每个解的维度；col：解向量的维度
 输出：多个解向量的标准差的均值，表示总体的多样性**/
inline double diversity_compute_nabla(std::vector<double**> nabla, int pop, int row, int col){
    double mean_std=0;

    // 遍历每个解向量集合并计算它们的多样性
    for(int i=0;i<pop;i++){
        double** arr = new double*[row];
        // 将当前解的维度数组复制到临时数组
        for(int j=0;j<row;j++){
            arr[j] = nabla[j][i];
        }
        // 计算当前解集合的多样性并累加
        mean_std += diversity_compute_array(arr,row,col);
        delete[] arr;//释放临时数组内存
    }

    // 返回平均的标准差作为多样性
    mean_std /= pop;
    return mean_std;
}

// double consensus_multi_agent(std::vector<unit*>& swarm,int pop,int dim)
/**
 * 算一个群体解的距离到全局最优解的距离，作为全局搜索的衡量指标
 * 输入：swarm：解群体；groupDim：需要计算的解的维度集合；globalBest：全局最优解
 * 输出：群体解与全局最优解的平均距离
    **/
inline double distance_compute(std::vector<unit*>& swarm, std::vector<int> groupDim, double* globalBest){
    int num = swarm.size();  // 群体大小
    int size = groupDim.size();  // 解的维度
    double* mean_vector = new double[size]{0};// 初始化均值向量

    // 计算群体解的平均值
    for(int i=0;i<num;i++){
        for(int j=0;j<size;j++){
            mean_vector[j]+=swarm[i]->X[groupDim[j]];
        }
    }

    //计算均值
    for(int i=0;i<size;i++)
        mean_vector[i] /= num;

    //计算距离
    double dis = 0;
    for(int j=0;j<size;j++){
        dis += (globalBest[groupDim[j]]-mean_vector[j])*(globalBest[groupDim[j]]-mean_vector[j]);
    }
    dis=sqrt(dis/size);// 平均距离的平方根

    delete[] mean_vector;// 释放均值向量内存
    return dis;// 返回距离
}

// 计算一个向量的L2范数（欧几里得距离）
inline double norm_2(double* v,int length){
    double res = 0;
    // 计算每个元素的平方和
    for (int i=0;i<length;i++){
        res = res + v[i]*v[i];
    }
    res = sqrt(res);// 计算平方和的平方根
    return res;// 返回L2范数
}

// 计算两个点之间的欧几里得距离
inline double distance_p2p(double *a, double* b,int length){
    double res = 0;
    // 计算每个维度的差的平方和
    for (int i=0;i<length;i++){
        double v = a[i]-b[i];
        res = res + v*v;
    }
    res = sqrt(res);// 计算平方和的平方根
    return res;// 返回欧几里得距离
}

// 计算两个点在指定维度集合上的欧几里得距离
inline double distance_compute_p2p(double* a, double* b, std::vector<int> groupDim){
    int size = groupDim.size();// 维度大小
    double res = 0;
    // 计算指定维度上的差的平方和
    for(int i=0;i<size;i++){
        double v = a[groupDim[i]]-b[groupDim[i]];
        res += v*v;
    }
    res = sqrt(res);// 计算平方和的平方根
    return res;// 返回距离
}

/* 排序函数：根据输入向量的值对索引进行排序，返回一个排序索引的向量
 * 功能是根据输入向量的值对索引进行排序，并返回一个排序后的索引向量。*/
/**举例说明
假设有一个输入向量 v：vector<int> v = {40, 10, 20, 30};
执行 sort_index 后，步骤如下：
1、初始化索引向量 idx 为 [0, 1, 2, 3]。
2、排序过程中，根据 v 中的值对索引进行排序：
   比较 v[1] (10) 和 v[0] (40)，由于 10 < 40，索引 1 排在前面。
   比较 v[2] (20) 和 v[1] (10)，由于 20 > 10，索引 1 仍在前面，依次进行比较。
3、最终排序结果为索引向量 idx = [1, 2, 3, 0]，对应的排序顺序为 [10, 20, 30, 40]。
 * */
//使用模板，以支持不同类型的向量（如 int, double, 等）
template<typename T>
//函数 sort_index 接受一个类型为 const vector<T>& 的输入向量 v，返回一个 vector<size_t> 类型的排序索引向量。
inline std::vector<size_t> sort_index(const std::vector<T> &v){
    std::vector<size_t> idx(v.size());//创建一个大小与输入向量 v 相同的索引向量 idx
    // 初始化索引
    for(unsigned int i=0;i<idx.size();i++){
        //过循环将索引向量 idx 初始化为 [0, 1, 2, ..., n-1]，其中 n 是输入向量 v 的大小
        idx[i] = i;
    }
    // 按照向量v的值对索引进行排序
    std::sort(idx.begin(),idx.end(),[&v](size_t i1,size_t i2){ return v[i1]<v[i2]; });
    //使用 sort 函数对索引向量 idx 进行排序，排序依据是输入向量 v 中对应索引的值，即比较 v[i1] 和 v[i2] 的大小
    //通过这种方式，索引向量 idx 将按照输入向量 v 中的值从小到大排序
    return idx;// 返回排序后的索引向量
}

/** 向量与矩阵相乘
    输入：vector：一个向量，matrix：一个矩阵，dim：向量的维度
    输出：矩阵和向量相乘后的结果向量*/
inline double* multiply_vec_mtx(double*vector, double**matrix, int dim) {
	int    i, j;
	//double*result = (double*)malloc(sizeof(double) * dim);
	double*result = new double[dim];// 结果向量

    // 向量与矩阵相乘
	for (i = dim - 1; i >= 0; i--) {
		result[i] = 0;

		for (j = dim - 1; j >= 0; j--) {
			result[i] += vector[j] * matrix[i][j];
		}
	}

	return(result);// 返回计算结果
}
#endif