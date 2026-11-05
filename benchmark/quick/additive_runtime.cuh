#ifndef FAST_BOYS_QUICK_ADDITIVE_RUNTIME_CUH_
#define FAST_BOYS_QUICK_ADDITIVE_RUNTIME_CUH_
#pragma push_macro("min")
#pragma push_macro("max")
#undef min
#undef max
#include <cstdio>
#include <cstdlib>
#include "additive_binding.cuh"
#pragma pop_macro("max")
#pragma pop_macro("min")

extern "C" const std::uint64_t *fabo_quick_host_table(int, std::size_t *);

static void fabo_quick_check(cudaError_t status) {
  if (status != cudaSuccess) {
    std::fprintf(stderr, "FABO QUICK initialization: %s\n",
                 cudaGetErrorString(status));
    std::exit(2);
  }
}

static const std::uint64_t *fabo_quick_upload(int last) {
  std::size_t bytes = 0;
  const auto *host = fabo_quick_host_table(last, &bytes);
  if (!host || !bytes) {
    std::fputs("Missing FABO QUICK table\n", stderr);
    std::exit(2);
  }
  void *device = nullptr;
  fabo_quick_check(cudaMalloc(&device, bytes));
  fabo_quick_check(cudaMemcpy(device, host, bytes, cudaMemcpyHostToDevice));
  return static_cast<const std::uint64_t *>(device);
}

// Called once per QUICK device initialization, not per integral/Fock build.
// Allocations have device-context lifetime, like QUICK's own constant handles.
extern "C" void fabo_quick_boys_init_() {
  const std::uint64_t *main[3] = {fabo_quick_upload(4), nullptr, nullptr};
#ifdef ENABLEF
  main[1] = main[2] = fabo_quick_upload(12);
#else
  main[1] = fabo_quick_upload(8);
#endif
#ifndef FAST_BOYS_COMBINED_TABLE
#ifdef FAST_BOYS_RANGE_TAILS
  const std::uint64_t *tail[3]={fabo_quick_upload(-4),nullptr,nullptr};
#ifdef ENABLEF
  tail[1]=tail[2]=fabo_quick_upload(-12);
#else
  tail[1]=fabo_quick_upload(-8);
#endif
#else
  const auto *tail = fabo_quick_upload(-1);
#endif
#endif
  fabo_quick_check(cudaMemcpyToSymbol(fabo_quick_main, main, sizeof(main)));
#ifndef FAST_BOYS_COMBINED_TABLE
  fabo_quick_check(cudaMemcpyToSymbol(fabo_quick_tail, &tail, sizeof(tail)));
#endif
}
#endif
