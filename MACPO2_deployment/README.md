# MACPO2 部署包

## 包含内容
- `MACPO_CSO.cpp` - CSO优化器版本
- `MACPO_LLSO.cpp` - LLSO优化器版本
- `Benchmarks/` - 基准函数库
- `components/` - 组件库
- `util/` - 工具库

## 安装和运行

### 1. 安装依赖并编译
```bash
chmod +x *.sh
./install.sh
```

### 2. 运行批量实验（50次）
```bash
./run_experiments.sh
```

### 3. 单次测试
```bash
./run_single.sh CSO F1 1    # CSO方法，F1函数，第1次
./run_single.sh LLSO F2 5   # LLSO方法，F2函数，第5次
```

## 结果输出
- `output/CSO/` - CSO方法结果
- `output/LLSO/` - LLSO方法结果
- `output/summary.txt` - 汇总统计
- `log/` - 运行日志

## 实验配置
- 函数: F1-F6
- 每种方法每函数运行50次
- MPI进程数: 20

