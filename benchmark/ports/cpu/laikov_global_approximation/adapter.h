#ifndef FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_ADAPTER_H_
#define FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_ADAPTER_H_

#ifdef __cplusplus
extern "C" {
#endif

typedef struct fast_boys_laikov_parameters {
  double coefficients[44];
  int root_counts[3];
  int maximum_order;
  int degree;
} fast_boys_laikov_parameters;

int fast_boys_laikov_initialize(fast_boys_laikov_parameters* parameters,
                                int maximum_order);

#ifdef __cplusplus
}
#endif

#endif  // FAST_BOYS_BENCHMARK_LAIKOV_GLOBAL_APPROXIMATION_ADAPTER_H_
