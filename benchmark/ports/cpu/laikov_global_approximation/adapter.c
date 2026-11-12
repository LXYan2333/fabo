#include "adapter.h"

#include <quadmath.h>

typedef __float128 real;

real c1fn(int L);
real x1fn_53(int L);
int z1pqfn(real** coefficients, int* root_counts, int L, int degree);
int fast_boys_laikov_initialize(fast_boys_laikov_parameters* parameters,
                                const int maximum_order) {
  // t_fn.c's nc53 table selects the degrees used for the 53-bit results in
  // Table I. Repeated entries are intentional.
  static const int degrees[37] = {
      10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13,
      13, 13, 13, 13, 13, 14, 14, 14, 14, 14, 14, 14, 14,
      14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
  };

  if (parameters == NULL || maximum_order < 0 || maximum_order > 36) {
    return -1;
  }

  parameters->maximum_order = maximum_order;
  parameters->degree = degrees[maximum_order];
  // z:2 in the supplied test driver selects the root-factor form from
  // z1nm4.c, corresponding to Eqs. (12)--(14) in the paper.
  parameters->root_counts[2] = 1;

  real* source = NULL;
  const int accuracy_bits =
      z1pqfn(&source, parameters->root_counts, maximum_order,
              parameters->degree);
  if (accuracy_bits <= 0 || source == NULL) {
    return -2;
  }

  const int degree = parameters->degree;
  for (int index = 0; index <= 1 + degree + degree; ++index) {
    parameters->coefficients[index] = (double)source[index];
  }
  parameters->coefficients[2 + degree + degree] =
      (double)c1fn(maximum_order);
  parameters->coefficients[3 + degree + degree] =
      (double)x1fn_53(maximum_order);
  return accuracy_bits;
}
