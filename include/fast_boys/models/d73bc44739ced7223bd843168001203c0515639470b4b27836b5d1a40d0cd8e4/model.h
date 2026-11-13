#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::
    m_d73bc44739ced7223bd843168001203c0515639470b4b27836b5d1a40d0cd8e4 {
struct Model {
  static constexpr int first = 0, last = 0, highest_reference_order = 4;
  inline static constexpr int degrees[] = {4};
  static constexpr unsigned retained_bits = 10, discarded_bits = 42;
  static constexpr double offset = 0x1.0300000000000p+2,
                          domain_end = 0x1.146b4b4e3f86dp+5;
  static constexpr std::uint64_t key_min = 1049612ULL, key_max = 1052883ULL;
  static constexpr std::size_t row_count = 3272, row_words = 6,
                               table_bytes = 255408;
  static constexpr std::size_t word_count = table_bytes / 8;
  inline static constexpr char payload_layout[] =
      "materialized-nextup-main-tail-v3";
  inline static constexpr char canonical_payload_sha256[] =
      "c7b7d9481a9eb3327e19491cd9efba744f7960a822fd71d8ad7fdb5c890c40fa";
  inline static constexpr char payload_sha256[] =
      "a5a74ded5df782f3cc7c35e3645382835701dfc15655e25a355bb88e2915eb27";
  inline static constexpr char model_id[] =
      "d73bc44739ced7223bd843168001203c0515639470b4b27836b5d1a40d0cd8e4";
  static constexpr ErrorMetric error_metric = ErrorMetric::Ulp;
  static constexpr double error_limit = 0x1.0000000000000p+0;
  static constexpr bool combined_table = true;
  static constexpr std::size_t main_table_bytes = 157056,
                               tail_table_bytes = 98352;
  static constexpr std::size_t tail_row_offset = row_count,
                               tail_row_count = 2049;
  static constexpr unsigned tail_retained_bits = 10, tail_discarded_bits = 42;
  static_assert(tail_row_offset * row_words * 8 == main_table_bytes,
                "tail offset mismatch");
  static_assert((row_count + tail_row_count) * row_words * 8 == table_bytes,
                "combined allocation mismatch");
  // Sampled qualification, not a continuous-domain error certificate.
  FAST_BOYS_HD static constexpr int high_before(int begin, int end) {
    int high = begin - 1;
    for (int n = begin; n < end; ++n)
      if (n + degrees[n - first] > high)
        high = n + degrees[n - first];
    return high;
  }
  FAST_BOYS_HD static constexpr int degree_before(int begin, int end) {
    int degree = 1;
    for (int n = begin; n < end; ++n)
      if (degrees[n - first] > degree)
        degree = degrees[n - first];
    return degree;
  }
  template <class O, int First, int Limit>
  FAST_BOYS_HD static FAST_BOYS_INLINE void
  evaluate(const std::uint64_t *FAST_BOYS_RESTRICT row, double h,
           int last_output, double *FAST_BOYS_RESTRICT out, std::size_t stride,
           unsigned scale_k = 0) {
    static_assert(first <= First && First <= Limit && Limit <= last,
                  "invalid subset");
    // No dynamic coefficient array: every access below has a fixed index.
    std::uint64_t minimum_up FAST_BOYS_INDETERMINATE;
    double c1 FAST_BOYS_INDETERMINATE;
    double c2 FAST_BOYS_INDETERMINATE;
    double c3 FAST_BOYS_INDETERMINATE;
    double c4 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    std::uint64_t w0 FAST_BOYS_INDETERMINATE;
    if constexpr (First <= 0 && 0 <= Limit) {
      if constexpr (0 > high_before(First, 0))
        minimum_up = row[1];
      if constexpr (1 > high_before(First, 0))
        c1 = O::value(row[2]);
      if constexpr (2 > high_before(First, 0))
        c2 = O::value(row[3]);
      if constexpr (3 > high_before(First, 0))
        c3 = O::value(row[4]);
      if constexpr (4 > high_before(First, 0))
        c4 = O::value(row[5]);
      if constexpr (2 > degree_before(First, 0))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 0))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 0))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (First == 0 || 0 == 0)
        w0 = row[0];
      double q = c4;
      q = O::fma(a4, q, c3);
      q = O::fma(a3, q, c2);
      q = O::fma(a2, q, c1);
      const auto hi = minimum_up - 1;
      const double result =
          O::add(O::value(minimum_up),
                 O::fma(h, q, -O::template correction_from_word<0>(hi, w0)));
      out[(0 - First) * stride] = O::scale(result, unsigned(1 * scale_k));
      if (last_output == 0)
        return;
    }
  }
};
} // namespace
  // fast_boys::models::m_d73bc44739ced7223bd843168001203c0515639470b4b27836b5d1a40d0cd8e4
