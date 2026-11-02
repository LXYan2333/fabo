#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_2fb72e32747202afa704dca629ceba69bb9363f0415e8af4dadfcf4d12666155 {
struct Model {
  static constexpr int first=0, last=5, highest_reference_order=11;
  inline static constexpr int degrees[] = {5,6,6,6,6,6};
  static constexpr unsigned retained_bits=8, discarded_bits=44;
  static constexpr double offset=0x1.5400000000000p+0, domain_end=0x1.312d000000000p+23;
  static constexpr std::uint64_t key_min=261972ULL, key_max=267825ULL;
  static constexpr std::size_t row_count=5854, row_words=13, table_bytes=608816;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-interleaved8-v2";
  inline static constexpr char canonical_payload_sha256[]="3e63a5c92406c41cadf01dbcdc8fef18c4aaf308355459a8bdb5e74504b8f057";
  inline static constexpr char payload_sha256[]="3cf48a69bfe8728e76e369e06b423299abd68a5e70625d7ee5f2229fb8b6d235";
  inline static constexpr char model_id[]="2fb72e32747202afa704dca629ceba69bb9363f0415e8af4dadfcf4d12666155";
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
    double c7 FAST_BOYS_INDETERMINATE;
    double c8 FAST_BOYS_INDETERMINATE;
    double c9 FAST_BOYS_INDETERMINATE;
    double c10 FAST_BOYS_INDETERMINATE;
    double c11 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    double a6 FAST_BOYS_INDETERMINATE;
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
      if constexpr(7>high_before(First,1)) c7=O::value(row[8]);
      if constexpr(2>degree_before(First,1)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,1)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,1)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,1)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,1)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c7;
      q=O::fma(a6,q,c6);
      q=O::fma(a5,q,c5);
      q=O::fma(a4,q,c4);
      q=O::fma(a3,q,c3);
      q=O::fma(a2,q,c2);
      const auto hi=O::bits(c1);
      const unsigned code=unsigned((row[0] >> 8) & 255U);
      out[(1-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==1) return;
    }
    if constexpr(First<=2 && 2<=Limit) {
      if constexpr(2>high_before(First,2)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,2)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,2)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,2)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,2)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,2)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,2)) c8=O::value(row[9]);
      if constexpr(2>degree_before(First,2)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,2)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,2)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,2)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,2)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c8;
      q=O::fma(a6,q,c7);
      q=O::fma(a5,q,c6);
      q=O::fma(a4,q,c5);
      q=O::fma(a3,q,c4);
      q=O::fma(a2,q,c3);
      const auto hi=O::bits(c2);
      const unsigned code=unsigned((row[0] >> 16) & 255U);
      out[(2-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==2) return;
    }
    if constexpr(First<=3 && 3<=Limit) {
      if constexpr(3>high_before(First,3)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,3)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,3)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,3)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,3)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,3)) c8=O::value(row[9]);
      if constexpr(9>high_before(First,3)) c9=O::value(row[10]);
      if constexpr(2>degree_before(First,3)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,3)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,3)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,3)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,3)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c9;
      q=O::fma(a6,q,c8);
      q=O::fma(a5,q,c7);
      q=O::fma(a4,q,c6);
      q=O::fma(a3,q,c5);
      q=O::fma(a2,q,c4);
      const auto hi=O::bits(c3);
      const unsigned code=unsigned((row[0] >> 24) & 255U);
      out[(3-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==3) return;
    }
    if constexpr(First<=4 && 4<=Limit) {
      if constexpr(4>high_before(First,4)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,4)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,4)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,4)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,4)) c8=O::value(row[9]);
      if constexpr(9>high_before(First,4)) c9=O::value(row[10]);
      if constexpr(10>high_before(First,4)) c10=O::value(row[11]);
      if constexpr(2>degree_before(First,4)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,4)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,4)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,4)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,4)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c10;
      q=O::fma(a6,q,c9);
      q=O::fma(a5,q,c8);
      q=O::fma(a4,q,c7);
      q=O::fma(a3,q,c6);
      q=O::fma(a2,q,c5);
      const auto hi=O::bits(c4);
      const unsigned code=unsigned((row[0] >> 32) & 255U);
      out[(4-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==4) return;
    }
    if constexpr(First<=5 && 5<=Limit) {
      if constexpr(5>high_before(First,5)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,5)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,5)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,5)) c8=O::value(row[9]);
      if constexpr(9>high_before(First,5)) c9=O::value(row[10]);
      if constexpr(10>high_before(First,5)) c10=O::value(row[11]);
      if constexpr(11>high_before(First,5)) c11=O::value(row[12]);
      if constexpr(2>degree_before(First,5)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,5)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,5)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,5)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,5)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c11;
      q=O::fma(a6,q,c10);
      q=O::fma(a5,q,c9);
      q=O::fma(a4,q,c8);
      q=O::fma(a3,q,c7);
      q=O::fma(a2,q,c6);
      const auto hi=O::bits(c5);
      const unsigned code=unsigned((row[0] >> 40) & 255U);
      out[(5-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::correction(hi,code)));
      if(last_output==5) return;
    }
  }
};
}
