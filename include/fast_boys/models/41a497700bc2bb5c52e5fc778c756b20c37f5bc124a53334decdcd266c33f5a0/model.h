#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::
    m_41a497700bc2bb5c52e5fc778c756b20c37f5bc124a53334decdcd266c33f5a0 {
struct Model {
  static constexpr int first = 0, last = 15, highest_reference_order = 21;
  inline static constexpr int degrees[] = {5, 5, 5, 5, 5, 5, 5, 6,
                                           6, 6, 6, 6, 6, 6, 6, 6};
  static constexpr unsigned retained_bits = 10, discarded_bits = 42;
  static constexpr double offset = 0x1.ee00000000000p+2,
                          domain_end = 0x1.22cc0195a0284p+6;
  static constexpr std::uint64_t key_min = 1050552ULL, key_max = 1053959ULL;
  static constexpr std::size_t row_count = 3408, row_words = 24,
                               table_bytes = 1047744;
  static constexpr std::size_t word_count = table_bytes / 8;
  inline static constexpr char payload_layout[] =
      "materialized-nextup-main-tail-v3";
  inline static constexpr char canonical_payload_sha256[] =
      "a7f995358c7012511c02048906b8b6ebc7fa3ab46ee238d0e073b75d971f9f19";
  inline static constexpr char payload_sha256[] =
      "adea22a9a1889b7ee22fb4c1e3f9c2209ddb8750e920be9639bf23d757b120c8";
  inline static constexpr char model_id[] =
      "41a497700bc2bb5c52e5fc778c756b20c37f5bc124a53334decdcd266c33f5a0";
  static constexpr ErrorMetric error_metric = ErrorMetric::Ulp;
  static constexpr double error_limit = 0x1.0000000000000p+0;
  static constexpr bool combined_table = true;
  static constexpr std::size_t main_table_bytes = 654336,
                               tail_table_bytes = 393408;
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
    double c5 FAST_BOYS_INDETERMINATE;
    double c6 FAST_BOYS_INDETERMINATE;
    double c7 FAST_BOYS_INDETERMINATE;
    double c8 FAST_BOYS_INDETERMINATE;
    double c9 FAST_BOYS_INDETERMINATE;
    double c10 FAST_BOYS_INDETERMINATE;
    double c11 FAST_BOYS_INDETERMINATE;
    double c12 FAST_BOYS_INDETERMINATE;
    double c13 FAST_BOYS_INDETERMINATE;
    double c14 FAST_BOYS_INDETERMINATE;
    double c15 FAST_BOYS_INDETERMINATE;
    double c16 FAST_BOYS_INDETERMINATE;
    double c17 FAST_BOYS_INDETERMINATE;
    double c18 FAST_BOYS_INDETERMINATE;
    double c19 FAST_BOYS_INDETERMINATE;
    double c20 FAST_BOYS_INDETERMINATE;
    double c21 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    double a6 FAST_BOYS_INDETERMINATE;
    std::uint64_t w0 FAST_BOYS_INDETERMINATE;
    std::uint64_t w1 FAST_BOYS_INDETERMINATE;
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
      if constexpr (5 > high_before(First, 0))
        c5 = O::value(row[6]);
      if constexpr (2 > degree_before(First, 0))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 0))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 0))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 0))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 0 || 0 == 0)
        w0 = row[0];
      double q = c5;
      q = O::fma(a5, q, c4);
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
    if constexpr (First <= 1 && 1 <= Limit) {
      if constexpr (1 > high_before(First, 1))
        c1 = O::value(row[2]);
      if constexpr (2 > high_before(First, 1))
        c2 = O::value(row[3]);
      if constexpr (3 > high_before(First, 1))
        c3 = O::value(row[4]);
      if constexpr (4 > high_before(First, 1))
        c4 = O::value(row[5]);
      if constexpr (5 > high_before(First, 1))
        c5 = O::value(row[6]);
      if constexpr (6 > high_before(First, 1))
        c6 = O::value(row[7]);
      if constexpr (2 > degree_before(First, 1))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 1))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 1))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 1))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 1 || 1 == 0)
        w0 = row[0];
      double q = c6;
      q = O::fma(a5, q, c5);
      q = O::fma(a4, q, c4);
      q = O::fma(a3, q, c3);
      q = O::fma(a2, q, c2);
      const auto hi = O::bits(c1);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<1>(hi, w0)));
      out[(1 - First) * stride] = O::scale(result, unsigned(3 * scale_k));
      if (last_output == 1)
        return;
    }
    if constexpr (First <= 2 && 2 <= Limit) {
      if constexpr (2 > high_before(First, 2))
        c2 = O::value(row[3]);
      if constexpr (3 > high_before(First, 2))
        c3 = O::value(row[4]);
      if constexpr (4 > high_before(First, 2))
        c4 = O::value(row[5]);
      if constexpr (5 > high_before(First, 2))
        c5 = O::value(row[6]);
      if constexpr (6 > high_before(First, 2))
        c6 = O::value(row[7]);
      if constexpr (7 > high_before(First, 2))
        c7 = O::value(row[8]);
      if constexpr (2 > degree_before(First, 2))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 2))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 2))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 2))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 2 || 2 == 0)
        w0 = row[0];
      double q = c7;
      q = O::fma(a5, q, c6);
      q = O::fma(a4, q, c5);
      q = O::fma(a3, q, c4);
      q = O::fma(a2, q, c3);
      const auto hi = O::bits(c2);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<2>(hi, w0)));
      out[(2 - First) * stride] = O::scale(result, unsigned(5 * scale_k));
      if (last_output == 2)
        return;
    }
    if constexpr (First <= 3 && 3 <= Limit) {
      if constexpr (3 > high_before(First, 3))
        c3 = O::value(row[4]);
      if constexpr (4 > high_before(First, 3))
        c4 = O::value(row[5]);
      if constexpr (5 > high_before(First, 3))
        c5 = O::value(row[6]);
      if constexpr (6 > high_before(First, 3))
        c6 = O::value(row[7]);
      if constexpr (7 > high_before(First, 3))
        c7 = O::value(row[8]);
      if constexpr (8 > high_before(First, 3))
        c8 = O::value(row[10]);
      if constexpr (2 > degree_before(First, 3))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 3))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 3))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 3))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 3 || 3 == 0)
        w0 = row[0];
      double q = c8;
      q = O::fma(a5, q, c7);
      q = O::fma(a4, q, c6);
      q = O::fma(a3, q, c5);
      q = O::fma(a2, q, c4);
      const auto hi = O::bits(c3);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<3>(hi, w0)));
      out[(3 - First) * stride] = O::scale(result, unsigned(7 * scale_k));
      if (last_output == 3)
        return;
    }
    if constexpr (First <= 4 && 4 <= Limit) {
      if constexpr (4 > high_before(First, 4))
        c4 = O::value(row[5]);
      if constexpr (5 > high_before(First, 4))
        c5 = O::value(row[6]);
      if constexpr (6 > high_before(First, 4))
        c6 = O::value(row[7]);
      if constexpr (7 > high_before(First, 4))
        c7 = O::value(row[8]);
      if constexpr (8 > high_before(First, 4))
        c8 = O::value(row[10]);
      if constexpr (9 > high_before(First, 4))
        c9 = O::value(row[11]);
      if constexpr (2 > degree_before(First, 4))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 4))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 4))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 4))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 4 || 4 == 0)
        w0 = row[0];
      double q = c9;
      q = O::fma(a5, q, c8);
      q = O::fma(a4, q, c7);
      q = O::fma(a3, q, c6);
      q = O::fma(a2, q, c5);
      const auto hi = O::bits(c4);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<4>(hi, w0)));
      out[(4 - First) * stride] = O::scale(result, unsigned(9 * scale_k));
      if (last_output == 4)
        return;
    }
    if constexpr (First <= 5 && 5 <= Limit) {
      if constexpr (5 > high_before(First, 5))
        c5 = O::value(row[6]);
      if constexpr (6 > high_before(First, 5))
        c6 = O::value(row[7]);
      if constexpr (7 > high_before(First, 5))
        c7 = O::value(row[8]);
      if constexpr (8 > high_before(First, 5))
        c8 = O::value(row[10]);
      if constexpr (9 > high_before(First, 5))
        c9 = O::value(row[11]);
      if constexpr (10 > high_before(First, 5))
        c10 = O::value(row[12]);
      if constexpr (2 > degree_before(First, 5))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 5))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 5))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 5))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 5 || 5 == 0)
        w0 = row[0];
      double q = c10;
      q = O::fma(a5, q, c9);
      q = O::fma(a4, q, c8);
      q = O::fma(a3, q, c7);
      q = O::fma(a2, q, c6);
      const auto hi = O::bits(c5);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<5>(hi, w0)));
      out[(5 - First) * stride] = O::scale(result, unsigned(11 * scale_k));
      if (last_output == 5)
        return;
    }
    if constexpr (First <= 6 && 6 <= Limit) {
      if constexpr (6 > high_before(First, 6))
        c6 = O::value(row[7]);
      if constexpr (7 > high_before(First, 6))
        c7 = O::value(row[8]);
      if constexpr (8 > high_before(First, 6))
        c8 = O::value(row[10]);
      if constexpr (9 > high_before(First, 6))
        c9 = O::value(row[11]);
      if constexpr (10 > high_before(First, 6))
        c10 = O::value(row[12]);
      if constexpr (11 > high_before(First, 6))
        c11 = O::value(row[13]);
      if constexpr (2 > degree_before(First, 6))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 6))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 6))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 6))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (First == 6 || 6 == 0)
        w0 = row[0];
      double q = c11;
      q = O::fma(a5, q, c10);
      q = O::fma(a4, q, c9);
      q = O::fma(a3, q, c8);
      q = O::fma(a2, q, c7);
      const auto hi = O::bits(c6);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<6>(hi, w0)));
      out[(6 - First) * stride] = O::scale(result, unsigned(13 * scale_k));
      if (last_output == 6)
        return;
    }
    if constexpr (First <= 7 && 7 <= Limit) {
      if constexpr (7 > high_before(First, 7))
        c7 = O::value(row[8]);
      if constexpr (8 > high_before(First, 7))
        c8 = O::value(row[10]);
      if constexpr (9 > high_before(First, 7))
        c9 = O::value(row[11]);
      if constexpr (10 > high_before(First, 7))
        c10 = O::value(row[12]);
      if constexpr (11 > high_before(First, 7))
        c11 = O::value(row[13]);
      if constexpr (12 > high_before(First, 7))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 7))
        c13 = O::value(row[15]);
      if constexpr (2 > degree_before(First, 7))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 7))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 7))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 7))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 7))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 7 || 7 == 0)
        w0 = row[0];
      double q = c13;
      q = O::fma(a6, q, c12);
      q = O::fma(a5, q, c11);
      q = O::fma(a4, q, c10);
      q = O::fma(a3, q, c9);
      q = O::fma(a2, q, c8);
      const auto hi = O::bits(c7);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<7>(hi, w0)));
      out[(7 - First) * stride] = O::scale(result, unsigned(15 * scale_k));
      if (last_output == 7)
        return;
    }
    if constexpr (First <= 8 && 8 <= Limit) {
      if constexpr (8 > high_before(First, 8))
        c8 = O::value(row[10]);
      if constexpr (9 > high_before(First, 8))
        c9 = O::value(row[11]);
      if constexpr (10 > high_before(First, 8))
        c10 = O::value(row[12]);
      if constexpr (11 > high_before(First, 8))
        c11 = O::value(row[13]);
      if constexpr (12 > high_before(First, 8))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 8))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 8))
        c14 = O::value(row[16]);
      if constexpr (2 > degree_before(First, 8))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 8))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 8))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 8))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 8))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 8 || 8 == 8)
        w1 = row[9];
      double q = c14;
      q = O::fma(a6, q, c13);
      q = O::fma(a5, q, c12);
      q = O::fma(a4, q, c11);
      q = O::fma(a3, q, c10);
      q = O::fma(a2, q, c9);
      const auto hi = O::bits(c8);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<0>(hi, w1)));
      out[(8 - First) * stride] = O::scale(result, unsigned(17 * scale_k));
      if (last_output == 8)
        return;
    }
    if constexpr (First <= 9 && 9 <= Limit) {
      if constexpr (9 > high_before(First, 9))
        c9 = O::value(row[11]);
      if constexpr (10 > high_before(First, 9))
        c10 = O::value(row[12]);
      if constexpr (11 > high_before(First, 9))
        c11 = O::value(row[13]);
      if constexpr (12 > high_before(First, 9))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 9))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 9))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 9))
        c15 = O::value(row[17]);
      if constexpr (2 > degree_before(First, 9))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 9))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 9))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 9))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 9))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 9 || 9 == 8)
        w1 = row[9];
      double q = c15;
      q = O::fma(a6, q, c14);
      q = O::fma(a5, q, c13);
      q = O::fma(a4, q, c12);
      q = O::fma(a3, q, c11);
      q = O::fma(a2, q, c10);
      const auto hi = O::bits(c9);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<1>(hi, w1)));
      out[(9 - First) * stride] = O::scale(result, unsigned(19 * scale_k));
      if (last_output == 9)
        return;
    }
    if constexpr (First <= 10 && 10 <= Limit) {
      if constexpr (10 > high_before(First, 10))
        c10 = O::value(row[12]);
      if constexpr (11 > high_before(First, 10))
        c11 = O::value(row[13]);
      if constexpr (12 > high_before(First, 10))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 10))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 10))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 10))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 10))
        c16 = O::value(row[18]);
      if constexpr (2 > degree_before(First, 10))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 10))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 10))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 10))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 10))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 10 || 10 == 8)
        w1 = row[9];
      double q = c16;
      q = O::fma(a6, q, c15);
      q = O::fma(a5, q, c14);
      q = O::fma(a4, q, c13);
      q = O::fma(a3, q, c12);
      q = O::fma(a2, q, c11);
      const auto hi = O::bits(c10);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<2>(hi, w1)));
      out[(10 - First) * stride] = O::scale(result, unsigned(21 * scale_k));
      if (last_output == 10)
        return;
    }
    if constexpr (First <= 11 && 11 <= Limit) {
      if constexpr (11 > high_before(First, 11))
        c11 = O::value(row[13]);
      if constexpr (12 > high_before(First, 11))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 11))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 11))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 11))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 11))
        c16 = O::value(row[18]);
      if constexpr (17 > high_before(First, 11))
        c17 = O::value(row[19]);
      if constexpr (2 > degree_before(First, 11))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 11))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 11))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 11))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 11))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 11 || 11 == 8)
        w1 = row[9];
      double q = c17;
      q = O::fma(a6, q, c16);
      q = O::fma(a5, q, c15);
      q = O::fma(a4, q, c14);
      q = O::fma(a3, q, c13);
      q = O::fma(a2, q, c12);
      const auto hi = O::bits(c11);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<3>(hi, w1)));
      out[(11 - First) * stride] = O::scale(result, unsigned(23 * scale_k));
      if (last_output == 11)
        return;
    }
    if constexpr (First <= 12 && 12 <= Limit) {
      if constexpr (12 > high_before(First, 12))
        c12 = O::value(row[14]);
      if constexpr (13 > high_before(First, 12))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 12))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 12))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 12))
        c16 = O::value(row[18]);
      if constexpr (17 > high_before(First, 12))
        c17 = O::value(row[19]);
      if constexpr (18 > high_before(First, 12))
        c18 = O::value(row[20]);
      if constexpr (2 > degree_before(First, 12))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 12))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 12))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 12))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 12))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 12 || 12 == 8)
        w1 = row[9];
      double q = c18;
      q = O::fma(a6, q, c17);
      q = O::fma(a5, q, c16);
      q = O::fma(a4, q, c15);
      q = O::fma(a3, q, c14);
      q = O::fma(a2, q, c13);
      const auto hi = O::bits(c12);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<4>(hi, w1)));
      out[(12 - First) * stride] = O::scale(result, unsigned(25 * scale_k));
      if (last_output == 12)
        return;
    }
    if constexpr (First <= 13 && 13 <= Limit) {
      if constexpr (13 > high_before(First, 13))
        c13 = O::value(row[15]);
      if constexpr (14 > high_before(First, 13))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 13))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 13))
        c16 = O::value(row[18]);
      if constexpr (17 > high_before(First, 13))
        c17 = O::value(row[19]);
      if constexpr (18 > high_before(First, 13))
        c18 = O::value(row[20]);
      if constexpr (19 > high_before(First, 13))
        c19 = O::value(row[21]);
      if constexpr (2 > degree_before(First, 13))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 13))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 13))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 13))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 13))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 13 || 13 == 8)
        w1 = row[9];
      double q = c19;
      q = O::fma(a6, q, c18);
      q = O::fma(a5, q, c17);
      q = O::fma(a4, q, c16);
      q = O::fma(a3, q, c15);
      q = O::fma(a2, q, c14);
      const auto hi = O::bits(c13);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<5>(hi, w1)));
      out[(13 - First) * stride] = O::scale(result, unsigned(27 * scale_k));
      if (last_output == 13)
        return;
    }
    if constexpr (First <= 14 && 14 <= Limit) {
      if constexpr (14 > high_before(First, 14))
        c14 = O::value(row[16]);
      if constexpr (15 > high_before(First, 14))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 14))
        c16 = O::value(row[18]);
      if constexpr (17 > high_before(First, 14))
        c17 = O::value(row[19]);
      if constexpr (18 > high_before(First, 14))
        c18 = O::value(row[20]);
      if constexpr (19 > high_before(First, 14))
        c19 = O::value(row[21]);
      if constexpr (20 > high_before(First, 14))
        c20 = O::value(row[22]);
      if constexpr (2 > degree_before(First, 14))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 14))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 14))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 14))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 14))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 14 || 14 == 8)
        w1 = row[9];
      double q = c20;
      q = O::fma(a6, q, c19);
      q = O::fma(a5, q, c18);
      q = O::fma(a4, q, c17);
      q = O::fma(a3, q, c16);
      q = O::fma(a2, q, c15);
      const auto hi = O::bits(c14);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<6>(hi, w1)));
      out[(14 - First) * stride] = O::scale(result, unsigned(29 * scale_k));
      if (last_output == 14)
        return;
    }
    if constexpr (First <= 15 && 15 <= Limit) {
      if constexpr (15 > high_before(First, 15))
        c15 = O::value(row[17]);
      if constexpr (16 > high_before(First, 15))
        c16 = O::value(row[18]);
      if constexpr (17 > high_before(First, 15))
        c17 = O::value(row[19]);
      if constexpr (18 > high_before(First, 15))
        c18 = O::value(row[20]);
      if constexpr (19 > high_before(First, 15))
        c19 = O::value(row[21]);
      if constexpr (20 > high_before(First, 15))
        c20 = O::value(row[22]);
      if constexpr (21 > high_before(First, 15))
        c21 = O::value(row[23]);
      if constexpr (2 > degree_before(First, 15))
        a2 = O::mul(h, 0x1.0000000000000p-1);
      if constexpr (3 > degree_before(First, 15))
        a3 = O::mul(h, 0x1.5555555555555p-2);
      if constexpr (4 > degree_before(First, 15))
        a4 = O::mul(h, 0x1.0000000000000p-2);
      if constexpr (5 > degree_before(First, 15))
        a5 = O::mul(h, 0x1.999999999999ap-3);
      if constexpr (6 > degree_before(First, 15))
        a6 = O::mul(h, 0x1.5555555555555p-3);
      if constexpr (First == 15 || 15 == 8)
        w1 = row[9];
      double q = c21;
      q = O::fma(a6, q, c20);
      q = O::fma(a5, q, c19);
      q = O::fma(a4, q, c18);
      q = O::fma(a3, q, c17);
      q = O::fma(a2, q, c16);
      const auto hi = O::bits(c15);
      const double result =
          O::add(O::value(hi + 1),
                 O::fma(h, q, -O::template correction_from_word<7>(hi, w1)));
      out[(15 - First) * stride] = O::scale(result, unsigned(31 * scale_k));
      if (last_output == 15)
        return;
    }
  }
};
} // namespace
  // fast_boys::models::m_41a497700bc2bb5c52e5fc778c756b20c37f5bc124a53334decdcd266c33f5a0
