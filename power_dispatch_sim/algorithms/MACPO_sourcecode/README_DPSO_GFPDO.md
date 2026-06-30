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

## 批量 25 次（WSL 推荐）

```bash
# 方式 A：项目根目录一键脚本（自动编译 + 续跑）
cd /mnt/d/zyj/MACPO2   # 改成你的 WSL 路径
bash scripts/run_baselines_wsl.sh dpso    # 或 gfpdo

# 方式 B：在 MACPO_sourcecode 内直接跑
cd MACPO_sourcecode
export OMP_NUM_THREADS=1 OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
export OMPI_MCA_btl_vader_single_copy_mechanism=none
ALGO=dpso RUNS=25 OUT=./output_baselines_dpso_25runs bash run_baselines_f1_f6_batch.sh
ALGO=gfpdo RUNS=25 OUT=./output_baselines_gfpdo_25runs bash run_baselines_f1_f6_batch.sh
```

默认 **25** 次（ex01–ex25），`SKIP_EXISTING=1` 可断点续跑。  
产物：`*.log`（含 `final fitness=`）与 `iter_*.txt`（每代曲线）。

Mac 汇总：

```bash
python3 scripts/aggregate_baselines_f1_f6.py
```
