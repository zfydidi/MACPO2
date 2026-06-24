#ifndef STRUCT_H
#define STRUCT_H

#include <string.h>
#include <vector>

struct unit
{
    double *X;
    double fitness;
    unit(double *globalBest, int dimension)
    {
        X = new double[dimension];
        memcpy(X, globalBest, sizeof(double) * dimension);
        fitness = DBL_MAX;
    }
    bool operator<(const unit &y) const
    {
        return fitness < y.fitness;
    }
    bool operator>(const unit &y) const
    {
        return fitness > y.fitness;
    }
    ~unit(){
        // cout<<"destruction of unit object\n";
        delete[] X;
    }
};

static bool cmp_unit_pointer(unit* a, unit* b){
    return a->fitness < b->fitness;
}

struct particle : unit
{
    double *v;
    particle(double *globalBest, int dimension) : unit(globalBest, dimension)
    {
        v = new double[dimension];
        memset(v, 0, sizeof(double) * dimension);
    }
    ~particle(){
        // cout<<"destruction of particle object\n";
        delete[] v;
    }
};

void standardization(double* arr, int size){
    double std = 0;
    double mean = 0;
    for(int i=0;i<size;i++){
        mean += arr[i];
    }
    mean = mean/size;

    for(int i=0;i<size;i++){
        std += (arr[i]-mean)*(arr[i]-mean);
    }
    std = sqrt(std/size);

    for(int i=0;i<size;i++){
        if(std == 0)
            arr[i] = 0;
        else
            arr[i] = (arr[i]-mean)/std;
    }

    return;
}

void getStd(double* arr, int size, double &std, double &mean){
    std = 0;
    mean = 0;
    for(int i=0;i<size;i++){
        mean += arr[i];
    }
    mean = mean/size;

    for(int i=0;i<size;i++){
        std += (arr[i]-mean)*(arr[i]-mean);
    }
    std = sqrt(std/size);

    return;
}

double* getMean(std::vector<unit*>& swarm, vector<int> groupDim){
    int dim_size = groupDim.size();
    int swarm_size = swarm.size();
    double* mean = new double[dim_size]{0};
    for(int j=0;j<dim_size;j++){
        for(int i=0;i<swarm_size;i++){
            mean[j] += swarm[i]->X[groupDim[j]];
        }
        mean[j] /= swarm_size;
    }
    delete[] mean;
    return mean;
}

double getArrMean(double* arr, int size){
    double res = 0;
    for(int i=0;i<size;i++){
        res += arr[i];
    }
    return res/size;
}

void normalize(double* arr, int size){
    int x_min_index = 0;
    int x_max_index = 0; 
    for(int i=0;i<size;i++){
        if(arr[i] < arr[x_min_index])
            x_min_index = i;
        else if(arr[i] > arr[x_max_index])
            x_max_index = i;
    }

    for(int i=0;i<size;i++){
        if( (arr[x_max_index]-arr[x_min_index])==0 )
            arr[i] = 0;
        else
            arr[i] = (arr[i]-arr[x_min_index])/(arr[x_max_index]-arr[x_min_index]);
    }

    return;
}

double diversity_compute(std::vector<unit*>& swarm, vector<int> groupDim){
    int num = swarm.size();
    int size = groupDim.size();
    double** swarm_data = new double*[num];
    double* mean_vector = new double[size]{0};
    for(int i=0;i<num;i++){
        swarm_data[i] = new double[size];
        for(int j=0;j<size;j++){
            swarm_data[i][j] = swarm[i]->X[groupDim[j]];
            mean_vector[j]+=swarm_data[i][j];
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
        std +=sqrt(dis);
    }
    std /= num;
    delete[] mean_vector;
    for(int i=0;i<num;i++){
        delete[] swarm_data[i];
    }
    delete[] swarm_data;
    return std;
}

double diversity_compute_array(double** arr, int row, int col){

    double* mean_vector = new double[col]{0};
    for(int i=0;i<row;i++){
        for(int j=0;j<col;j++){
            mean_vector[j]+=arr[i][j];
        }
    }
    //计算均值
    for(int i=0;i<col;i++)
        mean_vector[i] /= row;
    //计算标准差
    double std=0;
    for(int i=0;i<row;i++){
        double dis = 0;
        for(int j=0;j<col;j++){
            dis += (arr[i][j]-mean_vector[j])*(arr[i][j]-mean_vector[j]);
        }
        std +=sqrt(dis);
    }
    std /= row;
    delete[] mean_vector;
    return std;
}

double diversity_compute_nabla(vector<double**> nabla, int pop, int row, int col){

    double mean_std=0;
    for(int i=0;i<pop;i++){
        double** arr = new double*[row];
        for(int j=0;j<row;j++){
            arr[j] = nabla[j][i];
        }
        mean_std += diversity_compute_array(arr,row,col);
        delete[] arr;
    }
    mean_std /= pop;
    return mean_std;
}

// double consensus_multi_agent(std::vector<unit*>& swarm,int pop,int dim)

double distance_compute(std::vector<unit*>& swarm, vector<int> groupDim, double* globalBest){
    int num = swarm.size();
    int size = groupDim.size();
    double* mean_vector = new double[size]{0};
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
    dis=sqrt(dis/size);
    delete[] mean_vector;
    return dis;
}


double norm_2(double* v,int length){
    double res = 0;
    for (int i=0;i<length;i++){
        res = res + v[i]*v[i];
    }
    res = sqrt(res);
    return res;
}

double distance_p2p(double *a, double* b,int length){
    double res = 0;
    for (int i=0;i<length;i++){
        double v = a[i]-b[i];
        res = res + v*v;
    }
    res = sqrt(res);
    return res;
}

double distance_compute_p2p(double* a, double* b, vector<int> groupDim){
    int size = groupDim.size();
    double res = 0;
    for(int i=0;i<size;i++){
        double v = a[groupDim[i]]-b[groupDim[i]];
        res += v*v;
    }
    res = sqrt(res);
    return res;
}

template<typename T>
vector<size_t> sort_index(const vector<T> &v){
    vector<size_t> idx(v.size());
    for(unsigned int i=0;i<idx.size();i++){
        idx[i] = i;
    }
    sort(idx.begin(),idx.end(),[&v](size_t i1,size_t i2){ return v[i1]<v[i2]; });
    return idx;
}


double* multiply_vec_mtx(double*vector, double**matrix, int dim) {
	int    i, j;
	//double*result = (double*)malloc(sizeof(double) * dim);
	double*result = new double[dim];

	for (i = dim - 1; i >= 0; i--) {
		result[i] = 0;

		for (j = dim - 1; j >= 0; j--) {
			result[i] += vector[j] * matrix[i][j];
		}
	}

	return(result);
}
#endif