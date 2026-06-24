# WSL 远程机实验清单（F13–F18 通信率 + GFPDO/DPSO）

在 **Windows 的 WSL2（Ubuntu）** 终端执行。不要在本机 Windows CMD 里直接 `mpirun`。

假设 Mac 用户名为 `YOUR_MAC_USER`，远程 WSL 用户名为 `YOUR_WSL_USER`，远程 IP 为 `REMOTE_HOST`。
认证请用 **SSH 公钥**，勿在仓库或聊天中保存密码。

---

## 0a. 局域网分发（学校网无法 GitHub 时）

在 **Mac** 上（需 `brew install hudochenkov/sshpass/sshpass`）：

```bash
# 1) 复制并编辑机器列表（密码仅保存在本地，已 gitignore）
cp scripts/lan_hosts.example.tsv scripts/lan_hosts.local.tsv

# 2) 一键按分工表分发 + 启动（推荐）
bash scripts/lan_dispatch_all.sh

# 分工（scripts/lan_dispatch_plan.tsv）:
#   F13→.48  F14→.50  F15→.47  F16→.23  F17→.61  F18→.49
#   GFPDO→.27 (C:\zyj\MACPO2)  DPSO→.25   .24 备用

# 注意: .25/.27 可能 ping 不通但 SSH 可用；已 git clone 的机器无需 lan_distribute，直接:
#   TASK=baselines_dpso  bash scripts/lan_run_remote.sh --host 10.21.51.25
#   TASK=baselines_gfpdo bash scripts/lan_run_remote.sh --host 10.21.51.27

# 3) 仅分发 / 仅启动
bash scripts/lan_dispatch_all.sh --distribute-only
bash scripts/lan_dispatch_all.sh --run-only

# 4) 单机手动
FUNCS=F13 bash scripts/lan_run_remote.sh --host 10.21.51.48
TASK=baselines_gfpdo bash scripts/lan_run_remote.sh --host 10.21.51.24
TASK=baselines_dpso  bash scripts/lan_run_remote.sh --host 10.21.51.25

# 5) 跑完后拉回 Mac 并更新论文表
bash scripts/lan_fetch_results.sh --all
bash scripts/lan_fetch_results.sh --baselines
python3 scripts/aggregate_comm_rate_f1_f18.py
python3 scripts/patch_conference_comm_section.py
```

WSL 内日志：`tail -f /mnt/e/zyj/MACPO2/logs/*.log`（路径因机器而异）。

---

## 0. 两台机器分工

| 任务 | 目录 | 函数 | MPI 进程数 |
|------|------|------|------------|
| **B** F13–F18 通信率 | `RL-MACPO` + `scripts/run_comm_rate_f1_f18.sh` | F13–F18 | 各 60（脚本自动读取） |
| **A** GFPDO/DPSO 基线 | `MACPO_sourcecode` + `run_baselines_f1_f6_batch.sh` | F1–F6 only | 20 |

Mac 上 **F1–F12 通信率已完成**；远程只需跑 **F13–F18**（任务 B）。任务 A 为 Table I 的 † 替换（可选）。

---

## 1. WSL 一次性环境

```bash
sudo apt update
sudo apt install -y build-essential cmake git python3 \
  libopenmpi-dev openmpi-bin libeigen3-dev rsync
```

建议把仓库放在 Linux 家目录（如 `~/Project/MACPO2`），避免在 `/mnt/c/...` 上长时间跑 MPI。

---

## 2. 拉取代码（WSL）

```bash
mkdir -p ~/Project && cd ~/Project

# 方式 1：HTTPS / SSH clone（推荐，与 Mac 同一 remote）
git clone git@github.com:YOUR_ORG/MACPO2.git
cd MACPO2
git checkout main    # 或你 Mac 上正在用的分支

# 方式 2：Mac 尚未 push 时，可从 Mac 打包源码（不含 output）
# 在 Mac 上：
#   cd /path/to/MACPO2 && tar czf /tmp/MACPO2-src.tgz \
#     --exclude=output --exclude=ablation_experiments --exclude='*/build' .
#   scp /tmp/MACPO2-src.tgz YOUR_WSL_USER@REMOTE_HOST:~/
# 在 WSL 上：
#   mkdir -p ~/Project/MACPO2 && cd ~/Project/MACPO2
#   tar xzf ~/MACPO2-src.tgz
```

---

## 3. 编译

### 3a. 任务 B：RL-MACPO（F13–F18 通信率）

```bash
cd ~/Project/MACPO2/RL-MACPO
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx
cmake --build build -j"$(nproc)"
test -x build/MACPO_simplified && echo OK
```

### 3b. 任务 A：GFPDO / DPSO（F1–F6）

```bash
cd ~/Project/MACPO2/MACPO_sourcecode
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
test -x build/DPSO1 && test -x build/GFPDO_overlap && echo OK
```

---

## 4. 运行实验

### 4a. F13–F18 通信率（约 6×25 次，每次 ~1–2 min，60 ranks）

```bash
cd ~/Project/MACPO2
export OMP_NUM_THREADS=1
FUNCS=F13,F14,F15,F16,F17,F18 RUNS=25 \
  bash scripts/run_comm_rate_f1_f18.sh \
  2>&1 | tee ablation_experiments/results/comm_rate_f1_f18/batch_f13_f18.log
```

产物目录：

`ablation_experiments/results/comm_rate_f1_f18/F7_F18/F{13..18}/F*_LLSO_final_comm_*.txt`

脚本结束时会写：`RL_MACPO_IEEE_English_with_images/media/comm_rate_f1_f18.json`

### 4b. GFPDO/DPSO 5-run（可选，Table I）

```bash
cd ~/Project/MACPO2/MACPO_sourcecode
RUNS=5 OUT=./output_baselines_5runs NPROCS=20 \
  bash run_baselines_f1_f6_batch.sh \
  2>&1 | tee output_baselines_5runs/batch.log
```

产物：`MACPO_sourcecode/output_baselines_5runs/` 下各次运行的日志与输出。

---

## 5. 回传 Mac（scp / rsync）

在 **Mac** 上执行（先确保远程目录存在）：

```bash
REMOTE=YOUR_WSL_USER@REMOTE_HOST
REMOTE_ROOT=~/Project/MACPO2   # WSL 内路径

# F13–F18 通信率原始轨迹
rsync -avz --progress \
  "${REMOTE}:${REMOTE_ROOT}/ablation_experiments/results/comm_rate_f1_f18/F7_F18/F1"[3-8]"/" \
  "/Users/zhangyingjie/Project/MACPO2/ablation_experiments/results/comm_rate_f1_f18/F7_F18/"

# 汇总 JSON（若远程已 aggregate）
scp "${REMOTE}:${REMOTE_ROOT}/RL_MACPO_IEEE_English_with_images/media/comm_rate_f1_f18.json" \
  "/Users/zhangyingjie/Project/MACPO2/RL_MACPO_IEEE_English_with_images/media/"

# GFPDO/DPSO 输出（若跑了任务 A）
rsync -avz --progress \
  "${REMOTE}:${REMOTE_ROOT}/MACPO_sourcecode/output_baselines_5runs/" \
  "/Users/zhangyingjie/Project/MACPO2/MACPO_sourcecode/output_baselines_5runs/"
```

在 **Mac** 上合并 F1–F12（本地已有）+ F13–F18（刚回传）并更新论文：

```bash
cd /Users/zhangyingjie/Project/MACPO2
python3 scripts/aggregate_comm_rate_f1_f18.py --runs 25
python3 scripts/patch_conference_comm_section.py
cd RL_MACPO_IEEE_English_with_images && pdflatex -interaction=nonstopmode conference_en_ready.tex
```

GFPDO/DPSO 回传后（Table I，待 Mac 上 patch 脚本）：

```bash
python3 utils/baseline_log_stats.py   # 若已有汇总脚本则运行
# 再 patch conference_en_ready.tex 中 GFPDO†/DPSO† 列
```

---

## 6. Git：传什么、不传什么

### 用 Git 同步（代码 + 小 JSON）

| 应提交 | 不应提交（已在 .gitignore） |
|--------|----------------------------|
| 源码、`scripts/`、本 runbook | `output/`、`ablation_experiments/` |
| `utils/`、论文 `.tex` | `MACPO_original_output/`、`*.log` |
| 可选：`media/comm_rate_f1_f18.json`（几 KB） | 数千个 `*_LLSO_final_comm_*.txt` 轨迹 |

### Mac 上首次推远程（示例）

```bash
cd /Users/zhangyingjie/Project/MACPO2
git init
git add .gitignore scripts/ utils/ RL-MACPO/ MACPO_sourcecode/ \
  RL_MACPO_IEEE_English_with_images/conference_en_ready.tex \
  RL_MACPO_IEEE_English_with_images/media/*.json
git commit -m "Add WSL runbook and experiment scripts"
git branch -M main
git remote add origin git@github.com:YOUR_ORG/MACPO2.git
git push -u origin main
```

### WSL 上更新

```bash
cd ~/Project/MACPO2 && git pull
# 重新编译（见第 3 节）
```

### 实验结果回 Mac：**不要用 Git 传大轨迹**

`.gitignore` 已忽略 `ablation_experiments/`。请用 **rsync/scp**（第 5 节）。
若只想备份汇总，可单独提交小 JSON：

```bash
git add RL_MACPO_IEEE_English_with_images/media/comm_rate_f1_f18.json
git commit -m "F1-F18 comm rate summary"
git push
```

---

## 7. 故障排查

| 现象 | 处理 |
|------|------|
| `MPI_ERR_RANK` | `mpirun -n` 必须等于 `benchmarks.F*.group_num`（F13–F18 为 60） |
| `FAILED F13 run` | 查看对应 `F13_LLSO_final_comm_*.txt` 是否只有表头；单独重跑该 exid |
| WSL 内存不足 | 一次只跑一个函数：`FUNCS=F13 RUNS=25 bash scripts/...` |
| GFPDO 极慢 | 正常；F1 LLSO 单次可达数分钟；可 `RUNS=5` 先冒烟 |

---

## 8. SSH 公钥（无密码）

在 Mac 上：

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_macpo -N ""
ssh-copy-id -i ~/.ssh/id_ed25519_macpo.pub YOUR_WSL_USER@REMOTE_HOST
```

`~/.ssh/config`：

```
Host macpo-wsl
  HostName REMOTE_HOST
  User YOUR_WSL_USER
  IdentityFile ~/.ssh/id_ed25519_macpo
```

之后：`ssh macpo-wsl`、`rsync ... macpo-wsl:~/Project/MACPO2/...`
