# DPSO1 / GFPDO 与 MACPO 对齐说明

## 启动方式

与 `readme.md` 中 **MACPO** 相同：`mpirun -n <group_num>`，其中 F1–F6 的 `group_num` 为 **20**。

```bash
mpirun -n 20 ./build/DPSO1      F1 ex01 LLSO ./output/
mpirun -n 20 ./build/GFPDO_overlap F1 ex01 LLSO ./output/
```

参数顺序与 **`MACPO.cpp`** 一致：`funcID`、`exID`、`LLSO|CSO`、`outDir/`。

若 `mpirun` 进程数 ≠ 基准的 `group_num`，程序会报错退出。

## 随机种子

与 **`MACPO.cpp`** 一致：**不固定种子**，使用 `srand(当前时间毫秒)`（仅 rank 0 执行计算时调用）。若要可复现实验，需另行改代码或加环境变量（当前未实现）。

## 为何 rank 0 才算 DPSO/GFPDO？

这两个基线在源码里是 **单地址空间协同进化**（多子群循环）。为与 MACPO **命令行和进程数一致**，其余 MPI rank 在 `MPI_Init` 后直接退出，**不参与数值计算**。这与 MACPO「每 rank 一个 agent」的并行模型不同；论文中应说明：基线为文献 CC 实现，并行启动仅用于 **实验脚本对齐**。

## 批量 25 次

```bash
chmod +x run_baselines_f1_f6_batch.sh
RUNS=25 OUT=./output_baselines bash run_baselines_f1_f6_batch.sh
```

默认已为 **25** 次（ex01–ex25）。
