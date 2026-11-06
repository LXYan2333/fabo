#if defined(FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#undef FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#else
#define FAST_BOYS_SIMD_0DF661439C3650BD9A59597B6A1EFEA0034F13D629D7EAAA3662EF2E69C798EC_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec/model.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {
template<> struct Kernel<fast_boys::models::m_0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec::Model> {
 using M=fast_boys::models::m_0df661439c3650bd9a59597b6a1efea0034f13d629d7eaaa3662ef2e69c798ec::Model;
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
 V a2 FAST_BOYS_INDETERMINATE;
 V a3 FAST_BOYS_INDETERMINATE;
 V a4 FAST_BOYS_INDETERMINATE;
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
 }
};
} } }
HWY_AFTER_NAMESPACE();
#endif
