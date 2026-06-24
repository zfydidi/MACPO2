#!/usr/bin/env bash
# 通过 SSH 在远程 WSL 上编译并后台启动实验。
# 用法:
#   FUNCS=F13 bash scripts/lan_run_remote.sh --host 10.21.51.48
#   TASK=baselines_dpso bash scripts/lan_run_remote.sh --host 10.21.51.25
#   TASK=baselines_gfpdo bash scripts/lan_run_remote.sh --host 10.21.51.24
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=lan_hosts_lib.sh
source "$(dirname "$0")/lan_hosts_lib.sh"
HOSTS_FILE="$ROOT/scripts/lan_hosts.local.tsv"
TASK="${TASK:-comm_f13_f18}"
FUNCS="${FUNCS:-F13,F14,F15,F16,F17,F18}"
BASELINE_RUNS="${BASELINE_RUNS:-5}"
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

write_remote_runner() {
  local proj="$1" out="$2"
  local stop_block=""
  if [[ "$STOP_OLD" == "1" ]]; then
    stop_block='pkill -f run_comm_rate_f1_f18.sh 2>/dev/null || true
pkill -f run_baselines_f1_f6_batch.sh 2>/dev/null || true
sleep 1'
  fi

  if [[ "$TASK" == "comm_f13_f18" ]]; then
    cat > "$out" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail
cd "$proj"
export OMP_NUM_THREADS=1
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
mkdir -p logs
${stop_block}
if [[ ! -x RL-MACPO/build/MACPO_simplified ]]; then
  echo "==> compile RL-MACPO"
  cmake -S RL-MACPO -B RL-MACPO/build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=mpicxx
  cmake --build RL-MACPO/build -j"\$(nproc)"
fi
LOG="logs/comm_${FUNCS}_\$(date +%Y%m%d_%H%M%S).log"
nohup bash -lc 'FUNCS=${FUNCS} RUNS=25 bash scripts/run_comm_rate_f1_f18.sh' >"\$LOG" 2>&1 &
echo "STARTED comm funcs=${FUNCS} pid=\$! log=\$LOG"
SCRIPT
  elif [[ "$TASK" == "baselines_dpso" || "$TASK" == "baselines_gfpdo" ]]; then
    local algo out_sub log_tag need_bin
    if [[ "$TASK" == "baselines_dpso" ]]; then
      algo="dpso"
      out_sub="output_baselines_dpso_5runs"
      log_tag="baselines_dpso"
      need_bin="MACPO_sourcecode/build/DPSO1"
    else
      algo="gfpdo"
      out_sub="output_baselines_gfpdo_5runs"
      log_tag="baselines_gfpdo"
      need_bin="MACPO_sourcecode/build/GFPDO_overlap"
    fi
    cat > "$out" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail
cd "$proj"
mkdir -p logs
${stop_block}
if [[ ! -x ${need_bin} ]]; then
  echo "==> compile MACPO_sourcecode (${algo})"
  cmake -S MACPO_sourcecode -B MACPO_sourcecode/build -DCMAKE_BUILD_TYPE=Release
  cmake --build MACPO_sourcecode/build -j"\$(nproc)" --target $([[ "$algo" == "dpso" ]] && echo DPSO1 || echo GFPDO_overlap)
fi
LOG="logs/${log_tag}_\$(date +%Y%m%d_%H%M%S).log"
pushd MACPO_sourcecode >/dev/null
export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
nohup env ALGO=${algo} RUNS=${BASELINE_RUNS} OUT=./${out_sub} bash run_baselines_f1_f6_batch.sh >"../\$LOG" 2>&1 &
popd >/dev/null
echo "STARTED ${log_tag} pid=\$! log=\$LOG"
SCRIPT
  else
    echo "未知 TASK: $TASK"
    exit 1
  fi
  chmod +x "$out"
}

if [[ "$RUN_ALL" != true && -z "$FILTER_HOST" ]]; then
  echo "请指定 --host IP 或 --all"
  exit 1
fi

sync_remote_scripts() {
  local ip=$1 pass=$2 scp_win=$3 wsl_root=$4
  if [[ "$TASK" == comm_f13_f18 ]]; then
    sshpass -p "$pass" scp "${SSH_OPTS[@]}" \
      "$ROOT/scripts/run_comm_rate_f1_f18.sh" \
      "${user}@${ip}:${scp_win}/scripts/run_comm_rate_f1_f18.sh" 2>/dev/null || true
  elif [[ "$TASK" == baselines_dpso || "$TASK" == baselines_gfpdo ]]; then
    for rel in MACPO_sourcecode/run_baselines_f1_f6_batch.sh \
               MACPO_sourcecode/GFPDO_overlap.cpp \
               MACPO_sourcecode/DPSO1.cpp; do
      if ! sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$ROOT/$rel" "${ssh_user}@${ip}:${scp_win}/$rel" 2>/dev/null; then
        echo "    scp $rel 失败，改用 wsl tee..."
        cat "$ROOT/$rel" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
          "wsl.exe bash -lc \"tee '${wsl_root}/$rel' > /dev/null\""
      fi
    done
  fi
}

while read_lan_host_row; do
  if [[ "$RUN_ALL" != true && "$ip" != "$FILTER_HOST" ]]; then
    continue
  fi

  scp_win=$(win_to_scp_path "$win_path")
  wsl_root=$(win_to_wsl_root "$win_path" "${wsl_path_extra:-}")
  remote_runner_win="${scp_win}/_lan_remote_run.sh"
  remote_runner_wsl="${wsl_root}/_lan_remote_run.sh"

  write_remote_runner "$wsl_root" "/tmp/macpo_lan_remote_run_${ip}.sh"
  RUNNER_LOCAL="/tmp/macpo_lan_remote_run_${ip}.sh"

  echo "==> [$ip] ${ssh_user} 同步脚本并启动 $TASK ${FUNCS:+funcs=$FUNCS}"
  sync_remote_scripts "$ip" "$pass" "$scp_win" "$wsl_root"
  sshpass -p "$pass" scp "${SSH_OPTS[@]}" "$RUNNER_LOCAL" "${ssh_user}@${ip}:${remote_runner_win}"
  sshpass -p "$pass" ssh "${SSH_OPTS[@]}" "${ssh_user}@${ip}" \
    "wsl.exe bash -lc \"chmod +x '${remote_runner_wsl}' && bash '${remote_runner_wsl}'\""
done < "$HOSTS_FILE"

echo "远程任务已提交。WSL 内查看: tail -f <项目>/logs/*.log"
