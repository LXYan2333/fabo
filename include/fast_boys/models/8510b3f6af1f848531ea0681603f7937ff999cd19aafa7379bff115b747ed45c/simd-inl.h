#if defined(FAST_BOYS_SIMD_8510B3F6AF1F848531EA0681603F7937FF999CD19AAFA7379BFF115B747ED45C_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_8510B3F6AF1F848531EA0681603F7937FF999CD19AAFA7379BFF115B747ED45C_H_
#undef FAST_BOYS_SIMD_8510B3F6AF1F848531EA0681603F7937FF999CD19AAFA7379BFF115B747ED45C_H_
#else
#define FAST_BOYS_SIMD_8510B3F6AF1F848531EA0681603F7937FF999CD19AAFA7379BFF115B747ED45C_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/8510b3f6af1f848531ea0681603f7937ff999cd19aafa7379bff115b747ed45c/model.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {
template<> struct Kernel<fast_boys::models::m_8510b3f6af1f848531ea0681603f7937ff999cd19aafa7379bff115b747ed45c::Model> {
 using M=fast_boys::models::m_8510b3f6af1f848531ea0681603f7937ff999cd19aafa7379bff115b747ed45c::Model;
 template<int First,int Last,bool Software,class... Outputs>
 static HWY_INLINE void run(const std::uint64_t* data,const V x,Outputs& HWY_RESTRICT ...out) {
 using namespace detail;
 U row FAST_BOYS_INDETERMINATE;
 U k FAST_BOYS_INDETERMINATE;
 V h FAST_BOYS_INDETERMINATE;
 PrepareCombinedCoordinates<M>(x,row,h,k);
 static_assert(M::word_count-1<=INT64_MAX,"gather index exceeds signed range");
 const auto two_k=hn::Add(k,k);
 auto scale_power=k;
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
 V a2 FAST_BOYS_INDETERMINATE;
 V a3 FAST_BOYS_INDETERMINATE;
 V a4 FAST_BOYS_INDETERMINATE;
 V a5 FAST_BOYS_INDETERMINATE;
 V a6 FAST_BOYS_INDETERMINATE;
 U w0 FAST_BOYS_INDETERMINATE;
 U w1 FAST_BOYS_INDETERMINATE;
 if constexpr(First<=0 && 0<=Last) {
 if constexpr(0>M::high_before(First,0)) c0=Float(hn::Sub(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(1))),SU(1)));
 if constexpr(1>M::high_before(First,0)) c1=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(2))));
 if constexpr(2>M::high_before(First,0)) c2=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(3))));
 if constexpr(3>M::high_before(First,0)) c3=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(4))));
 if constexpr(4>M::high_before(First,0)) c4=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5))));
 if constexpr(First==0 || 0==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,0)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,0)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,0)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 V q=c4;
 q=Fma(a4,q,c3);
 q=Fma(a3,q,c2);
 q=Fma(a2,q,c1);
 const auto hi=Bits(c0);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<0>(hi,w0)));
 At<0-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(0<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=1 && 1<=Last) {
 if constexpr(1>M::high_before(First,1)) c1=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(2))));
 if constexpr(2>M::high_before(First,1)) c2=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(3))));
 if constexpr(3>M::high_before(First,1)) c3=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(4))));
 if constexpr(4>M::high_before(First,1)) c4=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5))));
 if constexpr(5>M::high_before(First,1)) c5=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6))));
 if constexpr(6>M::high_before(First,1)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(First==1 || 1==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,1)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,1)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,1)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,1)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c6;
 q=Fma(a5,q,c5);
 q=Fma(a4,q,c4);
 q=Fma(a3,q,c3);
 q=Fma(a2,q,c2);
 const auto hi=Bits(c1);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<1>(hi,w0)));
 At<1-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(1<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=2 && 2<=Last) {
 if constexpr(2>M::high_before(First,2)) c2=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(3))));
 if constexpr(3>M::high_before(First,2)) c3=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(4))));
 if constexpr(4>M::high_before(First,2)) c4=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5))));
 if constexpr(5>M::high_before(First,2)) c5=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6))));
 if constexpr(6>M::high_before(First,2)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(7>M::high_before(First,2)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(First==2 || 2==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,2)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,2)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,2)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,2)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c7;
 q=Fma(a5,q,c6);
 q=Fma(a4,q,c5);
 q=Fma(a3,q,c4);
 q=Fma(a2,q,c3);
 const auto hi=Bits(c2);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<2>(hi,w0)));
 At<2-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(2<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=3 && 3<=Last) {
 if constexpr(3>M::high_before(First,3)) c3=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(4))));
 if constexpr(4>M::high_before(First,3)) c4=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5))));
 if constexpr(5>M::high_before(First,3)) c5=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6))));
 if constexpr(6>M::high_before(First,3)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(7>M::high_before(First,3)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(8>M::high_before(First,3)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(First==3 || 3==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,3)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,3)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,3)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,3)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c8;
 q=Fma(a5,q,c7);
 q=Fma(a4,q,c6);
 q=Fma(a3,q,c5);
 q=Fma(a2,q,c4);
 const auto hi=Bits(c3);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<3>(hi,w0)));
 At<3-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(3<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=4 && 4<=Last) {
 if constexpr(4>M::high_before(First,4)) c4=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5))));
 if constexpr(5>M::high_before(First,4)) c5=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6))));
 if constexpr(6>M::high_before(First,4)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(7>M::high_before(First,4)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(8>M::high_before(First,4)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(9>M::high_before(First,4)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(First==4 || 4==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,4)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,4)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,4)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,4)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c9;
 q=Fma(a5,q,c8);
 q=Fma(a4,q,c7);
 q=Fma(a3,q,c6);
 q=Fma(a2,q,c5);
 const auto hi=Bits(c4);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<4>(hi,w0)));
 At<4-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(4<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=5 && 5<=Last) {
 if constexpr(5>M::high_before(First,5)) c5=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6))));
 if constexpr(6>M::high_before(First,5)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(7>M::high_before(First,5)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(8>M::high_before(First,5)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(9>M::high_before(First,5)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(10>M::high_before(First,5)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(First==5 || 5==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,5)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,5)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,5)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,5)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c10;
 q=Fma(a5,q,c9);
 q=Fma(a4,q,c8);
 q=Fma(a3,q,c7);
 q=Fma(a2,q,c6);
 const auto hi=Bits(c5);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<5>(hi,w0)));
 At<5-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(5<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=6 && 6<=Last) {
 if constexpr(6>M::high_before(First,6)) c6=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7))));
 if constexpr(7>M::high_before(First,6)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(8>M::high_before(First,6)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(9>M::high_before(First,6)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(10>M::high_before(First,6)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(11>M::high_before(First,6)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(First==6 || 6==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,6)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,6)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,6)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,6)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c11;
 q=Fma(a5,q,c10);
 q=Fma(a4,q,c9);
 q=Fma(a3,q,c8);
 q=Fma(a2,q,c7);
 const auto hi=Bits(c6);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<6>(hi,w0)));
 At<6-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(6<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=7 && 7<=Last) {
 if constexpr(7>M::high_before(First,7)) c7=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8))));
 if constexpr(8>M::high_before(First,7)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(9>M::high_before(First,7)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(10>M::high_before(First,7)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(11>M::high_before(First,7)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(12>M::high_before(First,7)) c12=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(14))));
 if constexpr(First==7 || 7==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,7)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,7)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,7)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,7)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c12;
 q=Fma(a5,q,c11);
 q=Fma(a4,q,c10);
 q=Fma(a3,q,c9);
 q=Fma(a2,q,c8);
 const auto hi=Bits(c7);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<7>(hi,w0)));
 At<7-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(7<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=8 && 8<=Last) {
 if constexpr(8>M::high_before(First,8)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
 if constexpr(9>M::high_before(First,8)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(10>M::high_before(First,8)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(11>M::high_before(First,8)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(12>M::high_before(First,8)) c12=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(14))));
 if constexpr(13>M::high_before(First,8)) c13=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(15))));
 if constexpr(First==8 || 8==8) w1=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9)));
 if constexpr(2>M::degree_before(First,8)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,8)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,8)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,8)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 V q=c13;
 q=Fma(a5,q,c12);
 q=Fma(a4,q,c11);
 q=Fma(a3,q,c10);
 q=Fma(a2,q,c9);
 const auto hi=Bits(c8);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<0>(hi,w1)));
 At<8-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(8<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=9 && 9<=Last) {
 if constexpr(9>M::high_before(First,9)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(11))));
 if constexpr(10>M::high_before(First,9)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(11>M::high_before(First,9)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(12>M::high_before(First,9)) c12=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(14))));
 if constexpr(13>M::high_before(First,9)) c13=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(15))));
 if constexpr(14>M::high_before(First,9)) c14=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(16))));
 if constexpr(15>M::high_before(First,9)) c15=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(17))));
 if constexpr(First==9 || 9==8) w1=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9)));
 if constexpr(2>M::degree_before(First,9)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,9)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,9)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,9)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 if constexpr(6>M::degree_before(First,9)) a6=RoundedMul(h,S(0x1.5555555555555p-3));
 V q=c15;
 q=Fma(a6,q,c14);
 q=Fma(a5,q,c13);
 q=Fma(a4,q,c12);
 q=Fma(a3,q,c11);
 q=Fma(a2,q,c10);
 const auto hi=Bits(c9);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<1>(hi,w1)));
 At<9-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(9<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=10 && 10<=Last) {
 if constexpr(10>M::high_before(First,10)) c10=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(12))));
 if constexpr(11>M::high_before(First,10)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(12>M::high_before(First,10)) c12=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(14))));
 if constexpr(13>M::high_before(First,10)) c13=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(15))));
 if constexpr(14>M::high_before(First,10)) c14=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(16))));
 if constexpr(15>M::high_before(First,10)) c15=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(17))));
 if constexpr(16>M::high_before(First,10)) c16=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(18))));
 if constexpr(First==10 || 10==8) w1=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9)));
 if constexpr(2>M::degree_before(First,10)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,10)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,10)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,10)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 if constexpr(6>M::degree_before(First,10)) a6=RoundedMul(h,S(0x1.5555555555555p-3));
 V q=c16;
 q=Fma(a6,q,c15);
 q=Fma(a5,q,c14);
 q=Fma(a4,q,c13);
 q=Fma(a3,q,c12);
 q=Fma(a2,q,c11);
 const auto hi=Bits(c10);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<2>(hi,w1)));
 At<10-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(10<Last) scale_power=hn::Add(scale_power,two_k);
 if constexpr(First<=11 && 11<=Last) {
 if constexpr(11>M::high_before(First,11)) c11=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(13))));
 if constexpr(12>M::high_before(First,11)) c12=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(14))));
 if constexpr(13>M::high_before(First,11)) c13=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(15))));
 if constexpr(14>M::high_before(First,11)) c14=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(16))));
 if constexpr(15>M::high_before(First,11)) c15=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(17))));
 if constexpr(16>M::high_before(First,11)) c16=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(18))));
 if constexpr(17>M::high_before(First,11)) c17=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(19))));
 if constexpr(First==11 || 11==8) w1=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9)));
 if constexpr(2>M::degree_before(First,11)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,11)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,11)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 if constexpr(5>M::degree_before(First,11)) a5=RoundedMul(h,S(0x1.999999999999ap-3));
 if constexpr(6>M::degree_before(First,11)) a6=RoundedMul(h,S(0x1.5555555555555p-3));
 V q=c17;
 q=Fma(a6,q,c16);
 q=Fma(a5,q,c15);
 q=Fma(a4,q,c14);
 q=Fma(a3,q,c13);
 q=Fma(a2,q,c12);
 const auto hi=Bits(c11);
 const auto value=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,CorrectionFromWord<3>(hi,w1)));
 At<11-First>(out...)=Scale(Bits(value),scale_power);
 }
 if constexpr(11<Last) scale_power=hn::Add(scale_power,two_k);
 }
};
} } }
HWY_AFTER_NAMESPACE();
#endif
