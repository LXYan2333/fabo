#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_951812053d6b5885393d7d0f31f09e9d7cd50e09709a176bd1b3db9079fa99a5 {
struct Model {
  static constexpr int first=0, last=8, highest_reference_order=13;
  inline static constexpr int degrees[] = {4,5,5,5,5,5,5,5,5};
  static constexpr unsigned retained_bits=10, discarded_bits=42;
  static constexpr double offset=0x1.eb40000000000p+1, domain_end=0x1.d32002c203895p+5;
  static constexpr std::uint64_t key_min=1049517ULL, key_max=1053639ULL;
  static constexpr std::size_t row_count=4123, row_words=16, table_bytes=790016;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-main-tail-v3";
  inline static constexpr char canonical_payload_sha256[]="24003edb001176fef9121af31b35fcfd1bbf8671ece195228d3790adfdece2c9";
  inline static constexpr char payload_sha256[]="a37c1eca8d471b3518e9199cea806409b534619c825a1e17ef0240d96fa70855";
  inline static constexpr char model_id[]="951812053d6b5885393d7d0f31f09e9d7cd50e09709a176bd1b3db9079fa99a5";
  static constexpr ErrorMetric error_metric=ErrorMetric::Ulp;
  static constexpr double error_limit=0x1.0000000000000p+0;
  static constexpr bool combined_table=true;
  static constexpr std::size_t main_table_bytes=527744,tail_table_bytes=262272;
  static constexpr std::size_t tail_row_offset=row_count,tail_row_count=2049;
  static constexpr unsigned tail_retained_bits=10,tail_discarded_bits=42;
  static_assert(tail_row_offset*row_words*8==main_table_bytes,"tail offset mismatch");
  static_assert((row_count+tail_row_count)*row_words*8==table_bytes,"combined allocation mismatch");
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
  FAST_BOYS_HD static FAST_BOYS_INLINE void evaluate(const std::uint64_t* FAST_BOYS_RESTRICT row,double h,int last_output,double* FAST_BOYS_RESTRICT out,std::size_t stride,unsigned scale_k=0) {
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
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    std::uint64_t w0 FAST_BOYS_INDETERMINATE;
    std::uint64_t w1 FAST_BOYS_INDETERMINATE;
    for(int n=First;n<=last_output;++n) {
      switch(n) {
    case 0: {
    if constexpr(First<=0 && 0<=Limit) {
      if constexpr(0>high_before(First,0)) minimum_up=row[1];
      if constexpr(1>high_before(First,0)) c1=O::value(row[2]);
      if constexpr(2>high_before(First,0)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,0)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,0)) c4=O::value(row[5]);
      if constexpr(2>degree_before(First,0)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,0)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,0)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(First==0 || 0==0) w0=row[0];
      double q=c4;
      q=O::fma(a4,q,c3);
      q=O::fma(a3,q,c2);
      q=O::fma(a2,q,c1);
      const auto hi=minimum_up-1;
      const double result=O::add(O::value(minimum_up),O::fma(h,q,-O::template correction_from_word<0>(hi,w0)));
      out[(0-First)*stride]=scale_k ? O::scale(result,unsigned(1*scale_k)) : result;
    }
      break;
    }
    case 1: {
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
      if constexpr(First==1 || 1==0) w0=row[0];
      double q=c6;
      q=O::fma(a5,q,c5);
      q=O::fma(a4,q,c4);
      q=O::fma(a3,q,c3);
      q=O::fma(a2,q,c2);
      const auto hi=O::bits(c1);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<1>(hi,w0)));
      out[(1-First)*stride]=scale_k ? O::scale(result,unsigned(3*scale_k)) : result;
    }
      break;
    }
    case 2: {
    if constexpr(First<=2 && 2<=Limit) {
      if constexpr(2>high_before(First,2)) c2=O::value(row[3]);
      if constexpr(3>high_before(First,2)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,2)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,2)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,2)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,2)) c7=O::value(row[8]);
      if constexpr(2>degree_before(First,2)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,2)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,2)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,2)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==2 || 2==0) w0=row[0];
      double q=c7;
      q=O::fma(a5,q,c6);
      q=O::fma(a4,q,c5);
      q=O::fma(a3,q,c4);
      q=O::fma(a2,q,c3);
      const auto hi=O::bits(c2);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<2>(hi,w0)));
      out[(2-First)*stride]=scale_k ? O::scale(result,unsigned(5*scale_k)) : result;
    }
      break;
    }
    case 3: {
    if constexpr(First<=3 && 3<=Limit) {
      if constexpr(3>high_before(First,3)) c3=O::value(row[4]);
      if constexpr(4>high_before(First,3)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,3)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,3)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,3)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,3)) c8=O::value(row[10]);
      if constexpr(2>degree_before(First,3)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,3)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,3)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,3)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==3 || 3==0) w0=row[0];
      double q=c8;
      q=O::fma(a5,q,c7);
      q=O::fma(a4,q,c6);
      q=O::fma(a3,q,c5);
      q=O::fma(a2,q,c4);
      const auto hi=O::bits(c3);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<3>(hi,w0)));
      out[(3-First)*stride]=scale_k ? O::scale(result,unsigned(7*scale_k)) : result;
    }
      break;
    }
    case 4: {
    if constexpr(First<=4 && 4<=Limit) {
      if constexpr(4>high_before(First,4)) c4=O::value(row[5]);
      if constexpr(5>high_before(First,4)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,4)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,4)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,4)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,4)) c9=O::value(row[11]);
      if constexpr(2>degree_before(First,4)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,4)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,4)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,4)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==4 || 4==0) w0=row[0];
      double q=c9;
      q=O::fma(a5,q,c8);
      q=O::fma(a4,q,c7);
      q=O::fma(a3,q,c6);
      q=O::fma(a2,q,c5);
      const auto hi=O::bits(c4);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<4>(hi,w0)));
      out[(4-First)*stride]=scale_k ? O::scale(result,unsigned(9*scale_k)) : result;
    }
      break;
    }
    case 5: {
    if constexpr(First<=5 && 5<=Limit) {
      if constexpr(5>high_before(First,5)) c5=O::value(row[6]);
      if constexpr(6>high_before(First,5)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,5)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,5)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,5)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,5)) c10=O::value(row[12]);
      if constexpr(2>degree_before(First,5)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,5)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,5)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,5)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==5 || 5==0) w0=row[0];
      double q=c10;
      q=O::fma(a5,q,c9);
      q=O::fma(a4,q,c8);
      q=O::fma(a3,q,c7);
      q=O::fma(a2,q,c6);
      const auto hi=O::bits(c5);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<5>(hi,w0)));
      out[(5-First)*stride]=scale_k ? O::scale(result,unsigned(11*scale_k)) : result;
    }
      break;
    }
    case 6: {
    if constexpr(First<=6 && 6<=Limit) {
      if constexpr(6>high_before(First,6)) c6=O::value(row[7]);
      if constexpr(7>high_before(First,6)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,6)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,6)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,6)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,6)) c11=O::value(row[13]);
      if constexpr(2>degree_before(First,6)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,6)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,6)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,6)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==6 || 6==0) w0=row[0];
      double q=c11;
      q=O::fma(a5,q,c10);
      q=O::fma(a4,q,c9);
      q=O::fma(a3,q,c8);
      q=O::fma(a2,q,c7);
      const auto hi=O::bits(c6);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<6>(hi,w0)));
      out[(6-First)*stride]=scale_k ? O::scale(result,unsigned(13*scale_k)) : result;
    }
      break;
    }
    case 7: {
    if constexpr(First<=7 && 7<=Limit) {
      if constexpr(7>high_before(First,7)) c7=O::value(row[8]);
      if constexpr(8>high_before(First,7)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,7)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,7)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,7)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,7)) c12=O::value(row[14]);
      if constexpr(2>degree_before(First,7)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,7)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,7)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,7)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==7 || 7==0) w0=row[0];
      double q=c12;
      q=O::fma(a5,q,c11);
      q=O::fma(a4,q,c10);
      q=O::fma(a3,q,c9);
      q=O::fma(a2,q,c8);
      const auto hi=O::bits(c7);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<7>(hi,w0)));
      out[(7-First)*stride]=scale_k ? O::scale(result,unsigned(15*scale_k)) : result;
    }
      break;
    }
    case 8: {
    if constexpr(First<=8 && 8<=Limit) {
      if constexpr(8>high_before(First,8)) c8=O::value(row[10]);
      if constexpr(9>high_before(First,8)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,8)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,8)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,8)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,8)) c13=O::value(row[15]);
      if constexpr(2>degree_before(First,8)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,8)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,8)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,8)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(First==8 || 8==8) w1=row[9];
      double q=c13;
      q=O::fma(a5,q,c12);
      q=O::fma(a4,q,c11);
      q=O::fma(a3,q,c10);
      q=O::fma(a2,q,c9);
      const auto hi=O::bits(c8);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<0>(hi,w1)));
      out[(8-First)*stride]=scale_k ? O::scale(result,unsigned(17*scale_k)) : result;
    }
      break;
    }
    default: return;
      }
    }
  }
};
}
