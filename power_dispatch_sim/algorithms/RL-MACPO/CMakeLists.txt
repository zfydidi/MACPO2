cmake_minimum_required(VERSION 3.10 FATAL_ERROR)
project(MACPO2)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# MPI — do not hard-code mpicxx (breaks MSVC on Windows)
find_package(MPI REQUIRED)
include_directories(${MPI_INCLUDE_PATH})

find_package(Eigen3 REQUIRED)
include_directories(${EIGEN3_INCLUDE_DIR})

set(MACPO2_ROOT ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(MACPO_simplified
    Benchmarks/Benchmarks.cpp
    MACPO_simplified.cpp
    components/evaluator.cpp
)
target_include_directories(MACPO_simplified PRIVATE ${MACPO2_ROOT})
target_link_libraries(MACPO_simplified
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)

if(EXISTS ${CMAKE_SOURCE_DIR}/MACPO_CSO_properly_fixed.cpp)
    add_executable(MACPO_CSO_properly_fixed
        Benchmarks/Benchmarks.cpp
        MACPO_CSO_properly_fixed.cpp
        components/evaluator.cpp
    )
    target_include_directories(MACPO_CSO_properly_fixed PRIVATE ${MACPO2_ROOT})
    target_link_libraries(MACPO_CSO_properly_fixed
        PRIVATE
        Eigen3::Eigen
        ${MPI_LIBRARIES}
    )
endif()

# === Power Grid Scenario (added by power_dispatch_sim/setup.sh) ===
add_executable(RL_MACPO_power
    Benchmarks/Benchmarks.cpp
    RL_MACPO_power.cpp
    components/evaluator.cpp
)
target_include_directories(RL_MACPO_power PRIVATE ${MACPO2_ROOT})
target_link_libraries(RL_MACPO_power
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)

# === NDO Scenarios (added by power_dispatch_sim/setup.sh) ===
add_executable(RL_MACPO_ndo
    Benchmarks/Benchmarks.cpp
    RL_MACPO_ndo.cpp
    components/evaluator.cpp
)
target_include_directories(RL_MACPO_ndo PRIVATE ${MACPO2_ROOT})
target_link_libraries(RL_MACPO_ndo
    PRIVATE
    Eigen3::Eigen
    ${MPI_LIBRARIES}
)
