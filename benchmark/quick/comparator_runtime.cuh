#ifndef FABO_QUICK_COMPARATOR_RUNTIME_CUH_
#define FABO_QUICK_COMPARATOR_RUNTIME_CUH_
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include <cstdio>
#include <cstdlib>
#include "comparator_binding.cuh"

static void fabo_comparator_check(cudaError_t status) {
  if (status != cudaSuccess) {
    std::fprintf(stderr, "QUICK comparator initialization: %s\n", cudaGetErrorString(status));
    std::exit(2);
  }
}

// One context-lifetime global allocation during QUICK initialization, outside
// the timed SCF loop. File contents are generated and hashed by the workflow.
extern "C" void fabo_comparator_init_() {
#if !defined(FABO_COMPARATOR_VSR)
#if defined(FABO_COMPARATOR_LIBINTX)
  constexpr std::size_t count = 8 * 13 * 819;
#else
  constexpr std::size_t count = 30720;
#endif
  const char *path = std::getenv("FABO_COMPARATOR_TABLE");
  FILE *file = path ? std::fopen(path, "rb") : nullptr;
  if (!file) { std::fputs("FABO_COMPARATOR_TABLE is required\n", stderr); std::exit(2); }
  double *host = new double[count];
  const bool valid = std::fread(host, sizeof(double), count, file) == count && std::fgetc(file) == EOF;
  if (std::fclose(file) != 0 || !valid) { std::fputs("Invalid comparator table\n", stderr); std::exit(2); }
  double *device = nullptr;
  fabo_comparator_check(cudaMalloc(&device, count * sizeof(double)));
  fabo_comparator_check(cudaMemcpy(device, host, count * sizeof(double), cudaMemcpyHostToDevice));
  fabo_comparator_check(cudaMemcpyToSymbol(fabo_comparator_table, &device, sizeof(device)));
  delete[] host;
#endif
}
#pragma pop_macro("max")
#pragma pop_macro("min")
#endif
