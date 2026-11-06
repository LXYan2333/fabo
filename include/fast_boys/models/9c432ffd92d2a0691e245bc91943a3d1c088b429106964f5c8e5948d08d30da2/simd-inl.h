#if defined(FAST_BOYS_SIMD_9C432FFD92D2A0691E245BC91943A3D1C088B429106964F5C8E5948D08D30DA2_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_9C432FFD92D2A0691E245BC91943A3D1C088B429106964F5C8E5948D08D30DA2_H_
#undef FAST_BOYS_SIMD_9C432FFD92D2A0691E245BC91943A3D1C088B429106964F5C8E5948D08D30DA2_H_
#else
#define FAST_BOYS_SIMD_9C432FFD92D2A0691E245BC91943A3D1C088B429106964F5C8E5948D08D30DA2_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/9c432ffd92d2a0691e245bc91943a3d1c088b429106964f5c8e5948d08d30da2/model.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {
template<> struct Kernel<fast_boys::models::m_9c432ffd92d2a0691e245bc91943a3d1c088b429106964f5c8e5948d08d30da2::Model> {
 using M=fast_boys::models::m_9c432ffd92d2a0691e245bc91943a3d1c088b429106964f5c8e5948d08d30da2::Model;
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
 V a2 FAST_BOYS_INDETERMINATE;
 V a3 FAST_BOYS_INDETERMINATE;
 V a4 FAST_BOYS_INDETERMINATE;
 V a5 FAST_BOYS_INDETERMINATE;
 U w0 FAST_BOYS_INDETERMINATE;
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
 if constexpr(First==1 || 1==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,1)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,1)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,1)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 V q=c5;
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
 if constexpr(First==2 || 2==0) w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 if constexpr(2>M::degree_before(First,2)) a2=RoundedMul(h,S(0x1.0000000000000p-1));
 if constexpr(3>M::degree_before(First,2)) a3=RoundedMul(h,S(0x1.5555555555555p-2));
 if constexpr(4>M::degree_before(First,2)) a4=RoundedMul(h,S(0x1.0000000000000p-2));
 V q=c6;
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
 if constexpr(8>M::high_before(First,3)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9))));
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
 if constexpr(8>M::high_before(First,4)) c8=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(9))));
 if constexpr(9>M::high_before(First,4)) c9=Float(Gather<Software,M::word_count-1>(data,hn::Add(row,SU(10))));
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
 }
};
} } }
HWY_AFTER_NAMESPACE();
#endif
