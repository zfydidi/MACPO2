#include <sstream>
#include <fstream>
#include <iostream>
#include<cstring>
#include<cstdio>
#include<cmath>
#include<algorithm>
#include <random> 
// #include<regex>
#include "Benchmarks.h"
#include "BaseFunction.h"
using namespace std;
using json = nlohmann::json;

void log_str(string str, int rank){
    string log_filename = "../log/rank"+to_string(rank)+".txt";
    fstream ft(log_filename, ios::out);
    ft<<str<<endl;
    ft.close();
}


void shuffleArrays(double* array1, double* array2, int length) {
    // Create a vector of indices from 0 to length-1
    std::vector<int> indices(length);
    for (int i = 0; i < length; ++i) {
        indices[i] = i;
    }

    // Create a random number generator
    std::random_device rd;
    std::mt19937 gen(rd());

    // Shuffle the indices
    std::shuffle(indices.begin(), indices.end(), gen);

    // Create temporary arrays to hold the shuffled values
    std::vector<double> tempArray1(length);
    std::vector<double> tempArray2(length);

    // Reorder the original arrays based on the shuffled indices
    for (int i = 0; i < length; ++i) {
        tempArray1[i] = array1[indices[i]];
        tempArray2[i] = array2[indices[i]];
    }

    // Copy the shuffled values back to the original arrays
    for (int i = 0; i < length; ++i) {
        array1[i] = tempArray1[i];
        array2[i] = tempArray2[i];
    }
}

Benchmarks::Benchmarks(string ID,int max_eva_times,bool overlap){
    string config_path = "./Benchmarks/default_config.json";
    string data_path = "./Benchmarks/data/";
    this->funcID = ID;

    ifstream file_config(config_path);
    json config;
    file_config >> config;
    file_config.close();

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
    
    // 读取最优值
    xopt = read_data<double>(data_path+"xopt_"+ID+".txt");

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

    shftx = new double[len];
    for (int j = 0; j < len; j++) {
        int index = group[groupIndex][j];
        if (x[index] > ub || x[index] < lb) {
            cout << "solution out of range;" << endl;
            return 0;
        }
        shftx[j] = x[index] - xopt[groupIndex][j];
    }

    if(if_rotate==true)
        rotate_x = multiply(shftx, R[groupIndex], len);
    else
        rotate_x = shftx;

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

double Benchmarks::global_eva(double* x) {
	double res = 0;
    for(int i=0;i<group_num;i++){
        double r = local_eva(x,i);
        res += r;
    }
    

	return res;
}

double Benchmarks::getLocalOpt(int groupIndex){
    double fopt = 0;
    try{
        fopt = func_config["subproblems"][groupIndex]["fopt"];
    }catch(...){
    }
    
    return fopt;

}

double Benchmarks::getMinX() {
	return func_config["lower_bound"];
}
double Benchmarks::getMaxX() {
	return func_config["upper_bound"];
}
int Benchmarks::getGroupNum() {
	return func_config["group_num"];
}
int Benchmarks::getDimension(){
    return func_config["dimension"];
}


template<typename T>
T** Benchmarks::read_data(string fileName) {
	// cout << fileName<<endl;
    T** res = nullptr;
    ifstream file(fileName);
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

vector<int> Benchmarks::getOverlapDim(int g1,int g2){
    vector<int> dim1 = getGroupDim(g1);
    vector<int> dim2 = getGroupDim(g2);
    vector<int> overlap;
    sort(dim1.begin(),dim1.end());
    sort(dim2.begin(),dim2.end());
    set_intersection(dim1.begin(),dim1.end(),dim2.begin(),dim2.end(),back_inserter(overlap));
    return overlap;
}


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

vector<int> Benchmarks::getGroupDim(int groupIndex){
    if(this->overlap_grouping){
        int size = func_config["subproblems"][groupIndex]["dimension"];
        vector<int> v(group[groupIndex],group[groupIndex]+size);
        return v;
    }else{
        int size = func_config["subproblems"][groupIndex]["dimension"];
        vector<int> v(group[groupIndex],group[groupIndex]+size);
        vector<int> overlap = getOverlapGroup(groupIndex);
        for(int g:overlap){
            if(g<groupIndex){
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
        }
        return v;
    }
} 

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

double** Benchmarks::getNetworkGraph(){
    if(W==nullptr){
        string data_path = "./Benchmarks/data/";
        W=read_data<double>(data_path+"W_"+funcID);
    }
    return W;
}