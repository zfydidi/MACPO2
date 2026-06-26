# Scalability 实验（F1 / F7 / F13 / F1S50 / F1S100）

## 重要：运行顺序

每个 benchmark **先跑 5 次 MACPO**，再跑 **5 次 RL-MACPO**。  
日志里第一条出现 `AlwaysOn` 是 **正常的**，不是没跑 RL。

```
MACPO:    scale_F1S100_MACPO_r01 … r05   配置 AlwaysOn
RL-MACPO: scale_F1S100_RL-MACPO_r01 … r05   配置 Selection_0.9_0.7_0.5
```

F1S100 共 **10 次 MPI**（约数小时），请等日志出现 `==== F1S100 | RL-MACPO` 再判断 RL 是否开始。

---

## Mac → WSL 要传的文件

**最小更新包（先传这些）：**

```
scripts/run_scalability_experiments.py
scripts/run_scalability_experiments_wsl.sh
utils/wsl_mpi_env.sh
utils/chain_benchmark_codegen.py
```

**若 WSL 还没编过 RL-MACPO，还需源码：**

```
RL-MACPO/CMakeLists.txt
RL-MACPO/MACPO_simplified.cpp
RL-MACPO/components/
RL-MACPO/Benchmarks/
```

**Mac 打包示例：**

```bash
cd /Users/zhangyingjie/Project/MACPO2
tar czf /tmp/MACPO2-scale-scripts.tgz \
  scripts/run_scalability_experiments.py \
  scripts/run_scalability_experiments_wsl.sh \
  scripts/WSL_SCALABILITY_RUNBOOK.md \
  utils/wsl_mpi_env.sh \
  utils/chain_benchmark_codegen.py
```

WSL 解压：`cd /mnt/d/zyj/MACPO2 && tar xzf /mnt/d/zyj/MACPO2-scale-scripts.tgz`

或 `git pull`（两边同一仓库时）。

---

## WSL 一次性准备

```bash
cd /mnt/d/zyj/MACPO2
source utils/wsl_mpi_env.sh
export OMP_NUM_THREADS=1

# 编译（只需一次）
cmake -S RL-MACPO -B RL-MACPO/build \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx
cmake --build RL-MACPO/build -j"$(nproc)"
file RL-MACPO/build/MACPO_simplified   # 必须 ELF x86-64

# F1S50/F1S100 数据文件
python3 -c "from utils.chain_benchmark_codegen import ensure_scalability_benchmarks; print(ensure_scalability_benchmarks())"

mkdir -p RL-MACPO/output1/output logs
```

---

## 哪些要重跑、哪些不用？

| Benchmark | 是否需要重跑 | 说明 |
|-----------|--------------|------|
| F1 / F7 / F13 | **通常不用** | `output1/output/` 里已有完整 `scale_*_r01…r05`（各 30+ 行）时，`--skip-existing` 会全部跳过 |
| F1S50 / F1S100 | 缺 RL 或 scale 空壳时才跑 | 只需补缺失的 MACPO/RL 次数 |

**logs 里的控制台文字不能代替结果文件。** 汇总 JSON 只读：

`RL-MACPO/output1/output/F*_LLSO_final_scale_*.txt`

若 Mac 上 F1/F7/F13 已齐，WSL 也有同名完整 `.txt`，跑脚本会打印 `skip-existing`，不会重跑 MPI。

---

**每个窗口先执行：**

```bash
cd /mnt/d/zyj/MACPO2
source utils/wsl_mpi_env.sh
export OMP_NUM_THREADS=1
```

**再各开一窗：**

```bash
bash scripts/run_scalability_experiments_wsl.sh F1
bash scripts/run_scalability_experiments_wsl.sh F7
bash scripts/run_scalability_experiments_wsl.sh F13
bash scripts/run_scalability_experiments_wsl.sh F1S50
bash scripts/run_scalability_experiments_wsl.sh F1S100
```

**看日志：**

```bash
tail -f "$(cat logs/.last_scale_F1S100.logpath)"
```

**输出目录（固定）：**

```
RL-MACPO/output1/output/
  F1S100_LLSO_final_scale_F1S100_MACPO_r01.txt
  F1S100_LLSO_final_scale_F1S100_RL-MACPO_r01.txt
  ...
```

完整文件应有 **30+ 行** 且末尾含 `# COST_STATS`。只有 3 行表头 = 跑挂了，需重跑。

---

## WSL → Mac 拉回

复制整个目录：

```
D:\zyj\MACPO2\RL-MACPO\output1\output\
```

到 Mac：

```
MACPO2/RL-MACPO/output1/output/
```

---

## Mac 汇总 JSON + 更新论文

```bash
cd /Users/zhangyingjie/Project/MACPO2

python3 scripts/run_scalability_experiments.py --aggregate-only \
  --output-dir RL-MACPO/output1/output \
  --benchmarks F1,F7,F13,F1S50,F1S100 --runs 5

python3 scripts/run_comm_baselines.py --aggregate-only \
  --output-dir RL-MACPO/output1/output \
  --funcs F1,F2,F3,F4,F5,F6 --runs 10

python3 scripts/patch_conference_comm_policy.py
```

检查 `RL_MACPO_IEEE_English_with_images/media/scalability_chain.json` 里 F1S100 的 `RL-MACPO` 行 `runs` 应为 **5**（不是 0）。
