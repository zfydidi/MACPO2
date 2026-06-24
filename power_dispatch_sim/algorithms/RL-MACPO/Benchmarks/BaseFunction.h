#ifndef BASEFUNCTION_H  // 如果没有定义 BASEFUNCTION_H 宏
#define BASEFUNCTION_H  // 则定义 BASEFUNCTION_H 宏，防止重复包含此头文件

#include <algorithm>
#include <cmath>
#include <iostream>

#define PI (3.141592653589793238462643383279)  // 定义 PI 的近似值
#define E  (2.718281828459045235360287471352)  // 定义自然数 E 的近似值
#define L(i) ((int64_t)i)   // 定义宏 L，将值 i 转换为 int64_t 类型
#define D(i) ((double)i)    // 定义宏 D，将值 i 转换为 double 类型

using std::cout;
using std::endl;

// 函数声明部分，包含了一些用于优化算法或数学计算的函数
double* multiply(double*vector, double**matrix, int dim);
double elliptic(double*x, int dim);
double rastrigin(double*x, int dim);
double ackley(double*x, int dim);
double schwefel(double*x, int dim);
double rosenbrock(double*x, int dim);
double griewank(double*x, int dim);
double ellipsoid(double* x,int dim);
void transform_osz(double* z, int dim);
void transform_asy(double* z, double beta, int dim);
void Lambda(double* z, double alpha, int dim);
int sign(double x);
double hat(double x);
double c1(double x);
double c2(double x);

/**
 * @brief 矩阵向量乘法函数
 *
 * 计算一个向量与一个矩阵的乘积
 *
 * @param vector 输入的向量
 * @param matrix 输入的矩阵
 * @param dim 向量和矩阵的维度
 * @return 返回乘积结果向量
 */
// 矩阵乘法函数：计算向量 vector 与矩阵 matrix 的乘积 dim是维数
double* multiply(double*vector, double**matrix, int dim) {
	int    i, j;
	//double*result = (double*)malloc(sizeof(double) * dim);
	double*result = new double[dim];  // 动态分配数组用于存储结果

	for (i = dim - 1; i >= 0; i--) {  // 遍历每一行
		result[i] = 0;

		for (j = dim - 1; j >= 0; j--) {
			result[i] += vector[j] * matrix[i][j]; // 计算矩阵乘积
		}
	}

	return(result);  // 返回结果向量
}

/**
 * @brief Elliptic 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Elliptic 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double elliptic(double*x, int dim) {
	double result = 0.0;
	int    i;

	transform_osz(x, dim);  // 进行 osz 变换

	for (i = 0; i < dim; i++)
	{
		// printf("%f %f %f\n",result, x[i], pow(1.0e6,  i/((double)(dim - 1)) ));
		result += pow(1.0e6, i / ((double)(dim - 1))) * x[i] * x[i];
	}
	return(result);
}

/**
 * @brief Ellipsoid 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Ellipsoid 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double ellipsoid(double* x,int dim){
	double result = 0.0;
	int i;
	for(i=0;i<dim;i++)
	{
		result += x[i] * x[i] * (i+1);// 各分量平方加权和
	}
	return result;
}

/**
 * @brief Rastrigin 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Rastrigin 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double rastrigin(double*x, int dim) {
	double sum = 0;
	int    i;


	// T_{osz}
	transform_osz(x, dim);// 进行 osz 变换

	// T_{asy}^{0.2}
	transform_asy(x, 0.2, dim);// 进行 asy 变换
	// lambda
	Lambda(x, 10, dim); // 进行 lambda 变换

	for (i = dim - 1; i >= 0; i--) {
		sum += x[i] * x[i] - 10.0 * cos(2 * PI * x[i]) + 10.0;
	}
	return(sum);
}

/**
 * @brief Ackley 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Ackley 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double ackley(double*x, int dim) {
	double sum1 = 0.0;
	double sum2 = 0.0;
	double sum;
	int    i;

	// T_{osz}
	transform_osz(x, dim);// 进行 osz 变换

	// T_{asy}^{0.2}
	transform_asy(x, 0.2, dim);// 进行 asy 变换

	// lambda
	Lambda(x, 10, dim);// 进行 lambda 变换

	for (i = dim - 1; i >= 0; i--) {
		sum1 += (x[i] * x[i]);
		sum2 += cos(2.0 * PI * x[i]);
	}

	sum = -20.0 * exp(-0.2 * sqrt(sum1 / dim)) - exp(sum2 / dim) + 20.0 + E;

	//cout<<sum1<<" "<<sum2<<" "<<sum<<endl;
	return(sum);
}

/**
 * @brief Schwefel 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Schwefel 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double schwefel(double*x, int dim) {
	int    j;
	double s1 = 0;
	double s2 = 0;

	// T_{osz}
	transform_osz(x, dim);// 进行 osz 变换

	// T_{asy}^{0.2}
	transform_asy(x, 0.2, dim);// 进行 asy 变换

	for (j = 0; j < dim; j++) {
		s1 += x[j];
		s2 += (s1 * s1);// 累加每一项的平方
	}

	return(s2);
}

/**
 * @brief Rosenbrock 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Rosenbrock 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double rosenbrock(double*x, int dim) {
	int    j;
	double oz, t;
	double s = 0.0;
	j = dim - 1;

	for (--j; j >= 0; j--) {
		oz = x[j + 1];
		t = ((x[j] * x[j]) - oz);
		s += (100.0 * t * t);
		t = (x[j] - 1.0);
		s += (t * t);
	}
	return(s);
}

/**
 * @brief Griewank 函数
 *
 * 用于优化测试的目标函数
 *
 * @param x 输入的向量
 * @param dim 向量的维度
 * @return 计算得到的目标函数值
 */
// Griewank 函数，用于优化测试，传入向量 x 和维数 dim，返回结果
double griewank(double* x,int dim){
	double res = 0;
	for(int i=0;i<dim;i++){
		res += x[i]*x[i]/4000;
	}
	double t = 1;
	for(int i=0;i<dim;i++){
		t = t*cos(x[i]/sqrt(i+1));
	}
	res -= t;
	res += 1;
	return res;
}

/**
 * @brief OSZ 变换
 *
 * 对输入向量应用 OSZ 变换
 *
 * @param z 输入的向量
 * @param dim 向量的维度
 */
// transform_osz 函数：osz 变换，用于优化
void transform_osz(double* z, int dim)
{
	// apply osz transformation to z
    // 对 z 应用 osz 变换
	for (int i = 0; i < dim; ++i)
	{
		double temp = sign(z[i]) * exp(hat(z[i]) + 0.049 * (sin(c1(z[i]) * hat(z[i])) + sin(c2(z[i])* hat(z[i]))));
		// cout<<fabs(z[i])<<" ";
		z[i]=temp;
	}
}

/**
 * @brief ASY 变换
 *
 * 对输入向量应用 ASY 变换
 *
 * @param z 输入的向量
 * @param beta 变换参数
 * @param dim 向量的维度
 */
// transform_asy 函数：asy 变换，用于优化
void transform_asy(double* z, double beta, int dim)
{
	for (int i = 0; i < dim; ++i)
	{
		if (z[i] > 0)
		{
			z[i] = pow(z[i], 1 + beta * i / ((double)(dim - 1)) * sqrt(z[i]));
		}
	}
}

/**
 * @brief Lambda 变换
 *
 * 对输入向量应用 Lambda 变换
 *
 * @param z 输入的向量
 * @param alpha 变换参数
 * @param dim 向量的维度
 */
// Lambda 函数：lambda 变换，用于优化
void Lambda(double* z, double alpha, int dim)
{
	for (int i = 0; i < dim; ++i)
	{
		z[i] = z[i] * pow(alpha, 0.5 * i / ((double)(dim - 1)));
	}
}

/**
 * @brief 返回 x 的符号
 *
 * @param x 输入值
 * @return x 的符号，返回 1、-1 或 0
 */
// sign 函数：返回 x 的符号
int sign(double x)
{
	if (x > 0) return 1;
	if (x < 0) return -1;
	return 0;
}

/**
 * @brief 计算 x 的绝对值的对数
 *
 * @param x 输入值
 * @return x 的绝对值的对数
 */
// hat 函数：返回 x 的绝对值的对数值
double hat(double x)
{
	if (x == 0)
	{
		return 0;
	}
	else
	{
		return log(fabs(x));
	}
}

/**
 * @brief 返回与 x 相关的常数 c1
 *
 * @param x 输入值
 * @return x 相关的常数 c1=10（x>0）否则 c1=5.5
 */
// c1 函数：条件返回不同的值
double c1(double x)
{
	if (x > 0)
	{
		return 10;
	}
	else
	{
		return 5.5;
	}
}

/**
 * @brief 返回与 x 相关的常数 c2
 *
 * @param x 输入值
 * @return x 相关的常数 c2=7.9(x>=) 否则 c2=3.1
 */
// c2 函数：条件返回不同的值
double c2(double x)
{
	if (x > 0)
	{
		return 7.9;
	}
	else
	{
		return 3.1;
	}
}

#endif