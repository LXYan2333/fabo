#if defined(                                                                               \
    FAST_BOYS_SIMD_6F9D84D52A2DF61E5619F17AB8159500FC0F7A4D8DB82C5003B18EA0A4ADEADA_H_) == \
    defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_6F9D84D52A2DF61E5619F17AB8159500FC0F7A4D8DB82C5003B18EA0A4ADEADA_H_
#undef FAST_BOYS_SIMD_6F9D84D52A2DF61E5619F17AB8159500FC0F7A4D8DB82C5003B18EA0A4ADEADA_H_
#else
#define FAST_BOYS_SIMD_6F9D84D52A2DF61E5619F17AB8159500FC0F7A4D8DB82C5003B18EA0A4ADEADA_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/6f9d84d52a2df61e5619f17ab8159500fc0f7a4d8db82c5003b18ea0a4adeada/model.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys {
namespace simd {
namespace HWY_NAMESPACE {
template <>
struct Kernel<
    fast_boys::models::
        m_6f9d84d52a2df61e5619f17ab8159500fc0f7a4d8db82c5003b18ea0a4adeada::
            Model> {
  using M = fast_boys::models::
      m_6f9d84d52a2df61e5619f17ab8159500fc0f7a4d8db82c5003b18ea0a4adeada::Model;
  template <int First, int Last, bool Software, class... Outputs>
  static HWY_INLINE void run(const std::uint64_t *data, const V x,
                             Outputs &HWY_RESTRICT... out) {
    using namespace detail;
    U row FAST_BOYS_INDETERMINATE;
    U k FAST_BOYS_INDETERMINATE;
    V h FAST_BOYS_INDETERMINATE;
    PrepareCombinedCoordinates<M>(x, row, h, k);
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
    V c6 FAST_BOYS_INDETERMINATE;
    V c7 FAST_BOYS_INDETERMINATE;
    V c8 FAST_BOYS_INDETERMINATE;
    V c9 FAST_BOYS_INDETERMINATE;
    V c10 FAST_BOYS_INDETERMINATE;
    V c11 FAST_BOYS_INDETERMINATE;
    V c12 FAST_BOYS_INDETERMINATE;
    V c13 FAST_BOYS_INDETERMINATE;
    V c14 FAST_BOYS_INDETERMINATE;
    V c15 FAST_BOYS_INDETERMINATE;
    V c16 FAST_BOYS_INDETERMINATE;
    V c17 FAST_BOYS_INDETERMINATE;
    V c18 FAST_BOYS_INDETERMINATE;
    V c19 FAST_BOYS_INDETERMINATE;
    V c20 FAST_BOYS_INDETERMINATE;
    V c21 FAST_BOYS_INDETERMINATE;
    V c22 FAST_BOYS_INDETERMINATE;
    V c23 FAST_BOYS_INDETERMINATE;
    V c24 FAST_BOYS_INDETERMINATE;
    V c25 FAST_BOYS_INDETERMINATE;
    V c26 FAST_BOYS_INDETERMINATE;
    V c27 FAST_BOYS_INDETERMINATE;
    V c28 FAST_BOYS_INDETERMINATE;
    V c29 FAST_BOYS_INDETERMINATE;
    V a2 FAST_BOYS_INDETERMINATE;
    V a3 FAST_BOYS_INDETERMINATE;
    V a4 FAST_BOYS_INDETERMINATE;
    V a5 FAST_BOYS_INDETERMINATE;
    V a6 FAST_BOYS_INDETERMINATE;
    V a7 FAST_BOYS_INDETERMINATE;
    U w0 FAST_BOYS_INDETERMINATE;
    U w1 FAST_BOYS_INDETERMINATE;
    U w2 FAST_BOYS_INDETERMINATE;
    if constexpr (First <= 0 && 0 <= Last) {
      if constexpr (0 > M::high_before(First, 0))
        c0 = Float(hn::Sub(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(1))),
            SU(1)));
      if constexpr (1 > M::high_before(First, 0))
        c1 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(2))));
      if constexpr (2 > M::high_before(First, 0))
        c2 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(3))));
      if constexpr (3 > M::high_before(First, 0))
        c3 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(4))));
      if constexpr (4 > M::high_before(First, 0))
        c4 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(5))));
      if constexpr (5 > M::high_before(First, 0))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (First == 0 || 0 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 0))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 0))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 0))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 0))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      V q = c5;
      q = Fma(a5, q, c4);
      q = Fma(a4, q, c3);
      q = Fma(a3, q, c2);
      q = Fma(a2, q, c1);
      const auto hi = Bits(c0);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<0>(hi, w0)));
      At<0 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (0 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 1 && 1 <= Last) {
      if constexpr (1 > M::high_before(First, 1))
        c1 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(2))));
      if constexpr (2 > M::high_before(First, 1))
        c2 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(3))));
      if constexpr (3 > M::high_before(First, 1))
        c3 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(4))));
      if constexpr (4 > M::high_before(First, 1))
        c4 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(5))));
      if constexpr (5 > M::high_before(First, 1))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (6 > M::high_before(First, 1))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (First == 1 || 1 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 1))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 1))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 1))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 1))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      V q = c6;
      q = Fma(a5, q, c5);
      q = Fma(a4, q, c4);
      q = Fma(a3, q, c3);
      q = Fma(a2, q, c2);
      const auto hi = Bits(c1);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<1>(hi, w0)));
      At<1 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (1 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 2 && 2 <= Last) {
      if constexpr (2 > M::high_before(First, 2))
        c2 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(3))));
      if constexpr (3 > M::high_before(First, 2))
        c3 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(4))));
      if constexpr (4 > M::high_before(First, 2))
        c4 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(5))));
      if constexpr (5 > M::high_before(First, 2))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (6 > M::high_before(First, 2))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (7 > M::high_before(First, 2))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (First == 2 || 2 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 2))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 2))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 2))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 2))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      V q = c7;
      q = Fma(a5, q, c6);
      q = Fma(a4, q, c5);
      q = Fma(a3, q, c4);
      q = Fma(a2, q, c3);
      const auto hi = Bits(c2);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<2>(hi, w0)));
      At<2 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (2 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 3 && 3 <= Last) {
      if constexpr (3 > M::high_before(First, 3))
        c3 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(4))));
      if constexpr (4 > M::high_before(First, 3))
        c4 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(5))));
      if constexpr (5 > M::high_before(First, 3))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (6 > M::high_before(First, 3))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (7 > M::high_before(First, 3))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (8 > M::high_before(First, 3))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (First == 3 || 3 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 3))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 3))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 3))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 3))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      V q = c8;
      q = Fma(a5, q, c7);
      q = Fma(a4, q, c6);
      q = Fma(a3, q, c5);
      q = Fma(a2, q, c4);
      const auto hi = Bits(c3);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<3>(hi, w0)));
      At<3 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (3 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 4 && 4 <= Last) {
      if constexpr (4 > M::high_before(First, 4))
        c4 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(5))));
      if constexpr (5 > M::high_before(First, 4))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (6 > M::high_before(First, 4))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (7 > M::high_before(First, 4))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (8 > M::high_before(First, 4))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (9 > M::high_before(First, 4))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 4))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (First == 4 || 4 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 4))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 4))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 4))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 4))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 4))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c10;
      q = Fma(a6, q, c9);
      q = Fma(a5, q, c8);
      q = Fma(a4, q, c7);
      q = Fma(a3, q, c6);
      q = Fma(a2, q, c5);
      const auto hi = Bits(c4);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<4>(hi, w0)));
      At<4 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (4 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 5 && 5 <= Last) {
      if constexpr (5 > M::high_before(First, 5))
        c5 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(6))));
      if constexpr (6 > M::high_before(First, 5))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (7 > M::high_before(First, 5))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (8 > M::high_before(First, 5))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (9 > M::high_before(First, 5))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 5))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 5))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (First == 5 || 5 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 5))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 5))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 5))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 5))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 5))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c11;
      q = Fma(a6, q, c10);
      q = Fma(a5, q, c9);
      q = Fma(a4, q, c8);
      q = Fma(a3, q, c7);
      q = Fma(a2, q, c6);
      const auto hi = Bits(c5);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<5>(hi, w0)));
      At<5 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (5 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 6 && 6 <= Last) {
      if constexpr (6 > M::high_before(First, 6))
        c6 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(7))));
      if constexpr (7 > M::high_before(First, 6))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (8 > M::high_before(First, 6))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (9 > M::high_before(First, 6))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 6))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 6))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 6))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (First == 6 || 6 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 6))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 6))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 6))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 6))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 6))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c12;
      q = Fma(a6, q, c11);
      q = Fma(a5, q, c10);
      q = Fma(a4, q, c9);
      q = Fma(a3, q, c8);
      q = Fma(a2, q, c7);
      const auto hi = Bits(c6);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<6>(hi, w0)));
      At<6 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (6 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 7 && 7 <= Last) {
      if constexpr (7 > M::high_before(First, 7))
        c7 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(8))));
      if constexpr (8 > M::high_before(First, 7))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (9 > M::high_before(First, 7))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 7))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 7))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 7))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 7))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (First == 7 || 7 == 0)
        w0 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(0)));
      if constexpr (2 > M::degree_before(First, 7))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 7))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 7))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 7))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 7))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c13;
      q = Fma(a6, q, c12);
      q = Fma(a5, q, c11);
      q = Fma(a4, q, c10);
      q = Fma(a3, q, c9);
      q = Fma(a2, q, c8);
      const auto hi = Bits(c7);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<7>(hi, w0)));
      At<7 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (7 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 8 && 8 <= Last) {
      if constexpr (8 > M::high_before(First, 8))
        c8 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(10))));
      if constexpr (9 > M::high_before(First, 8))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 8))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 8))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 8))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 8))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 8))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (First == 8 || 8 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 8))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 8))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 8))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 8))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 8))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c14;
      q = Fma(a6, q, c13);
      q = Fma(a5, q, c12);
      q = Fma(a4, q, c11);
      q = Fma(a3, q, c10);
      q = Fma(a2, q, c9);
      const auto hi = Bits(c8);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<0>(hi, w1)));
      At<8 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (8 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 9 && 9 <= Last) {
      if constexpr (9 > M::high_before(First, 9))
        c9 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(11))));
      if constexpr (10 > M::high_before(First, 9))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 9))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 9))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 9))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 9))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 9))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (First == 9 || 9 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 9))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 9))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 9))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 9))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 9))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c15;
      q = Fma(a6, q, c14);
      q = Fma(a5, q, c13);
      q = Fma(a4, q, c12);
      q = Fma(a3, q, c11);
      q = Fma(a2, q, c10);
      const auto hi = Bits(c9);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<1>(hi, w1)));
      At<9 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (9 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 10 && 10 <= Last) {
      if constexpr (10 > M::high_before(First, 10))
        c10 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(12))));
      if constexpr (11 > M::high_before(First, 10))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 10))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 10))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 10))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 10))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 10))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (First == 10 || 10 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 10))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 10))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 10))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 10))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 10))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c16;
      q = Fma(a6, q, c15);
      q = Fma(a5, q, c14);
      q = Fma(a4, q, c13);
      q = Fma(a3, q, c12);
      q = Fma(a2, q, c11);
      const auto hi = Bits(c10);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<2>(hi, w1)));
      At<10 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (10 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 11 && 11 <= Last) {
      if constexpr (11 > M::high_before(First, 11))
        c11 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(13))));
      if constexpr (12 > M::high_before(First, 11))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 11))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 11))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 11))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 11))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 11))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (First == 11 || 11 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 11))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 11))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 11))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 11))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 11))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c17;
      q = Fma(a6, q, c16);
      q = Fma(a5, q, c15);
      q = Fma(a4, q, c14);
      q = Fma(a3, q, c13);
      q = Fma(a2, q, c12);
      const auto hi = Bits(c11);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<3>(hi, w1)));
      At<11 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (11 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 12 && 12 <= Last) {
      if constexpr (12 > M::high_before(First, 12))
        c12 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(14))));
      if constexpr (13 > M::high_before(First, 12))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 12))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 12))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 12))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 12))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 12))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (First == 12 || 12 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 12))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 12))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 12))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 12))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 12))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      V q = c18;
      q = Fma(a6, q, c17);
      q = Fma(a5, q, c16);
      q = Fma(a4, q, c15);
      q = Fma(a3, q, c14);
      q = Fma(a2, q, c13);
      const auto hi = Bits(c12);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<4>(hi, w1)));
      At<12 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (12 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 13 && 13 <= Last) {
      if constexpr (13 > M::high_before(First, 13))
        c13 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(15))));
      if constexpr (14 > M::high_before(First, 13))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 13))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 13))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 13))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 13))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 13))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 13))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (First == 13 || 13 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 13))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 13))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 13))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 13))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 13))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 13))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c20;
      q = Fma(a7, q, c19);
      q = Fma(a6, q, c18);
      q = Fma(a5, q, c17);
      q = Fma(a4, q, c16);
      q = Fma(a3, q, c15);
      q = Fma(a2, q, c14);
      const auto hi = Bits(c13);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<5>(hi, w1)));
      At<13 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (13 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 14 && 14 <= Last) {
      if constexpr (14 > M::high_before(First, 14))
        c14 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(16))));
      if constexpr (15 > M::high_before(First, 14))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 14))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 14))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 14))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 14))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 14))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 14))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (First == 14 || 14 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 14))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 14))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 14))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 14))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 14))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 14))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c21;
      q = Fma(a7, q, c20);
      q = Fma(a6, q, c19);
      q = Fma(a5, q, c18);
      q = Fma(a4, q, c17);
      q = Fma(a3, q, c16);
      q = Fma(a2, q, c15);
      const auto hi = Bits(c14);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<6>(hi, w1)));
      At<14 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (14 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 15 && 15 <= Last) {
      if constexpr (15 > M::high_before(First, 15))
        c15 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(17))));
      if constexpr (16 > M::high_before(First, 15))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 15))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 15))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 15))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 15))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 15))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 15))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (First == 15 || 15 == 8)
        w1 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(9)));
      if constexpr (2 > M::degree_before(First, 15))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 15))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 15))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 15))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 15))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 15))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c22;
      q = Fma(a7, q, c21);
      q = Fma(a6, q, c20);
      q = Fma(a5, q, c19);
      q = Fma(a4, q, c18);
      q = Fma(a3, q, c17);
      q = Fma(a2, q, c16);
      const auto hi = Bits(c15);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<7>(hi, w1)));
      At<15 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (15 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 16 && 16 <= Last) {
      if constexpr (16 > M::high_before(First, 16))
        c16 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(19))));
      if constexpr (17 > M::high_before(First, 16))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 16))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 16))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 16))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 16))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 16))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 16))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (First == 16 || 16 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 16))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 16))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 16))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 16))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 16))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 16))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c23;
      q = Fma(a7, q, c22);
      q = Fma(a6, q, c21);
      q = Fma(a5, q, c20);
      q = Fma(a4, q, c19);
      q = Fma(a3, q, c18);
      q = Fma(a2, q, c17);
      const auto hi = Bits(c16);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<0>(hi, w2)));
      At<16 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (16 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 17 && 17 <= Last) {
      if constexpr (17 > M::high_before(First, 17))
        c17 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(20))));
      if constexpr (18 > M::high_before(First, 17))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 17))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 17))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 17))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 17))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 17))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 17))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (First == 17 || 17 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 17))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 17))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 17))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 17))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 17))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 17))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c24;
      q = Fma(a7, q, c23);
      q = Fma(a6, q, c22);
      q = Fma(a5, q, c21);
      q = Fma(a4, q, c20);
      q = Fma(a3, q, c19);
      q = Fma(a2, q, c18);
      const auto hi = Bits(c17);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<1>(hi, w2)));
      At<17 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (17 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 18 && 18 <= Last) {
      if constexpr (18 > M::high_before(First, 18))
        c18 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(21))));
      if constexpr (19 > M::high_before(First, 18))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 18))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 18))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 18))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 18))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 18))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (25 > M::high_before(First, 18))
        c25 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(28))));
      if constexpr (First == 18 || 18 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 18))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 18))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 18))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 18))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 18))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 18))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c25;
      q = Fma(a7, q, c24);
      q = Fma(a6, q, c23);
      q = Fma(a5, q, c22);
      q = Fma(a4, q, c21);
      q = Fma(a3, q, c20);
      q = Fma(a2, q, c19);
      const auto hi = Bits(c18);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<2>(hi, w2)));
      At<18 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (18 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 19 && 19 <= Last) {
      if constexpr (19 > M::high_before(First, 19))
        c19 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(22))));
      if constexpr (20 > M::high_before(First, 19))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 19))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 19))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 19))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 19))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (25 > M::high_before(First, 19))
        c25 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(28))));
      if constexpr (26 > M::high_before(First, 19))
        c26 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(29))));
      if constexpr (First == 19 || 19 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 19))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 19))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 19))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 19))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 19))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 19))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c26;
      q = Fma(a7, q, c25);
      q = Fma(a6, q, c24);
      q = Fma(a5, q, c23);
      q = Fma(a4, q, c22);
      q = Fma(a3, q, c21);
      q = Fma(a2, q, c20);
      const auto hi = Bits(c19);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<3>(hi, w2)));
      At<19 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (19 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 20 && 20 <= Last) {
      if constexpr (20 > M::high_before(First, 20))
        c20 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(23))));
      if constexpr (21 > M::high_before(First, 20))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 20))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 20))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 20))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (25 > M::high_before(First, 20))
        c25 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(28))));
      if constexpr (26 > M::high_before(First, 20))
        c26 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(29))));
      if constexpr (27 > M::high_before(First, 20))
        c27 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(30))));
      if constexpr (First == 20 || 20 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 20))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 20))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 20))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 20))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 20))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 20))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c27;
      q = Fma(a7, q, c26);
      q = Fma(a6, q, c25);
      q = Fma(a5, q, c24);
      q = Fma(a4, q, c23);
      q = Fma(a3, q, c22);
      q = Fma(a2, q, c21);
      const auto hi = Bits(c20);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<4>(hi, w2)));
      At<20 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (20 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 21 && 21 <= Last) {
      if constexpr (21 > M::high_before(First, 21))
        c21 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(24))));
      if constexpr (22 > M::high_before(First, 21))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 21))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 21))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (25 > M::high_before(First, 21))
        c25 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(28))));
      if constexpr (26 > M::high_before(First, 21))
        c26 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(29))));
      if constexpr (27 > M::high_before(First, 21))
        c27 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(30))));
      if constexpr (28 > M::high_before(First, 21))
        c28 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(31))));
      if constexpr (First == 21 || 21 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 21))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 21))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 21))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 21))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 21))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 21))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c28;
      q = Fma(a7, q, c27);
      q = Fma(a6, q, c26);
      q = Fma(a5, q, c25);
      q = Fma(a4, q, c24);
      q = Fma(a3, q, c23);
      q = Fma(a2, q, c22);
      const auto hi = Bits(c21);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<5>(hi, w2)));
      At<21 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (21 < Last)
      scale_power = hn::Add(scale_power, two_k);
    if constexpr (First <= 22 && 22 <= Last) {
      if constexpr (22 > M::high_before(First, 22))
        c22 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(25))));
      if constexpr (23 > M::high_before(First, 22))
        c23 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(26))));
      if constexpr (24 > M::high_before(First, 22))
        c24 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(27))));
      if constexpr (25 > M::high_before(First, 22))
        c25 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(28))));
      if constexpr (26 > M::high_before(First, 22))
        c26 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(29))));
      if constexpr (27 > M::high_before(First, 22))
        c27 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(30))));
      if constexpr (28 > M::high_before(First, 22))
        c28 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(31))));
      if constexpr (29 > M::high_before(First, 22))
        c29 = Float(
            Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(32))));
      if constexpr (First == 22 || 22 == 16)
        w2 = Gather<Software, M::word_count - 1>(data, hn::Add(row, SU(18)));
      if constexpr (2 > M::degree_before(First, 22))
        a2 = RoundedMul(h, S(0x1.0000000000000p-1));
      if constexpr (3 > M::degree_before(First, 22))
        a3 = RoundedMul(h, S(0x1.5555555555555p-2));
      if constexpr (4 > M::degree_before(First, 22))
        a4 = RoundedMul(h, S(0x1.0000000000000p-2));
      if constexpr (5 > M::degree_before(First, 22))
        a5 = RoundedMul(h, S(0x1.999999999999ap-3));
      if constexpr (6 > M::degree_before(First, 22))
        a6 = RoundedMul(h, S(0x1.5555555555555p-3));
      if constexpr (7 > M::degree_before(First, 22))
        a7 = RoundedMul(h, S(0x1.2492492492492p-3));
      V q = c29;
      q = Fma(a7, q, c28);
      q = Fma(a6, q, c27);
      q = Fma(a5, q, c26);
      q = Fma(a4, q, c25);
      q = Fma(a3, q, c24);
      q = Fma(a2, q, c23);
      const auto hi = Bits(c22);
      const auto value =
          RoundedAdd(Float(hn::Add(hi, SU(1))),
                     FmaSub(h, q, CorrectionFromWord<6>(hi, w2)));
      At<22 - First>(out...) = Scale(Bits(value), scale_power);
    }
    if constexpr (22 < Last)
      scale_power = hn::Add(scale_power, two_k);
  }
};
} // namespace HWY_NAMESPACE
} // namespace simd
} // namespace fast_boys
HWY_AFTER_NAMESPACE();
#endif
