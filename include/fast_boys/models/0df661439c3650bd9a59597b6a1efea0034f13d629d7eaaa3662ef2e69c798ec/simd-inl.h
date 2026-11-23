#if defined(                                                                               \
    FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_) == \
    defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#undef FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#else
#define FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec/model.h"
#if HWY_NATIVE_FMA
HWY_BEFORE_NAMESPACE();
namespace fast_boys {
namespace simd {
namespace HWY_NAMESPACE {
template <>
struct Kernel<
    fast_boys::models::
        m_0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec::
            Model> {
  using M = fast_boys::models::
      m_0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec::Model;
  template <int First, int Last, bool Software, class D, class... Outputs>
  static HWY_INLINE void run(D, const std::uint64_t *data, hn::VFromD<D> x,
                             Outputs &HWY_RESTRICT... out) {
    using Op = detail::Ops<D>;
    using V = hn::VFromD<D>;
    using U = typename Op::U;
    U row FAST_BOYS_INDETERMINATE;
    U k FAST_BOYS_INDETERMINATE;
    V h FAST_BOYS_INDETERMINATE;
    Op::template PrepareCombinedCoordinates<M>(x, row, h, k);
    static_assert(M::word_count - 1 <= INT64_MAX,
                  "gather index exceeds signed range");
    const auto two_k = hn::Add(k, k);
    auto scale_power = k;
    V c0 FAST_BOYS_INDETERMINATE;
    V c1 FAST_BOYS_INDETERMINATE;
    V c2 FAST_BOYS_INDETERMINATE;
    V c3 FAST_BOYS_INDETERMINATE;
    V c4 FAST_BOYS_INDETERMINATE;
    V c5 FAST_BOYS_INDETERMINATE;
    V a2 FAST_BOYS_INDETERMINATE;
    V a3 FAST_BOYS_INDETERMINATE;
    V a4 FAST_BOYS_INDETERMINATE;
    U w0 FAST_BOYS_INDETERMINATE;
    if constexpr (First <= 0 && 0 <= Last) {
      if constexpr (0 > M::high_before(First, 0))
        c0 = Op::Float(hn::Sub(Op::template Gather<Software, M::word_count - 1>(
                                   data, hn::Add(row, Op::SU(1))),
                               Op::SU(1)));
      if constexpr (1 > M::high_before(First, 0))
        c1 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(2))));
      if constexpr (2 > M::high_before(First, 0))
        c2 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(3))));
      if constexpr (3 > M::high_before(First, 0))
        c3 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(4))));
      if constexpr (4 > M::high_before(First, 0))
        c4 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(5))));
      if constexpr (First == 0 || 0 == 0)
        w0 = Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(0)));
      if constexpr (2 > M::degree_before(First, 0))
        a2 = Op::RoundedMul(h, Op::S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 0))
        a3 = Op::RoundedMul(h, Op::S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 0))
        a4 = Op::RoundedMul(h, Op::S(0x1.0000000000000p-2));
      V q = c4;
      q = Op::Fma(a4, q, c3);
      q = Op::Fma(a3, q, c2);
      q = Op::Fma(a2, q, c1);
      const auto hi = Op::Bits(c0);
      const auto value = Op::RoundedAdd(
          Op::Float(hn::Add(hi, Op::SU(1))),
          Op::FmaSub(h, q, Op::template CorrectionFromWord<0>(hi, w0)));
      Op::template At<0 - First>(out...) =
          Op::Scale(Op::Bits(value), scale_power);
    }
    if constexpr (0 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 1 && 1 <= Last) {
      if constexpr (1 > M::high_before(First, 1))
        c1 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(2))));
      if constexpr (2 > M::high_before(First, 1))
        c2 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(3))));
      if constexpr (3 > M::high_before(First, 1))
        c3 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(4))));
      if constexpr (4 > M::high_before(First, 1))
        c4 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(5))));
      if constexpr (5 > M::high_before(First, 1))
        c5 = Op::Float(Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(6))));
      if constexpr (First == 1 || 1 == 0)
        w0 = Op::template Gather<Software, M::word_count - 1>(
            data, hn::Add(row, Op::SU(0)));
      if constexpr (2 > M::degree_before(First, 1))
        a2 = Op::RoundedMul(h, Op::S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 1))
        a3 = Op::RoundedMul(h, Op::S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 1))
        a4 = Op::RoundedMul(h, Op::S(0x1.0000000000000p-2));
      V q = c5;
      q = Op::Fma(a4, q, c4);
      q = Op::Fma(a3, q, c3);
      q = Op::Fma(a2, q, c2);
      const auto hi = Op::Bits(c1);
      const auto value = Op::RoundedAdd(
          Op::Float(hn::Add(hi, Op::SU(1))),
          Op::FmaSub(h, q, Op::template CorrectionFromWord<1>(hi, w0)));
      Op::template At<1 - First>(out...) =
          Op::Scale(Op::Bits(value), scale_power);
    }
    if constexpr (1 < Last)
      scale_power = hn::Add(scale_power, two_k);
  }
};
} // namespace HWY_NAMESPACE
} // namespace simd
} // namespace fast_boys
HWY_AFTER_NAMESPACE();
#endif // HWY_NATIVE_FMA
#endif
