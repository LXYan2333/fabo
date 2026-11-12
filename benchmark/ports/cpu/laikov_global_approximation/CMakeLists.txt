if(NOT CMAKE_C_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR
        "Laikov's supplied source uses GNU __float128 and Q-suffixed literals")
endif()

if(NOT TARGET hwy::hwy)
    find_package(hwy CONFIG REQUIRED)
endif()
find_library(FAST_BOYS_LAIKOV_MVEC_LIBRARY NAMES mvec REQUIRED)

add_library(laikov-global-approximation STATIC
    adapter.c
    source/c0n4.c
    source/z1nm4.c
)
set_target_properties(laikov-global-approximation PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)
target_include_directories(laikov-global-approximation PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}"
)
# The supplementary source's makefile defines CC=gcc -O2. Apply that exact
# optimization choice privately to the author code and its thin adapter, then
# apply the explicit benchmark ISA required by Highway.
target_compile_options(laikov-global-approximation PRIVATE -O2)
fast_boys_apply_benchmark_architecture(laikov-global-approximation)
target_link_libraries(laikov-global-approximation PUBLIC
    hwy::hwy
    "${FAST_BOYS_LAIKOV_MVEC_LIBRARY}"
    quadmath
    m
)

add_library(laikov-global-approximation-benchmark-adapter SHARED
    benchmark_adapter.cc
)
target_compile_features(
    laikov-global-approximation-benchmark-adapter PRIVATE cxx_std_20
)
# The supplied makefile uses -O2; select the benchmark host ISA as above.
target_compile_options(
    laikov-global-approximation-benchmark-adapter PRIVATE
    -O2
)
fast_boys_apply_benchmark_architecture(laikov-global-approximation-benchmark-adapter)
target_compile_definitions(
    laikov-global-approximation-benchmark-adapter PRIVATE NDEBUG
)
target_link_libraries(
    laikov-global-approximation-benchmark-adapter PRIVATE
    benchmark::benchmark
    fast-boys-library-comparison-common
    laikov-global-approximation
)

add_executable(laikov-global-approximation-correctness
    "${CMAKE_CURRENT_SOURCE_DIR}/../laikov-global-approximation-correctness.cc"
)
target_compile_features(
    laikov-global-approximation-correctness PRIVATE cxx_std_20
)
# Use the author's documented optimization and the benchmark host ISA for the
# caller without leaking either option to other implementations.
target_compile_options(laikov-global-approximation-correctness PRIVATE
    -O2
)
fast_boys_apply_benchmark_architecture(laikov-global-approximation-correctness)
target_link_libraries(laikov-global-approximation-correctness PRIVATE
    laikov-global-approximation
    PkgConfig::GMP
)

add_test(
    NAME laikov-global-approximation-correctness
    COMMAND laikov-global-approximation-correctness
)
