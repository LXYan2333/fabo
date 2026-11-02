#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_71a0d765c94c0908f05707402d757b2d6effdfa79b2c1fca1ca3f9c55d2906dd {
struct Model {
  static constexpr int first=0, last=11, highest_reference_order=18;
  inline static constexpr int degrees[] = {6,6,6,7,7,7,7,7,7,7,7,7};
  static constexpr unsigned retained_bits=8, discarded_bits=44;
  static constexpr double offset=0x1.ac00000000000p+2, domain_end=0x1.312d000000000p+23;
  static constexpr std::uint64_t key_min=262572ULL, key_max=267825ULL;
  static constexpr std::size_t row_count=5254, row_words=21, table_bytes=882672;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-interleaved8-v2";
  inline static constexpr char canonical_payload_sha256[]="2aaa9bf2abf0637721359ee977b6f2d4f7ed66582be7d0ff2fd2746d2c1c2337";
  inline static constexpr char payload_sha256[]="cc5003512f5886f450082202bf693b86b6b15b1dc3fb4013eccc4eea7ba072c2";
  inline static constexpr char model_id[]="71a0d765c94c0908f05707402d757b2d6effdfa79b2c1fca1ca3f9c55d2906dd";
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
    double c12 FAST_BOYS_INDETERMINATE;
    double c13 FAST_BOYS_INDETERMINATE;
    double c14 FAST_BOYS_INDETERMINATE;
    double c15 FAST_BOYS_INDETERMINATE;
    double c16 FAST_BOYS_INDETERMINATE;
    double c17 FAST_BOYS_INDETERMINATE;
    double c18 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    double a6 FAST_BOYS_INDETERMINATE;
    double a7 FAST_BOYS_INDETERMINATE;
    if constexpr(First<=0 && 0<=Limit) {
      if constexpr(0>high_before(First,0)) minimum_up=row[1];
      if constexpr(1>high_before(First,0)) c1=O::value(row[2]);
      if constexpr(2>high_before(First,0)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,0)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,0)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,0)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,0)) c6=O::value(row[7]);
      if constexpr(2>degree_before(First,0)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,0)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,0)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,0)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,0)) a6=O::mul(h,0x1.5555555555555p-3);
      double q=c6;
      q=O::fma(a6,q,c5);
      q=O::fma(a5,q,c4);
      q=O::fma(a4,q,c3);
      q=O::fma(a3,q,c2);
      q=O::fma(a2,q,c1);
      const auto hi=minimum_up-1;
      out[(0-First)*stride]=O::add(O::value(minimum_up),O::fma(h,q,-O::template correction_from_word<0>(hi,row[0])));
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
      out[(1-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<1>(hi,row[0])));
      if(last_output==1) return;
    }
    if constexpr(First<=2 && 2<=Limit) {
      if constexpr(2>high_before(First,2)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,2)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,2)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,2)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,2)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,2)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,2)) c8=O::value(row[10]);
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
      out[(2-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<2>(hi,row[0])));
      if(last_output==2) return;
    }
    if constexpr(First<=3 && 3<=Limit) {
      if constexpr(3>high_before(First,3)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,3)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,3)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,3)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,3)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,3)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,3)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,3)) c10=O::value(row[12]);
      if constexpr(2>degree_before(First,3)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,3)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,3)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,3)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,3)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,3)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c10;
      q=O::fma(a7,q,c9);
      q=O::fma(a6,q,c8);
      q=O::fma(a5,q,c7);
      q=O::fma(a4,q,c6);
      q=O::fma(a3,q,c5);
      q=O::fma(a2,q,c4);
      const auto hi=O::bits(c3);
      out[(3-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<3>(hi,row[0])));
      if(last_output==3) return;
    }
    if constexpr(First<=4 && 4<=Limit) {
      if constexpr(4>high_before(First,4)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,4)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,4)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,4)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,4)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,4)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,4)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,4)) c11=O::value(row[13]);
      if constexpr(2>degree_before(First,4)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,4)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,4)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,4)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,4)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,4)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c11;
      q=O::fma(a7,q,c10);
      q=O::fma(a6,q,c9);
      q=O::fma(a5,q,c8);
      q=O::fma(a4,q,c7);
      q=O::fma(a3,q,c6);
      q=O::fma(a2,q,c5);
      const auto hi=O::bits(c4);
      out[(4-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<4>(hi,row[0])));
      if(last_output==4) return;
    }
    if constexpr(First<=5 && 5<=Limit) {
      if constexpr(5>high_before(First,5)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,5)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,5)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,5)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,5)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,5)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,5)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,5)) c12=O::value(row[14]);
      if constexpr(2>degree_before(First,5)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,5)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,5)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,5)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,5)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,5)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c12;
      q=O::fma(a7,q,c11);
      q=O::fma(a6,q,c10);
      q=O::fma(a5,q,c9);
      q=O::fma(a4,q,c8);
      q=O::fma(a3,q,c7);
      q=O::fma(a2,q,c6);
      const auto hi=O::bits(c5);
      out[(5-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<5>(hi,row[0])));
      if(last_output==5) return;
    }
    if constexpr(First<=6 && 6<=Limit) {
      if constexpr(6>high_before(First,6)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,6)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,6)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,6)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,6)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,6)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,6)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,6)) c13=O::value(row[15]);
      if constexpr(2>degree_before(First,6)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,6)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,6)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,6)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,6)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,6)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c13;
      q=O::fma(a7,q,c12);
      q=O::fma(a6,q,c11);
      q=O::fma(a5,q,c10);
      q=O::fma(a4,q,c9);
      q=O::fma(a3,q,c8);
      q=O::fma(a2,q,c7);
      const auto hi=O::bits(c6);
      out[(6-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<6>(hi,row[0])));
      if(last_output==6) return;
    }
    if constexpr(First<=7 && 7<=Limit) {
      if constexpr(7>high_before(First,7)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,7)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,7)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,7)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,7)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,7)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,7)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,7)) c14=O::value(row[16]);
      if constexpr(2>degree_before(First,7)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,7)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,7)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,7)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,7)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,7)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c14;
      q=O::fma(a7,q,c13);
      q=O::fma(a6,q,c12);
      q=O::fma(a5,q,c11);
      q=O::fma(a4,q,c10);
      q=O::fma(a3,q,c9);
      q=O::fma(a2,q,c8);
      const auto hi=O::bits(c7);
      out[(7-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<7>(hi,row[0])));
      if(last_output==7) return;
    }
    if constexpr(First<=8 && 8<=Limit) {
      if constexpr(8>high_before(First,8)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,8)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,8)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,8)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,8)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,8)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,8)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,8)) c15=O::value(row[17]);
      if constexpr(2>degree_before(First,8)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,8)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,8)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,8)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,8)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,8)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c15;
      q=O::fma(a7,q,c14);
      q=O::fma(a6,q,c13);
      q=O::fma(a5,q,c12);
      q=O::fma(a4,q,c11);
      q=O::fma(a3,q,c10);
      q=O::fma(a2,q,c9);
      const auto hi=O::bits(c8);
      out[(8-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<0>(hi,row[9])));
      if(last_output==8) return;
    }
    if constexpr(First<=9 && 9<=Limit) {
      if constexpr(9>high_before(First,9)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,9)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,9)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,9)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,9)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,9)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,9)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,9)) c16=O::value(row[18]);
      if constexpr(2>degree_before(First,9)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,9)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,9)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,9)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,9)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,9)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c16;
      q=O::fma(a7,q,c15);
      q=O::fma(a6,q,c14);
      q=O::fma(a5,q,c13);
      q=O::fma(a4,q,c12);
      q=O::fma(a3,q,c11);
      q=O::fma(a2,q,c10);
      const auto hi=O::bits(c9);
      out[(9-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<1>(hi,row[9])));
      if(last_output==9) return;
    }
    if constexpr(First<=10 && 10<=Limit) {
      if constexpr(10>high_before(First,10)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,10)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,10)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,10)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,10)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,10)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,10)) c16=O::value(row[18]);
      if constexpr(17>high_before(First,10)) c17=O::value(row[19]);
      if constexpr(2>degree_before(First,10)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,10)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,10)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,10)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,10)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,10)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c17;
      q=O::fma(a7,q,c16);
      q=O::fma(a6,q,c15);
      q=O::fma(a5,q,c14);
      q=O::fma(a4,q,c13);
      q=O::fma(a3,q,c12);
      q=O::fma(a2,q,c11);
      const auto hi=O::bits(c10);
      out[(10-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<2>(hi,row[9])));
      if(last_output==10) return;
    }
    if constexpr(First<=11 && 11<=Limit) {
      if constexpr(11>high_before(First,11)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,11)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,11)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,11)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,11)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,11)) c16=O::value(row[18]);
      if constexpr(17>high_before(First,11)) c17=O::value(row[19]);
      if constexpr(18>high_before(First,11)) c18=O::value(row[20]);
      if constexpr(2>degree_before(First,11)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,11)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,11)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,11)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,11)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,11)) a7=O::mul(h,0x1.2492492492492p-3);
      double q=c18;
      q=O::fma(a7,q,c17);
      q=O::fma(a6,q,c16);
      q=O::fma(a5,q,c15);
      q=O::fma(a4,q,c14);
      q=O::fma(a3,q,c13);
      q=O::fma(a2,q,c12);
      const auto hi=O::bits(c11);
      out[(11-First)*stride]=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<3>(hi,row[9])));
      if(last_output==11) return;
    }
  }
};
}
