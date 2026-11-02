#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_cd04d4dfa167fbbde140347fc517cced8f657a259b74f64da3a77f20b39250d7 {
struct Model {
  static constexpr int first=0, last=0, highest_reference_order=4;
  inline static constexpr int degrees[] = {4};
  static constexpr unsigned retained_bits=10, discarded_bits=42;
  static constexpr double offset=0x1.0300000000000p+2, domain_end=0x1.312d000000000p+23;
  static constexpr std::uint64_t key_min=1049612ULL, key_max=1071301ULL;
  static constexpr std::size_t row_count=21690, row_words=6, table_bytes=1041120;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-interleaved8-v2";
  inline static constexpr char canonical_payload_sha256[]="51ac248dc4bf3deab2bc1dd31df5545206cae43468c7c52238b4d29dfc599758";
  inline static constexpr char payload_sha256[]="8bea1a2788d06213c586c664f294719e2b31b266e3683b7361a8cd851f9218c8";
  inline static constexpr char model_id[]="cd04d4dfa167fbbde140347fc517cced8f657a259b74f64da3a77f20b39250d7";
  static constexpr ErrorMetric error_metric=ErrorMetric::Ulp;
  static constexpr double error_limit=0x1.0000000000000p+0;
  // Sampled qualification, not a continuous-domain error certificate.
  FAST_BOYS_HD static constexpr int high_before(int begin,int end) {
    int high=begin-1;
    for(int n=begin;n<end;++n) if(n+degrees[n-first]>high) high=n+degrees[n-first];
    return high;
  }
  FAST_BOYS_HD static constexpr int degree_before(int begin,int end) {
    int degree=1;
    for(int n=begin;n<end;++n) if(degrees[n-first]>degree) degree=degrees[n-first];
    return degree;
  }
  template<class O,int First,int Limit>
  FAST_BOYS_HD static inline void evaluate(const std::uint64_t* FAST_BOYS_RESTRICT row,double h,int last_output,double* FAST_BOYS_RESTRICT out,std::size_t stride) {
    static_assert(first<=First && First<=Limit && Limit<=last,"invalid subset");
    // No dynamic coefficient array: every access below has a fixed index.
    std::uint64_t minimum_up FAST_BOYS_INDETERMINATE;
    double c1 FAST_BOYS_INDETERMINATE;
    double c2 FAST_BOYS_INDETERMINATE;
    double c3 FAST_BOYS_INDETERMINATE;
    double c4 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    if constexpr(First<=0 && 0<=Limit) {
      if constexpr(0>high_before(First,0)) minimum_up=row[1];
      if constexpr(1>high_before(First,0)) c1=O::value(row[2]);
      if constexpr(2>high_before(First,0)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,0)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,0)) c4=O::value(row[5]);
      if constexpr(2>degree_before(First,0)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,0)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,0)) a4=O::mul(h,0x1.0000000000000p-2);
      double q=c4;
      q=O::fma(a4,q,c3);
      q=O::fma(a3,q,c2);
      q=O::fma(a2,q,c1);
      const auto hi=minimum_up-1;
      const unsigned code=unsigned((row[0] >> 0) & 255U);
      out[(0-First)*stride]=O::add(O::value(minimum_up),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==0) return;
    }
  }
};
}
