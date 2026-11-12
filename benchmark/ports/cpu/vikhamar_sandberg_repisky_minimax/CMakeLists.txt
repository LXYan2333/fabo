if(NOT TARGET hwy::hwy)
    find_package(hwy CONFIG REQUIRED)
endif()
find_library(FAST_BOYS_MVEC_LIBRARY NAMES mvec REQUIRED)

add_library(fast_boys_benchmark_vikhamar_sandberg_repisky INTERFACE)
target_include_directories(
    fast_boys_benchmark_vikhamar_sandberg_repisky
    INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/source"
)
target_link_libraries(
    fast_boys_benchmark_vikhamar_sandberg_repisky INTERFACE
    hwy::hwy
    "${FAST_BOYS_MVEC_LIBRARY}"
)

add_library(vikhamar-sandberg-repisky-benchmark-adapter SHARED
    benchmark_adapter.cc
)
target_compile_features(
    vikhamar-sandberg-repisky-benchmark-adapter PRIVATE cxx_std_20
)
# The authors' ancillary GCC build uses -O3 -ffast-math -fopenacc. This is an
# explicit Highway SIMD port rather than OpenACC source, so retain its
# optimization and fast-math choices and use the host ISA instead of OpenACC.
target_compile_options(
    vikhamar-sandberg-repisky-benchmark-adapter PRIVATE
    -O3
    -ffast-math
)
fast_boys_apply_benchmark_architecture(vikhamar-sandberg-repisky-benchmark-adapter)
target_compile_definitions(
    vikhamar-sandberg-repisky-benchmark-adapter PRIVATE NDEBUG
)
target_link_libraries(vikhamar-sandberg-repisky-benchmark-adapter PRIVATE
    benchmark::benchmark
    fast-boys-library-comparison-common
    fast_boys_benchmark_vikhamar_sandberg_repisky
)

add_executable(vikhamar-sandberg-repisky-minimax-correctness
    "${CMAKE_CURRENT_SOURCE_DIR}/../vikhamar-sandberg-repisky-minimax-correctness.cc"
)
target_compile_features(
    vikhamar-sandberg-repisky-minimax-correctness PRIVATE cxx_std_20
)
# Match the optimization/math policy of the authors' ancillary GCC build. The
# OpenACC flag does not apply to this explicit Highway SIMD implementation.
target_compile_options(vikhamar-sandberg-repisky-minimax-correctness PRIVATE
    -O3
    -ffast-math
)
fast_boys_apply_benchmark_architecture(vikhamar-sandberg-repisky-minimax-correctness)
target_compile_definitions(
    vikhamar-sandberg-repisky-minimax-correctness PRIVATE NDEBUG
)
target_link_libraries(vikhamar-sandberg-repisky-minimax-correctness PRIVATE
    fast_boys_benchmark_vikhamar_sandberg_repisky
    PkgConfig::GMP
)

add_test(
    NAME vikhamar-sandberg-repisky-minimax-correctness
    COMMAND vikhamar-sandberg-repisky-minimax-correctness
)
