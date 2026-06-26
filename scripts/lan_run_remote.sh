#!/usr/bin/env bash
# 通过 SSH 在远程 WSL 上启动实验。
# hxm 机优先 systemd-run（SSH 断开后仍运行）；Dell 等无 systemd 的 WSL 回退为 Mac 长连接 SSH。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
TASK="${TASK:-comm_f13_f18}"
FUNCS="${FUNCS:-F13,F14,F15,F16,F17,F18}"
BASELINE_RUNS="${BASELINE_RUNS:-25}"
STOP_OLD="${STOP_OLD:-0}"
FILTER_HOST=""
RUN_ALL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) FILTER_HOST="${2:-}"; shift 2 ;;
    --all) RUN_ALL=true; shift ;;
    --task) TASK="${2:-}"; shift 2 ;;
    *) echo "未知参数: $1"; exit 1 ;;
  esac
done

if ! command -v sshpass >/dev/null 2>&1; then
  echo "请先安装 sshpass: brew install hudochenkov/sshpass/sshpass"
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no)

win_to_scp_path() { echo "$1" | sed 's|\\|/|g'; }

win_to_wsl_root() {
  local win="$1" explicit="${2:-}"
  if [[ -n "$explicit" ]]; then echo "$explicit"; return; fi
  local drive rest
  drive=$(echo "$win" | sed -E 's/^([A-Za-z]):.*/\1/' | tr 'A-Z' 'a-z')
  rest=$(echo "$win" | sed -E 's/^[A-Za-z]:(.*)/\1/' | sed 's|\\|/|g')
  echo "/mnt/${drive}${rest}"
}

ip_slug() { echo "$1" | tr '.' '-'; }

# 在远程 runner 脚本末尾插入：检测 systemd，失败则打印 NEED_MAC_SSH
launch_block() {
  local unit="$1" inner="$2"
  cat <<LAUNCH
if command -v systemd-run >/dev/null 2>&1 && [[ -d /run/systemd/system ]] && systemctl --user show-environment >/dev/null 2>&1; then
  systemd-run --user --collect --unit='${unit}' bash -c "${inner}"
  echo "STARTED unit=${unit} via=systemd"
else
  echo "NEED_MAC_SSH=1 unit=${unit}"
fi
LAUNCH
}

# Dell 等无 systemd 的 WSL：从 Mac 保持 SSH 会话，避免 Windows 侧回收子进程
start_mac_persisted_ssh() {
  local pass=$1 ip=$2 ssh_user=$3 wsl_root=$4 inner="$5" log_tag="$6"
  local mac_log="/tmp/macpo_lan_${ip//./_}_${log_tag}.log"
  local remote_cmd="cd ${wsl_root} && export OMP_NUM_THREADS=1 OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 && ${inner}"
  nohup sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "wsl.exe bash -lc $(printf '%q' "$remote_cmd")" >"$mac_log" 2>&1 &
  local pid=$!
  echo "    Mac 长连接 SSH 已启动 PID=${pid} 日志=${mac_log}"
}

if [[ "$RUN_ALL" != true && -z "$FILTER_HOST" ]]; then
  echo "请指定 --host IP 或 --all"
  exit 1
fi

sync_remote_scripts() {
  local pass=$1 scp_win=$2 wsl_root=$3
  local -a rels
  if [[ "$TASK" == comm_f13_f18 ]]; then
    rels=(scripts/run_comm_rate_f1_f18.sh)
  else
    rels=(
      MACPO_sourcecode/run_baselines_f1_f6_batch.sh
      scripts/run_baselines_wsl.sh
      utils/wsl_mpi_env.sh
      utils/baseline_log_stats.py
      scripts/aggregate_baselines_f1_f6.py
      MACPO_sourcecode/GFPDO_overlap.cpp
      MACPO_sourcecode/DPSO1.cpp
    )
  fi
  for rel in "${rels[@]}"; do
    if ! sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$ROOT/$rel" "${ssh_user}@${ip}:${scp_win}/$rel" 2>/dev/null; then
      echo "    scp $rel 失败，改用 wsl tee..."
      cat "$ROOT/$rel" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
        "wsl.exe bash -lc \"tee '${wsl_root}/$rel' > /dev/null\""
    fi
  done
}

while read_lan_host_row; do
  if [[ "$RUN_ALL" != true && "$ip" != "$FILTER_HOST" ]]; then
    continue
  fi

  scp_win=$(win_to_scp_path "$win_path")
  wsl_root=$(win_to_wsl_root "$win_path" "${wsl_path_extra:-}")
  slug=$(ip_slug "$ip")
  runner_local="/tmp/macpo_lan_remote_run_${ip}.sh"
  runner_remote="${scp_win}/_lan_remote_run.sh"

  stop_line=""
  if [[ "$STOP_OLD" == "1" ]]; then
    stop_line="systemctl --user stop 'macpo-'* 2>/dev/null || true
pkill -f run_comm_rate_f1_f18.sh 2>/dev/null || true
pkill -f run_baselines_f1_f6_batch.sh 2>/dev/null || true
sleep 1"
  fi

  if [[ "$TASK" == comm_f13_f18 ]]; then
    unit="macpo-comm-${slug}-${FUNCS}"
    inner="cd ${wsl_root} && export OMP_NUM_THREADS=1 OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 && FUNCS=${FUNCS} RUNS=25 bash scripts/run_comm_rate_f1_f18.sh > logs/comm_${FUNCS}_\\\$(date +%Y%m%d_%H%M%S).log 2>&1"
    cat > "$runner_local" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail
cd "${wsl_root}"
mkdir -p logs
${stop_line}
if [[ -x RL-MACPO/build/MACPO_simplified ]] && ! file -b RL-MACPO/build/MACPO_simplified | grep -qE 'ELF .*x86-64'; then
  echo "WARN: 非 Linux ELF，清理 build/ 后重编译"
  rm -rf RL-MACPO/build
fi
if [[ ! -x RL-MACPO/build/MACPO_simplified ]]; then
  cmake -S RL-MACPO -B RL-MACPO/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx
  cmake --build RL-MACPO/build -j"\$(nproc)"
fi
$(launch_block "$unit" "$inner")
SCRIPT
    mac_inner="FUNCS=${FUNCS} RUNS=25 bash scripts/run_comm_rate_f1_f18.sh > logs/comm_${FUNCS}_mac_ssh.log 2>&1"
    mac_log_tag="comm_${FUNCS}"
  elif [[ "$TASK" == baselines_dpso || "$TASK" == baselines_gfpdo ]]; then
    if [[ "$TASK" == baselines_dpso ]]; then
      algo=dpso; out_sub=output_baselines_dpso_25runs; bin=MACPO_sourcecode/build/DPSO1; target=DPSO1
      unit="macpo-dpso-${slug}"
    else
      algo=gfpdo; out_sub=output_baselines_gfpdo_25runs; bin=MACPO_sourcecode/build/GFPDO_overlap; target=GFPDO_overlap
      unit="macpo-gfpdo-${slug}"
    fi
    inner="cd ${wsl_root}/MACPO_sourcecode && export OMP_NUM_THREADS=1 OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 && ALGO=${algo} RUNS=${BASELINE_RUNS} OUT=./${out_sub} bash run_baselines_f1_f6_batch.sh > ${wsl_root}/logs/baselines_${algo}_\\\$(date +%Y%m%d_%H%M%S).log 2>&1"
    cat > "$runner_local" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail
cd "${wsl_root}"
mkdir -p logs
${stop_line}
if [[ ! -x ${bin} ]]; then
  cmake -S MACPO_sourcecode -B MACPO_sourcecode/build -DCMAKE_BUILD_TYPE=Release
  cmake --build MACPO_sourcecode/build -j"\$(nproc)" --target ${target}
fi
$(launch_block "$unit" "$inner")
SCRIPT
    mac_inner="cd MACPO_sourcecode && export OMP_NUM_THREADS=1 && ALGO=${algo} RUNS=${BASELINE_RUNS} OUT=./${out_sub} bash run_baselines_f1_f6_batch.sh > logs/${algo}_mac_ssh.log 2>&1"
    mac_log_tag="${algo}"
  else
    echo "未知 TASK: $TASK"; exit 1
  fi
  chmod +x "$runner_local"

  echo "==> [$ip] ${ssh_user} 同步并启动 $TASK ${FUNCS:+funcs=$FUNCS}"
  sync_remote_scripts "$pass" "$scp_win" "$wsl_root"
  sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$runner_local" "${ssh_user}@${ip}:${runner_remote}"
  remote_out=$(sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "wsl.exe bash -lc \"bash '${wsl_root}/_lan_remote_run.sh'\"" 2>&1) || true
  echo "$remote_out" | grep -vE 'WARNING|post-quantum|store now|pq.html' || true
  if echo "$remote_out" | grep -q 'NEED_MAC_SSH=1'; then
    start_mac_persisted_ssh "$pass" "$ip" "$ssh_user" "$wsl_root" "$mac_inner" "$mac_log_tag"
  fi
done < "$HOSTS_FILE"

echo "远程任务已提交。hxm 机: systemctl --user list-units 'macpo-*'；Dell 机: tail -f /tmp/macpo_lan_*_*.log"
