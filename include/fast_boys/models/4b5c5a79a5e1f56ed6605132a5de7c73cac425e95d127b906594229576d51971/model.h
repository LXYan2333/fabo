#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_4b5c5a79a5e1f56ed6605132a5de7c73cac425e95d127b906594229576d51971 {
struct Model {
  static constexpr int first=0, last=1, highest_reference_order=6;
  inline static constexpr int degrees[] = {5,5};
  static constexpr unsigned retained_bits=9, discarded_bits=43;
  static constexpr double offset=0x1.0100000000000p+3, domain_end=0x1.312d000000000p+23;
  static constexpr std::uint64_t key_min=525314ULL, key_max=535650ULL;
  static constexpr std::size_t row_count=10337, row_words=8, table_bytes=661568;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-interleaved8-v2";
  inline static constexpr char canonical_payload_sha256[]="570316781f0a45f9dfff6db5790634cce5982315e1a1c8ed65af9dcb12336b87";
  inline static constexpr char payload_sha256[]="d7fc03f9370154de425b2e46e22e08ac39f9b62caf143ef65fa18ef5f29299b4";
  inline static constexpr char model_id[]="4b5c5a79a5e1f56ed6605132a5de7c73cac425e95d127b906594229576d51971";
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
    double c5 FAST_BOYS_INDETERMINATE;
    double c6 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    if constexpr(First<=0 && 0<=Limit) {
      if constexpr(0>high_before(First,0)) minimum_up=row[1];
      if constexpr(1>high_before(First,0)) c1=O::value(row[2]);
      if constexpr(2>high_before(First,0)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,0)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,0)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,0)) c5=O::value(row[6]);
      if constexpr(2>degree_before(First,0)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,0)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,0)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,0)) a5=O::mul(h,0x1.999999999999ap-3);
      double q=c5;
      q=O::fma(a5,q,c4);
      q=O::fma(a4,q,c3);
      q=O::fma(a3,q,c2);
      q=O::fma(a2,q,c1);
      const auto hi=minimum_up-1;
      const unsigned code=unsigned((row[0] >> 0) & 255U);
      out[(0-First)*stride]=O::add(O::value(minimum_up),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==0) return;
    }
    if constexpr(First<=1 && 1<=Limit) {
      if constexpr(1>high_before(First,1)) c1=O::value(row[2]);
      if constexpr(2>high_before(First,1)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,1)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,1)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,1)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,1)) c6=O::value(row[7]);
      if constexpr(2>degree_before(First,1)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,1)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,1)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,1)) a5=O::mul(h,0x1.999999999999ap-3);
      double q=c6;
      q=O::fma(a5,q,c5);
      q=O::fma(a4,q,c4);
      q=O::fma(a3,q,c3);
      q=O::fma(a2,q,c2);
      const auto hi=O::bits(c1);
      const unsigned code=unsigned((row[0] >> 8) & 255U);
      out[(1-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==1) return;
    }
  }
};
}
