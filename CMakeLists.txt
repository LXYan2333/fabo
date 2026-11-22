cmake_minimum_required(VERSION 3.23)
project(fabo LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
option(FABO_ENABLE_SIMD "Provide the Highway SIMD target" ON)
option(FABO_ENABLE_CUDA "Provide the CUDA target and runtime dependency" OFF)
option(FABO_ENABLE_INSTALL "Install FABO headers and CMake targets" ${PROJECT_IS_TOP_LEVEL})

add_library(fabo INTERFACE)
add_library(fabo::fabo ALIAS fabo)
target_compile_features(fabo INTERFACE cxx_std_17)
include(cmake/headers.cmake)
target_sources(fabo INTERFACE FILE_SET HEADERS
    BASE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/include"
    FILES ${FABO_PUBLIC_HEADERS})

if(FABO_ENABLE_SIMD)
    if(NOT TARGET hwy::hwy)
        find_package(hwy 1.4.0 CONFIG REQUIRED)
    endif()
    add_library(fabo_simd INTERFACE)
    add_library(fabo::simd ALIAS fabo_simd)
    set_target_properties(fabo_simd PROPERTIES EXPORT_NAME simd)
    target_link_libraries(fabo_simd INTERFACE fabo::fabo hwy::hwy)
endif()

if(FABO_ENABLE_CUDA)
    if(NOT TARGET CUDA::cudart)
        find_package(CUDAToolkit REQUIRED)
    endif()
    add_library(fabo_cuda INTERFACE)
    add_library(fabo::cuda ALIAS fabo_cuda)
    set_target_properties(fabo_cuda PROPERTIES EXPORT_NAME cuda)
    target_compile_features(fabo_cuda INTERFACE cuda_std_17)
    target_link_libraries(fabo_cuda INTERFACE fabo::fabo CUDA::cudart)
endif()

if(NOT FABO_ENABLE_INSTALL)
    return()
endif()

install(TARGETS fabo EXPORT faboCoreTargets FILE_SET HEADERS
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
install(EXPORT faboCoreTargets NAMESPACE fabo::
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/fabo")
if(FABO_ENABLE_SIMD)
    install(TARGETS fabo_simd EXPORT faboSimdTargets)
    install(EXPORT faboSimdTargets NAMESPACE fabo::
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/fabo")
endif()
if(FABO_ENABLE_CUDA)
    install(TARGETS fabo_cuda EXPORT faboCudaTargets)
    install(EXPORT faboCudaTargets NAMESPACE fabo::
        DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/fabo")
endif()

configure_package_config_file(cmake/faboConfig.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/faboConfig.cmake"
    INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/fabo")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/faboConfig.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/fabo")
install(FILES include/fast_boys/README.md include/fast_boys/SIMD.md
    DESTINATION "${CMAKE_INSTALL_DOCDIR}/api")
install(FILES LICENSE LICENSES/MPL-2.0.txt LICENSES/LGPL-3.0-only.txt
    LICENSES/GPL-3.0-only.txt DESTINATION "${CMAKE_INSTALL_DOCDIR}/licenses")
