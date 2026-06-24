cmake_minimum_required(VERSION 3.10)
project(MACPO_source CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Eigen3 REQUIRED)
find_package(MPI REQUIRED)

set(MACPO_ROOT ${CMAKE_CURRENT_SOURCE_DIR})
include_directories(${MACPO_ROOT})
include_directories(${EIGEN3_INCLUDE_DIR})
include_directories(${MPI_CXX_INCLUDE_DIRS})

set(BENCH_SRC ${MACPO_ROOT}/Benchmarks/Benchmarks.cpp)

# DPSO1 / GFPDO：与 MACPO 相同用 mpirun -n <group_num> 启动；算法主体仍在 rank0 执行（协同进化实现）
add_executable(DPSO1 ${MACPO_ROOT}/DPSO1.cpp ${BENCH_SRC})
target_link_libraries(DPSO1 PRIVATE Eigen3::Eigen MPI::MPI_CXX)
target_include_directories(DPSO1 PRIVATE ${MACPO_ROOT})

add_executable(GFPDO_overlap ${MACPO_ROOT}/GFPDO_overlap.cpp ${BENCH_SRC})
target_link_libraries(GFPDO_overlap PRIVATE Eigen3::Eigen MPI::MPI_CXX)
target_include_directories(GFPDO_overlap PRIVATE ${MACPO_ROOT})

# MACPO 主程序（与 readme 一致）
add_executable(MACPO ${MACPO_ROOT}/MACPO.cpp ${BENCH_SRC})
target_link_libraries(MACPO PRIVATE Eigen3::Eigen MPI::MPI_CXX)
target_include_directories(MACPO PRIVATE ${MACPO_ROOT})
