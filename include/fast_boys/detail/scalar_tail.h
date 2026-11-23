#ifndef FAST_BOYS_DETAIL_SCALAR_TAIL_H_
#define FAST_BOYS_DETAIL_SCALAR_TAIL_H_
#include "fast_boys/detail/binary64.h"
#include "fast_boys/detail/assert.h"
namespace fast_boys::scalar {
// Compact tail: the model reconstructs coefficients with integer patches.
// It tabulates the complete integral A_n(u), NOT the Boys function F_n(u).
template <class Tail> class LargeArgumentFallback {
public:
  FAST_BOYS_HD explicit constexpr LargeArgumentFallback(TableView<Tail> table)
      : table_(table) {}
  template <int First, int Limit>
  FAST_BOYS_HD inline void evaluate(double x, int last,
                                    double *FAST_BOYS_RESTRICT out,
                                    std::size_t stride) const {
    static_assert(Tail::first <= First && First <= Limit && Limit <= Tail::last,
                  "tail does not cover requested orders");
    FAST_BOYS_ASSERT(First <= last && last <= Limit && stride > 0);
    using O = fast_boys::detail::Binary64;
    const auto bits = O::bits(x);
    if (bits == 0x7ff0000000000000ULL) {
      for (int n = First; n <= last; ++n)
        out[(n - First) * stride] = 0.0;
      return;
    }
    if ((bits >> 63) || bits >= 0x7ff0000000000000ULL ||
        !(x > Tail::minimum_x)) {
      for (int n = First; n <= last; ++n)
        out[(n - First) * stride] = O::value(0x7ff8000000000000ULL);
      return;
    }
    const int exponent = int(bits >> 52) - 1023;
    const int k = exponent / 2; // x > 1e7: exponent is positive.
    const double u = O::value((bits & 0xfffffffffffffULL) |
                              (std::uint64_t(1023 + (exponent & 1)) << 52));
    Tail::template evaluate<O, First, Limit>(table_.data(), u, k, last, out,
                                             stride);
  }

private:
  TableView<Tail> table_;
};
} // namespace fast_boys::scalar
#endif
