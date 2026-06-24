## Build (CMake + Eigen + MPI)

```bash
cd MACPO_sourcecode
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

生成可执行文件：`MACPO`、`DPSO1`、`GFPDO_overlap`。

## Run（与 MACPO 相同的进程数规则）

基准 `group_num`：F1–F6 为 **20**，F7–F12 为 **40**，F13–F18 为 **60**。`mpirun -n` **必须等于** `group_num`（与 `MACPO.cpp` 中每 rank 对应一个子问题一致）。

**MACPO**

```bash
mpirun -n 20 ./build/MACPO F1 ex01 LLSO ./output/
# 等价于 readme 旧写法（省略 exID / 优化器 / 目录时使用默认）:
mpirun -n 20 ./build/MACPO F1
```

**DPSO1**（命令行参数顺序与 MACPO 一致：`funcID` `[exID]` `[LLSO|CSO]` `[outDir/]`）

```bash
mpirun -n 20 ./build/DPSO1 F1 ex01 LLSO ./output/
```

**GFPDO_overlap**

```bash
mpirun -n 20 ./build/GFPDO_overlap F1 ex01 LLSO ./output/
```

说明：DPSO/GFPDO 的协同进化主体在实现上由 **rank 0** 执行；其余 rank 仅占位退出，以便与 MACPO **使用相同的 `mpirun -n` 启动方式** 与脚本对齐。随机种子与 **MACPO.cpp** 一样：**非固定**，`srand(当前时间毫秒)`。

## 旧版手工编译（仅供参考）

```
mpic++ -std=c++11 MACPO.cpp ./Benchmarks/Benchmarks.cpp -o MACPO
mpirun -n 20 ./MACPO F1
```
