# 原生 Windows（MSVC）部署说明

> **若你用的是 Windows 自带的 WSL（Ubuntu 等）**：请在 WSL 终端里按 **Linux 方式**编译，见 **[README_WSL.md](./README_WSL.md)** 与 **`build_wsl.sh`**。下面 MSVC / `build_windows.bat` **仅适用于**「不经过 WSL、在 cmd/PowerShell + Visual Studio 下编译」。

---

本目录与仓库根目录下的 `RL-MACPO` **源码对齐**，通过 `MACPO_LLSO.cpp` / `MACPO_CSO.cpp` 分别对应：

| 可执行文件 | 来源（RL-MACPO） |
|------------|-------------------|
| `MACPO2_LLSO.exe` | `MACPO_simplified.cpp`（LLSO 优化器） |
| `MACPO2_CSO.exe` | `MACPO_CSO_properly_fixed.cpp`（CSO 优化器） |

主程序已使用 `std::chrono` 计时，**不再依赖** POSIX 的 `sys/time.h`，可在 MSVC 下编译。

## 依赖

1. **CMake** ≥ 3.10  
2. **Visual Studio** 2019/2022（含“使用 C++ 的桌面开发”）  
3. **MS-MPI**（含 SDK）：  
   <https://www.microsoft.com/en-us/download/details.aspx?id=105289>  
   安装后 `find_package(MPI)` 通常能自动找到头文件与 `msmpi.lib`。  
4. **Eigen3**（仅头文件库）：  
   下载/克隆 Eigen，记下根目录（内含 `Eigen/` 与 `cmake/`）。

## 配置与编译

在 **“x64 Native Tools Command Prompt for VS”** 或已配置好 MS-MPI 的环境中：

```bat
cd MACPO2_deployment
set EIGEN3_ROOT=C:\path\to\eigen
build_windows.bat
```

若 `find_package(Eigen3)` 失败，可手动指定：

```bat
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -DEigen3_DIR=C:\path\to\eigen\cmake
cmake --build build --config Release
```

生成文件（默认）：

- `build\Release\MACPO2_LLSO.exe`
- `build\Release\MACPO2_CSO.exe`

## 运行示例

与 Linux 一致：`funcID`、`exID`、可选 `config`（默认 `Full`）、可选输出目录。

```bat
cd build\Release
mpiexec -n 20 MACPO2_LLSO.exe F1 ex01 Full ..\..\output\
mpiexec -n 20 MACPO2_CSO.exe  F1 ex01 Full ..\..\output\
```

说明：

- `config` 可选值见源码注释（如 `Full`、`NoSelection`、`RL_Only` 等）。  
- 输出目录默认为 `./output/`，请保证对工作目录有写权限。  
- 进程数 `-n` 需与基准问题拓扑一致（与原 MACPO/RL-MACPO 脚本相同）。

## 与 Linux/macOS 一致

在非 Windows 上仍可用 CMake + `mpicxx`：

```bash
cd MACPO2_deployment
cmake -S . -B build -DCMAKE_CXX_COMPILER=mpicxx
cmake --build build
./build/MACPO2_LLSO ...
```

## 更新源码后

将 `RL-MACPO` 中更新过的文件同步到本目录（或重新执行项目内的同步脚本/拷贝），再重新 `cmake --build`。
