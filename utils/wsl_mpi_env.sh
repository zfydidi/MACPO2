#!/usr/bin/env bash
# WSL2 上 OpenMPI 常见修复：btl-vader cma-permission-denied
# 用法: source /path/to/MACPO2/utils/wsl_mpi_env.sh && wsl_mpi_env

wsl_mpi_env() {
  export OMPI_ALLOW_RUN_AS_ROOT="${OMPI_ALLOW_RUN_AS_ROOT:-1}"
  export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM="${OMPI_ALLOW_RUN_AS_ROOT_CONFIRM:-1}"
  export OMPI_MCA_btl_vader_single_copy_mechanism="${OMPI_MCA_btl_vader_single_copy_mechanism:-none}"
  export OMPI_MCA_mpi_leave_pinned="${OMPI_MCA_mpi_leave_pinned:-0}"
}

# mpirun 额外参数（与 wsl_mpi_env 配套）
WSL_MPIRUN_MCA_ARGS=(--mca btl_vader_single_copy_mechanism none)

wsl_mpi_env
