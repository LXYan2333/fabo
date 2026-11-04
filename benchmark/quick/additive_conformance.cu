// Standalone binding smoke test; no SCF calculation or performance timing.
#include <cuda_runtime.h>
#define min(a, b) quick_min_macro(a, b)
#define max(a, b) quick_max_macro(a, b)
#include "additive_runtime.cuh"
#ifndef min
#error QUICK macro was not restored
#endif
#undef min
#undef max
#include <vector>

template <int Family>
__global__ void evaluate(double *out) {
  const unsigned lane = blockIdx.x * blockDim.x + threadIdx.x;
  if (lane >= 47) return; // Partial final warp; heterogeneous requests.
  constexpr int last = FaboQuickFamily<Family>::last;
  const double inputs[] = {0., 0.01, 1., 100., 1e7, 1e8};
  FaboQuickFmT<Family>(lane % (last + 1), inputs[lane % 6], out + lane);
}

template <int Family> static bool check() {
  using M = typename FaboQuickFamily<Family>::Model;
#ifdef FAST_BOYS_RANGE_TAILS
  using T = fast_boys::selected::Tail<M::last>;
  constexpr int tail_key = -M::last;
#else
  using T = fast_boys::selected::Tail;
  constexpr int tail_key = -1;
#endif
  using O = fast_boys::detail::Binary64;
  constexpr unsigned stride = 64;
  std::vector<double> values(13 * stride, -1.);
  double *out = nullptr;
  fabo_quick_check(cudaMalloc(&out, values.size() * sizeof(double)));
  fabo_quick_check(cudaMemcpy(out, values.data(), values.size() * sizeof(double),
                              cudaMemcpyHostToDevice));
  evaluate<Family><<<2, 32>>>(out);
  fabo_quick_check(cudaGetLastError());
  fabo_quick_check(cudaMemcpy(values.data(), out, values.size() * sizeof(double),
                              cudaMemcpyDeviceToHost));
  fabo_quick_check(cudaFree(out));
  std::size_t bytes;
  auto evaluator = fast_boys::cuda::make_evaluator(
      fast_boys::TableView<M>::from_pointer(fabo_quick_host_table(M::last, &bytes)),
      fast_boys::TableView<T>::from_pointer(fabo_quick_host_table(tail_key, &bytes)));
  const double inputs[] = {0., 0.01, 1., 100., 1e7, 1e8};
  for (unsigned lane = 0; lane < stride; ++lane) {
    double expected[13];
    for (auto &value : expected) value = -1.;
    if (lane < 47)
      evaluator.template evaluate<0>(inputs[lane % 6], lane % (M::last + 1), expected);
    for (unsigned n = 0; n < 13; ++n)
      if (O::bits(values[n * stride + lane]) != O::bits(expected[n])) return false;
  }
  return true;
}

int main() {
  fabo_quick_boys_init_();
  if (!check<4>() || !check<8>()) return 1;
#ifdef ENABLEF
  if (!check<12>()) return 1;
#endif
  std::puts("QUICK additive binding: PASS");
}
