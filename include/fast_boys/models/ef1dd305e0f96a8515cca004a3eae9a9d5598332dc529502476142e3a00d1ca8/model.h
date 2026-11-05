#pragma once
#include "fast_boys/boys_types.h"
namespace fast_boys::models::m_ef1dd305e0f96a8515cca004a3eae9a9d5598332dc529502476142e3a00d1ca8 {
struct Model {
  static constexpr int first=0, last=23, highest_reference_order=30;
  inline static constexpr int degrees[] = {5,5,5,5,6,6,6,6,6,6,6,6,6,7,7,7,7,7,7,7,7,7,7,7};
  static constexpr unsigned retained_bits=9, discarded_bits=43;
  static constexpr double offset=0x1.0d80000000000p+1, domain_end=0x1.5ee3e69e6ba35p+6;
  static constexpr std::uint64_t key_min=524315ULL, key_max=527055ULL;
  static constexpr std::size_t row_count=2741, row_words=34, table_bytes=1024352;
  static constexpr std::size_t word_count=table_bytes/8;
  inline static constexpr char payload_layout[]="materialized-nextup-main-tail-v3";
  inline static constexpr char canonical_payload_sha256[]="3a1d27737067dc2c1ed31db5bccadc214ebbc11aeadb82a77cd0e0bf2ba094e0";
  inline static constexpr char payload_sha256[]="fa129c1e3689ed8478db24a093aa730676333b769f206384652c71e153388a14";
  inline static constexpr char model_id[]="ef1dd305e0f96a8515cca004a3eae9a9d5598332dc529502476142e3a00d1ca8";
  static constexpr ErrorMetric error_metric=ErrorMetric::Ulp;
  static constexpr double error_limit=0x1.0000000000000p+0;
  static constexpr bool combined_table=true;
  static constexpr std::size_t main_table_bytes=745552,tail_table_bytes=278800;
  static constexpr std::size_t tail_row_offset=row_count,tail_row_count=1025;
  static constexpr unsigned tail_retained_bits=9,tail_discarded_bits=43;
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
    double c14 FAST_BOYS_INDETERMINATE;
    double c15 FAST_BOYS_INDETERMINATE;
    double c16 FAST_BOYS_INDETERMINATE;
    double c17 FAST_BOYS_INDETERMINATE;
    double c18 FAST_BOYS_INDETERMINATE;
    double c19 FAST_BOYS_INDETERMINATE;
    double c20 FAST_BOYS_INDETERMINATE;
    double c21 FAST_BOYS_INDETERMINATE;
    double c22 FAST_BOYS_INDETERMINATE;
    double c23 FAST_BOYS_INDETERMINATE;
    double c24 FAST_BOYS_INDETERMINATE;
    double c25 FAST_BOYS_INDETERMINATE;
    double c26 FAST_BOYS_INDETERMINATE;
    double c27 FAST_BOYS_INDETERMINATE;
    double c28 FAST_BOYS_INDETERMINATE;
    double c29 FAST_BOYS_INDETERMINATE;
    double c30 FAST_BOYS_INDETERMINATE;
    double a2 FAST_BOYS_INDETERMINATE;
    double a3 FAST_BOYS_INDETERMINATE;
    double a4 FAST_BOYS_INDETERMINATE;
    double a5 FAST_BOYS_INDETERMINATE;
    double a6 FAST_BOYS_INDETERMINATE;
    double a7 FAST_BOYS_INDETERMINATE;
    std::uint64_t w0 FAST_BOYS_INDETERMINATE;
    std::uint64_t w1 FAST_BOYS_INDETERMINATE;
    std::uint64_t w2 FAST_BOYS_INDETERMINATE;
    for(int n=First;n<=last_output;++n) {
      switch(n) {
    case 0: {
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
      if constexpr(First==0 || 0==0) w0=row[0];
      double q=c5;
      q=O::fma(a5,q,c4);
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
      if constexpr(10>high_before(First,4)) c10=O::value(row[12]);
      if constexpr(2>degree_before(First,4)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,4)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,4)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,4)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,4)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==4 || 4==0) w0=row[0];
      double q=c10;
      q=O::fma(a6,q,c9);
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
      if constexpr(11>high_before(First,5)) c11=O::value(row[13]);
      if constexpr(2>degree_before(First,5)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,5)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,5)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,5)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,5)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==5 || 5==0) w0=row[0];
      double q=c11;
      q=O::fma(a6,q,c10);
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
      if constexpr(12>high_before(First,6)) c12=O::value(row[14]);
      if constexpr(2>degree_before(First,6)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,6)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,6)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,6)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,6)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==6 || 6==0) w0=row[0];
      double q=c12;
      q=O::fma(a6,q,c11);
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
      if constexpr(13>high_before(First,7)) c13=O::value(row[15]);
      if constexpr(2>degree_before(First,7)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,7)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,7)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,7)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,7)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==7 || 7==0) w0=row[0];
      double q=c13;
      q=O::fma(a6,q,c12);
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
      if constexpr(14>high_before(First,8)) c14=O::value(row[16]);
      if constexpr(2>degree_before(First,8)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,8)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,8)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,8)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,8)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==8 || 8==8) w1=row[9];
      double q=c14;
      q=O::fma(a6,q,c13);
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
    case 9: {
    if constexpr(First<=9 && 9<=Limit) {
      if constexpr(9>high_before(First,9)) c9=O::value(row[11]);
      if constexpr(10>high_before(First,9)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,9)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,9)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,9)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,9)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,9)) c15=O::value(row[17]);
      if constexpr(2>degree_before(First,9)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,9)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,9)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,9)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,9)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==9 || 9==8) w1=row[9];
      double q=c15;
      q=O::fma(a6,q,c14);
      q=O::fma(a5,q,c13);
      q=O::fma(a4,q,c12);
      q=O::fma(a3,q,c11);
      q=O::fma(a2,q,c10);
      const auto hi=O::bits(c9);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<1>(hi,w1)));
      out[(9-First)*stride]=scale_k ? O::scale(result,unsigned(19*scale_k)) : result;
    }
      break;
    }
    case 10: {
    if constexpr(First<=10 && 10<=Limit) {
      if constexpr(10>high_before(First,10)) c10=O::value(row[12]);
      if constexpr(11>high_before(First,10)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,10)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,10)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,10)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,10)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,10)) c16=O::value(row[19]);
      if constexpr(2>degree_before(First,10)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,10)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,10)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,10)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,10)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==10 || 10==8) w1=row[9];
      double q=c16;
      q=O::fma(a6,q,c15);
      q=O::fma(a5,q,c14);
      q=O::fma(a4,q,c13);
      q=O::fma(a3,q,c12);
      q=O::fma(a2,q,c11);
      const auto hi=O::bits(c10);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<2>(hi,w1)));
      out[(10-First)*stride]=scale_k ? O::scale(result,unsigned(21*scale_k)) : result;
    }
      break;
    }
    case 11: {
    if constexpr(First<=11 && 11<=Limit) {
      if constexpr(11>high_before(First,11)) c11=O::value(row[13]);
      if constexpr(12>high_before(First,11)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,11)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,11)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,11)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,11)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,11)) c17=O::value(row[20]);
      if constexpr(2>degree_before(First,11)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,11)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,11)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,11)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,11)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==11 || 11==8) w1=row[9];
      double q=c17;
      q=O::fma(a6,q,c16);
      q=O::fma(a5,q,c15);
      q=O::fma(a4,q,c14);
      q=O::fma(a3,q,c13);
      q=O::fma(a2,q,c12);
      const auto hi=O::bits(c11);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<3>(hi,w1)));
      out[(11-First)*stride]=scale_k ? O::scale(result,unsigned(23*scale_k)) : result;
    }
      break;
    }
    case 12: {
    if constexpr(First<=12 && 12<=Limit) {
      if constexpr(12>high_before(First,12)) c12=O::value(row[14]);
      if constexpr(13>high_before(First,12)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,12)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,12)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,12)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,12)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,12)) c18=O::value(row[21]);
      if constexpr(2>degree_before(First,12)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,12)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,12)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,12)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,12)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(First==12 || 12==8) w1=row[9];
      double q=c18;
      q=O::fma(a6,q,c17);
      q=O::fma(a5,q,c16);
      q=O::fma(a4,q,c15);
      q=O::fma(a3,q,c14);
      q=O::fma(a2,q,c13);
      const auto hi=O::bits(c12);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<4>(hi,w1)));
      out[(12-First)*stride]=scale_k ? O::scale(result,unsigned(25*scale_k)) : result;
    }
      break;
    }
    case 13: {
    if constexpr(First<=13 && 13<=Limit) {
      if constexpr(13>high_before(First,13)) c13=O::value(row[15]);
      if constexpr(14>high_before(First,13)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,13)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,13)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,13)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,13)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,13)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,13)) c20=O::value(row[23]);
      if constexpr(2>degree_before(First,13)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,13)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,13)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,13)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,13)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,13)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==13 || 13==8) w1=row[9];
      double q=c20;
      q=O::fma(a7,q,c19);
      q=O::fma(a6,q,c18);
      q=O::fma(a5,q,c17);
      q=O::fma(a4,q,c16);
      q=O::fma(a3,q,c15);
      q=O::fma(a2,q,c14);
      const auto hi=O::bits(c13);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<5>(hi,w1)));
      out[(13-First)*stride]=scale_k ? O::scale(result,unsigned(27*scale_k)) : result;
    }
      break;
    }
    case 14: {
    if constexpr(First<=14 && 14<=Limit) {
      if constexpr(14>high_before(First,14)) c14=O::value(row[16]);
      if constexpr(15>high_before(First,14)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,14)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,14)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,14)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,14)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,14)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,14)) c21=O::value(row[24]);
      if constexpr(2>degree_before(First,14)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,14)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,14)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,14)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,14)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,14)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==14 || 14==8) w1=row[9];
      double q=c21;
      q=O::fma(a7,q,c20);
      q=O::fma(a6,q,c19);
      q=O::fma(a5,q,c18);
      q=O::fma(a4,q,c17);
      q=O::fma(a3,q,c16);
      q=O::fma(a2,q,c15);
      const auto hi=O::bits(c14);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<6>(hi,w1)));
      out[(14-First)*stride]=scale_k ? O::scale(result,unsigned(29*scale_k)) : result;
    }
      break;
    }
    case 15: {
    if constexpr(First<=15 && 15<=Limit) {
      if constexpr(15>high_before(First,15)) c15=O::value(row[17]);
      if constexpr(16>high_before(First,15)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,15)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,15)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,15)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,15)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,15)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,15)) c22=O::value(row[25]);
      if constexpr(2>degree_before(First,15)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,15)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,15)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,15)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,15)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,15)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==15 || 15==8) w1=row[9];
      double q=c22;
      q=O::fma(a7,q,c21);
      q=O::fma(a6,q,c20);
      q=O::fma(a5,q,c19);
      q=O::fma(a4,q,c18);
      q=O::fma(a3,q,c17);
      q=O::fma(a2,q,c16);
      const auto hi=O::bits(c15);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<7>(hi,w1)));
      out[(15-First)*stride]=scale_k ? O::scale(result,unsigned(31*scale_k)) : result;
    }
      break;
    }
    case 16: {
    if constexpr(First<=16 && 16<=Limit) {
      if constexpr(16>high_before(First,16)) c16=O::value(row[19]);
      if constexpr(17>high_before(First,16)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,16)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,16)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,16)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,16)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,16)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,16)) c23=O::value(row[26]);
      if constexpr(2>degree_before(First,16)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,16)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,16)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,16)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,16)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,16)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==16 || 16==16) w2=row[18];
      double q=c23;
      q=O::fma(a7,q,c22);
      q=O::fma(a6,q,c21);
      q=O::fma(a5,q,c20);
      q=O::fma(a4,q,c19);
      q=O::fma(a3,q,c18);
      q=O::fma(a2,q,c17);
      const auto hi=O::bits(c16);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<0>(hi,w2)));
      out[(16-First)*stride]=scale_k ? O::scale(result,unsigned(33*scale_k)) : result;
    }
      break;
    }
    case 17: {
    if constexpr(First<=17 && 17<=Limit) {
      if constexpr(17>high_before(First,17)) c17=O::value(row[20]);
      if constexpr(18>high_before(First,17)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,17)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,17)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,17)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,17)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,17)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,17)) c24=O::value(row[27]);
      if constexpr(2>degree_before(First,17)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,17)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,17)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,17)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,17)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,17)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==17 || 17==16) w2=row[18];
      double q=c24;
      q=O::fma(a7,q,c23);
      q=O::fma(a6,q,c22);
      q=O::fma(a5,q,c21);
      q=O::fma(a4,q,c20);
      q=O::fma(a3,q,c19);
      q=O::fma(a2,q,c18);
      const auto hi=O::bits(c17);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<1>(hi,w2)));
      out[(17-First)*stride]=scale_k ? O::scale(result,unsigned(35*scale_k)) : result;
    }
      break;
    }
    case 18: {
    if constexpr(First<=18 && 18<=Limit) {
      if constexpr(18>high_before(First,18)) c18=O::value(row[21]);
      if constexpr(19>high_before(First,18)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,18)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,18)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,18)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,18)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,18)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,18)) c25=O::value(row[28]);
      if constexpr(2>degree_before(First,18)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,18)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,18)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,18)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,18)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,18)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==18 || 18==16) w2=row[18];
      double q=c25;
      q=O::fma(a7,q,c24);
      q=O::fma(a6,q,c23);
      q=O::fma(a5,q,c22);
      q=O::fma(a4,q,c21);
      q=O::fma(a3,q,c20);
      q=O::fma(a2,q,c19);
      const auto hi=O::bits(c18);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<2>(hi,w2)));
      out[(18-First)*stride]=scale_k ? O::scale(result,unsigned(37*scale_k)) : result;
    }
      break;
    }
    case 19: {
    if constexpr(First<=19 && 19<=Limit) {
      if constexpr(19>high_before(First,19)) c19=O::value(row[22]);
      if constexpr(20>high_before(First,19)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,19)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,19)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,19)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,19)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,19)) c25=O::value(row[28]);
      if constexpr(26>high_before(First,19)) c26=O::value(row[29]);
      if constexpr(2>degree_before(First,19)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,19)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,19)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,19)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,19)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,19)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==19 || 19==16) w2=row[18];
      double q=c26;
      q=O::fma(a7,q,c25);
      q=O::fma(a6,q,c24);
      q=O::fma(a5,q,c23);
      q=O::fma(a4,q,c22);
      q=O::fma(a3,q,c21);
      q=O::fma(a2,q,c20);
      const auto hi=O::bits(c19);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<3>(hi,w2)));
      out[(19-First)*stride]=scale_k ? O::scale(result,unsigned(39*scale_k)) : result;
    }
      break;
    }
    case 20: {
    if constexpr(First<=20 && 20<=Limit) {
      if constexpr(20>high_before(First,20)) c20=O::value(row[23]);
      if constexpr(21>high_before(First,20)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,20)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,20)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,20)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,20)) c25=O::value(row[28]);
      if constexpr(26>high_before(First,20)) c26=O::value(row[29]);
      if constexpr(27>high_before(First,20)) c27=O::value(row[30]);
      if constexpr(2>degree_before(First,20)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,20)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,20)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,20)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,20)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,20)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==20 || 20==16) w2=row[18];
      double q=c27;
      q=O::fma(a7,q,c26);
      q=O::fma(a6,q,c25);
      q=O::fma(a5,q,c24);
      q=O::fma(a4,q,c23);
      q=O::fma(a3,q,c22);
      q=O::fma(a2,q,c21);
      const auto hi=O::bits(c20);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<4>(hi,w2)));
      out[(20-First)*stride]=scale_k ? O::scale(result,unsigned(41*scale_k)) : result;
    }
      break;
    }
    case 21: {
    if constexpr(First<=21 && 21<=Limit) {
      if constexpr(21>high_before(First,21)) c21=O::value(row[24]);
      if constexpr(22>high_before(First,21)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,21)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,21)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,21)) c25=O::value(row[28]);
      if constexpr(26>high_before(First,21)) c26=O::value(row[29]);
      if constexpr(27>high_before(First,21)) c27=O::value(row[30]);
      if constexpr(28>high_before(First,21)) c28=O::value(row[31]);
      if constexpr(2>degree_before(First,21)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,21)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,21)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,21)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,21)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,21)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==21 || 21==16) w2=row[18];
      double q=c28;
      q=O::fma(a7,q,c27);
      q=O::fma(a6,q,c26);
      q=O::fma(a5,q,c25);
      q=O::fma(a4,q,c24);
      q=O::fma(a3,q,c23);
      q=O::fma(a2,q,c22);
      const auto hi=O::bits(c21);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<5>(hi,w2)));
      out[(21-First)*stride]=scale_k ? O::scale(result,unsigned(43*scale_k)) : result;
    }
      break;
    }
    case 22: {
    if constexpr(First<=22 && 22<=Limit) {
      if constexpr(22>high_before(First,22)) c22=O::value(row[25]);
      if constexpr(23>high_before(First,22)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,22)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,22)) c25=O::value(row[28]);
      if constexpr(26>high_before(First,22)) c26=O::value(row[29]);
      if constexpr(27>high_before(First,22)) c27=O::value(row[30]);
      if constexpr(28>high_before(First,22)) c28=O::value(row[31]);
      if constexpr(29>high_before(First,22)) c29=O::value(row[32]);
      if constexpr(2>degree_before(First,22)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,22)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,22)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,22)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,22)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,22)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==22 || 22==16) w2=row[18];
      double q=c29;
      q=O::fma(a7,q,c28);
      q=O::fma(a6,q,c27);
      q=O::fma(a5,q,c26);
      q=O::fma(a4,q,c25);
      q=O::fma(a3,q,c24);
      q=O::fma(a2,q,c23);
      const auto hi=O::bits(c22);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<6>(hi,w2)));
      out[(22-First)*stride]=scale_k ? O::scale(result,unsigned(45*scale_k)) : result;
    }
      break;
    }
    case 23: {
    if constexpr(First<=23 && 23<=Limit) {
      if constexpr(23>high_before(First,23)) c23=O::value(row[26]);
      if constexpr(24>high_before(First,23)) c24=O::value(row[27]);
      if constexpr(25>high_before(First,23)) c25=O::value(row[28]);
      if constexpr(26>high_before(First,23)) c26=O::value(row[29]);
      if constexpr(27>high_before(First,23)) c27=O::value(row[30]);
      if constexpr(28>high_before(First,23)) c28=O::value(row[31]);
      if constexpr(29>high_before(First,23)) c29=O::value(row[32]);
      if constexpr(30>high_before(First,23)) c30=O::value(row[33]);
      if constexpr(2>degree_before(First,23)) a2=O::mul(h,0x1.0000000000000p-1);
      if constexpr(3>degree_before(First,23)) a3=O::mul(h,0x1.5555555555555p-2);
      if constexpr(4>degree_before(First,23)) a4=O::mul(h,0x1.0000000000000p-2);
      if constexpr(5>degree_before(First,23)) a5=O::mul(h,0x1.999999999999ap-3);
      if constexpr(6>degree_before(First,23)) a6=O::mul(h,0x1.5555555555555p-3);
      if constexpr(7>degree_before(First,23)) a7=O::mul(h,0x1.2492492492492p-3);
      if constexpr(First==23 || 23==16) w2=row[18];
      double q=c30;
      q=O::fma(a7,q,c29);
      q=O::fma(a6,q,c28);
      q=O::fma(a5,q,c27);
      q=O::fma(a4,q,c26);
      q=O::fma(a3,q,c25);
      q=O::fma(a2,q,c24);
      const auto hi=O::bits(c23);
      const double result=O::add(O::value(hi+1),O::fma(h,q,-O::template correction_from_word<7>(hi,w2)));
      out[(23-First)*stride]=scale_k ? O::scale(result,unsigned(47*scale_k)) : result;
    }
      break;
    }
    default: return;
      }
    }
  }
};
}
