cmake_minimum_required(VERSION 3.24)
project(HestonPricer VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Compiler flags for optimization
if(MSVC)
    # MSVC uses /O2 for max speed, /arch:AVX2 for SIMD, and /fp:fast for fast math
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /O2 /arch:AVX2 /fp:fast")
else()
    # GCC/Clang optimization flags
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -ffast-math")
endif()

include(FetchContent)

# 1. GoogleTest
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# 2. Google Benchmark
set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "Disable benchmark testing" FORCE)
set(BENCHMARK_ENABLE_INSTALL OFF CACHE BOOL "Disable benchmark install" FORCE)
set(BENCHMARK_ENABLE_WERROR OFF CACHE BOOL "Disable Werror" FORCE)
FetchContent_Declare(
  googlebenchmark
  URL https://github.com/google/benchmark/archive/refs/tags/v1.8.3.zip
)
FetchContent_MakeAvailable(googlebenchmark)

# 3. Pybind11
FetchContent_Declare(
  pybind11
  URL https://github.com/pybind/pybind11/archive/refs/tags/v2.11.1.zip
)
FetchContent_MakeAvailable(pybind11)

# Include directories
include_directories(include)

# Core Library
add_library(heston_core src/heston.cpp)

# Tests
enable_testing()
add_executable(heston_test tests/pricer_test.cpp)
target_link_libraries(heston_test PRIVATE heston_core GTest::gtest_main)
include(GoogleTest)
gtest_discover_tests(heston_test)

# Benchmark
add_executable(heston_bench benchmarks/pricer_bench.cpp)
target_link_libraries(heston_bench PRIVATE heston_core benchmark::benchmark benchmark::benchmark_main)

# Python Bindings
pybind11_add_module(fast_pricer python/bindings.cpp)
target_link_libraries(fast_pricer PRIVATE heston_core)

