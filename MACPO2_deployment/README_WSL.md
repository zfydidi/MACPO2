# WSL 下编译与运行（推荐）

你在 **Windows 里用 WSL** 时，请在 **WSL 的 Linux 终端**里操作，相当于 **Ubuntu/Debian 类 Linux**，**不要**用 `build_windows.bat` / MSVC / MS-MPI——那是给「原生 Windows 命令行 + Visual Studio」用的。

WSL 下生成的是 **无后缀的可执行文件**（`MACPO2_LLSO`、`MACPO2_CSO`），用 `mpirun` 或 `mpiexec` 启动。

## 1. 安装依赖（以 Ubuntu/WSL 为例）

```bash
sudo apt update
sudo apt install -y build-essential cmake libopenmpi-dev libeigen3-dev
```

- **MPI**：`libopenmpi-dev`（提供 `mpicxx`、`mpirun`）  
- **Eigen3**：`libeigen3-dev`（CMake 通常能直接 `find_package(Eigen3)`）

若仍找不到 Eigen，可显式指定（路径因发行版略有不同）：

```bash
cmake -S . -B build -DCMAKE_CXX_COMPILER=mpicxx \
  -DEigen3_DIR=/usr/share/eigen3/cmake
```

（可先 `dpkg -L libeigen3-dev | grep cmake` 看实际路径。）

## 2. 代码放哪里

- 仓库放在 **WSL 家目录或 Linux 文件系统**（如 `~/Project/MACPO2`）编译最快、权限最省心。  
- 若项目在 **`/mnt/c/...`**（Windows 盘），一般也能编过，但 **I/O 较慢**；大实验建议拷到 `~` 下再跑。

## 3. 编译

在仓库里：

```bash
cd MACPO2_deployment
bash build_wsl.sh
```

或手动：

```bash
cd MACPO2_deployment
cmake -S . -B build -DCMAKE_CXX_COMPILER=mpicxx
cmake --build build -j$(nproc)
```

产物：`build/MACPO2_LLSO`、`build/MACPO2_CSO`。

## 4. 运行示例

```bash
cd MACPO2_deployment/build
mkdir -p ../output
mpirun -n 20 ./MACPO2_LLSO F1 ex01 Full ../output/
mpirun -n 20 ./MACPO2_CSO  F1 ex01 Full ../output/
```

参数含义与 `RL-MACPO` 一致：`funcID`、`exID`、可选 `config`（默认 `Full`）、可选输出目录。

## 5. 与「原生 Windows」说明的区别

| 环境 | 编译器 | MPI | 说明文档 |
|------|--------|-----|----------|
| **WSL** | `g++` / `mpicxx` | OpenMPI（apt） | **本文档** |
| **原生 Windows** | MSVC | MS-MPI | `README_WINDOWS.md` |

## 6. 更新源码后

在仓库根目录：

```bash
bash MACPO2_deployment/sync_from_RL-MACPO.sh
cd MACPO2_deployment && bash build_wsl.sh
```
