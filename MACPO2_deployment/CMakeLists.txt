cmake_minimum_required(VERSION 3.10 FATAL_ERROR)
project(MACPO2)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# -----------------------------------------------------------------------------
# MPI — Windows: install MS-MPI SDK, then e.g.
#   cmake -S . -B build -G "Visual Studio 17 2022" -A x64
# Unix/macOS: use MPI wrapper or:
#   cmake -S . -B build -DCMAKE_CXX_COMPILER=mpicxx
# Do NOT hard-code mpicxx here; it breaks MSVC on Windows.
# -----------------------------------------------------------------------------
find_package(MPI REQUIRED)
include_directories(${MPI_INCLUDE_PATH})

# Eigen3 — set EIGEN3_INCLUDE_DIR or CMAKE_PREFIX_PATH if find_package fails
find_package(Eigen3 REQUIRED)
include_directories(${EIGEN3_INCLUDE_DIR})

# Project root so #include "Benchmarks/..." and "components/..." resolve
set(MACPO2_ROOT ${CMAKE_CURRENT_SOURCE_DIR})

# Build MACPO2_LLSO (RL-MACPO + LLSO, synced from RL-MACPO/MACPO_simplified.cpp)
add_executable(MACPO2_LLSO
    Benchmarks/Benchmarks.cpp
    MACPO_LLSO.cpp
    components/evaluator.cpp
)
target_include_directories(MACPO2_LLSO PRIVATE ${MACPO2_ROOT})
target_link_libraries(MACPO2_LLSO
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)

# Build MACPO2_CSO (RL-MACPO + CSO, synced from RL-MACPO/MACPO_CSO_properly_fixed.cpp)
add_executable(MACPO2_CSO
    Benchmarks/Benchmarks.cpp
    MACPO_CSO.cpp
    components/evaluator.cpp
)
target_include_directories(MACPO2_CSO PRIVATE ${MACPO2_ROOT})
target_link_libraries(MACPO2_CSO
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)
