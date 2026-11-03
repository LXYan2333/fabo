#ifndef FABO_QUICK_PROBE_RUNTIME_H_
#define FABO_QUICK_PROBE_RUNTIME_H_
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <time.h>
static void fabo_check(cudaError_t status) {
  if (status != cudaSuccess) {
    std::fprintf(stderr, "QUICK probe: %s\n", cudaGetErrorString(status));
    std::exit(2);
  }
}
#ifdef FABO_QUICK_REFERENCE
#include "cuda/reference_runtime.h"
#endif
extern "C" void fabo_probe_init_() {
#ifdef FABO_QUICK_REFERENCE
  fabo_reference_init();
#endif
} // Timed variants uploaded their tables during device initialization.
extern "C" void fabo_probe_counts_() {} // No instrumentation in timing kernels.
extern "C" void fabo_request_begin_() {} // SCF calibration collects no Boys requests.
extern "C" void fabo_request_end_() {}
extern "C" void fabo_probe_sync_() {
  const auto status = cudaDeviceSynchronize();
  if (status != cudaSuccess) {
    std::fprintf(stderr, "QUICK probe: %s\n", cudaGetErrorString(status));
    std::exit(2);
  }
#ifdef FABO_QUICK_REFERENCE
  fabo_reference_check();
#endif
}
extern "C" void fabo_probe_clock_(double *value) {
  struct timespec stamp;
  if (clock_gettime(CLOCK_MONOTONIC, &stamp)) {
    std::perror("clock_gettime");
    std::exit(2);
  }
  *value = double(stamp.tv_sec) + double(stamp.tv_nsec) * 1e-9;
}
#endif
