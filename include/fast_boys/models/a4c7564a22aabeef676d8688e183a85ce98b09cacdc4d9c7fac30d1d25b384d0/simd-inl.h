#if defined(FAST_BOYS_SIMD_A4C7564A22AABEEF676D8688E183A85CE98B09CACDC4D9C7FAC30D1D25B384D0_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_A4C7564A22AABEEF676D8688E183A85CE98B09CACDC4D9C7FAC30D1D25B384D0_H_
#undef FAST_BOYS_SIMD_A4C7564A22AABEEF676D8688E183A85CE98B09CACDC4D9C7FAC30D1D25B384D0_H_
#else
#define FAST_BOYS_SIMD_A4C7564A22AABEEF676D8688E183A85CE98B09CACDC4D9C7FAC30D1D25B384D0_H_
#endif
#include "fast_boys/simd.h"
#include "fast_boys/models/a4c7564a22aabeef676d8688e183a85ce98b09cacdc4d9c7fac30d1d25b384d0/model.h"
HWY_BEFORE_NAMESPACE();
namespace fast_boys { namespace simd { namespace HWY_NAMESPACE {
template<> struct TailKernel<fast_boys::models::m_a4c7564a22aabeef676d8688e183a85ce98b09cacdc4d9c7fac30d1d25b384d0::Model> {
 using M=fast_boys::models::m_a4c7564a22aabeef676d8688e183a85ce98b09cacdc4d9c7fac30d1d25b384d0::Model;
 template<int First,int Last,bool Software,class... Outputs>
 static HWY_INLINE void run(const std::uint64_t* data,const V x,Mask active,Outputs& HWY_RESTRICT ...out) {
 using namespace detail;
 const auto bits=Bits(x);
 const auto exponent=hn::Sub(hn::ShiftRight<52>(bits),SU(1023));
 const auto k=hn::ShiftRight<1>(exponent);
 const auto u=Float(hn::Or(hn::And(bits,SU(0xfffffffffffffULL)),hn::ShiftLeft<52>(hn::Add(SU(1023),hn::And(exponent,SU(1))))));
 const auto key=hn::ShiftRight<46>(hn::Add(Bits(u),SU(1ULL<<45)));
 const auto row=MultiplyConstant<9,128>(hn::Sub(key,SU(65472)));
 const auto r=Float(hn::ShiftLeft<46>(key)),h=RoundedSub(r,u),t=RoundedAdd(r,r);
 const auto w0=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(0)));
 const auto w1=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(1)));
 const auto w2=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(2)));
 const auto w3=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(3)));
 const auto w4=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(4)));
 const auto w5=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(5)));
 const auto w6=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(6)));
 const auto w7=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(7)));
 const auto w8=Gather<Software,M::word_count-1>(data,hn::Add(row,SU(8)));
 const auto g36=Float(w0);
 const auto byte35=ByteAt<0>(w1);
 const auto patch35=hn::Sub(hn::Xor(byte35,SU(128)),SU(128));
 const auto g35=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g36),S(0x1.cd85689039b0bp-7))),patch35));
 const auto byte34=ByteAt<1>(w1);
 const auto patch34=hn::Sub(hn::Xor(byte34,SU(128)),SU(128));
 const auto g34=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g35),S(0x1.dae6076b981dbp-7))),patch34));
 const auto byte33=ByteAt<2>(w1);
 const auto patch33=hn::Sub(hn::Xor(byte33,SU(128)),SU(128));
 const auto g33=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g34),S(0x1.e9131abf0b767p-7))),patch33));
 const auto byte32=ByteAt<3>(w1);
 const auto patch32=hn::Sub(hn::Xor(byte32,SU(128)),SU(128));
 const auto g32=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g33),S(0x1.f81f81f81f820p-7))),patch32));
 const auto byte31=ByteAt<4>(w1);
 const auto patch31=hn::Sub(hn::Xor(byte31,SU(128)),SU(128));
 const auto g31=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g32),S(0x1.0410410410410p-6))),patch31));
 const auto byte30=ByteAt<5>(w1);
 const auto patch30=hn::Sub(hn::Xor(byte30,SU(128)),SU(128));
 const auto g30=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g31),S(0x1.0c9714fbcda3bp-6))),patch30));
 const auto byte29=ByteAt<6>(w1);
 const auto patch29=hn::Sub(hn::Xor(byte29,SU(128)),SU(128));
 const auto g29=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g30),S(0x1.15b1e5f75270dp-6))),patch29));
 const auto byte28=ByteAt<7>(w1);
 const auto patch28=hn::Sub(hn::Xor(byte28,SU(128)),SU(128));
 const auto g28=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g29),S(0x1.1f7047dc11f70p-6))),patch28));
 const auto byte27=ByteAt<0>(w2);
 const auto patch27=hn::Sub(hn::Xor(byte27,SU(128)),SU(128));
 const auto g27=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g28),S(0x1.29e4129e4129ep-6))),patch27));
 const auto byte26=ByteAt<1>(w2);
 const auto patch26=hn::Sub(hn::Xor(byte26,SU(128)),SU(128));
 const auto g26=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g27),S(0x1.3521cfb2b78c1p-6))),patch26));
 const auto byte25=ByteAt<2>(w2);
 const auto patch25=hn::Sub(hn::Xor(byte25,SU(128)),SU(128));
 const auto g25=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g26),S(0x1.4141414141414p-6))),patch25));
 const auto byte24=ByteAt<3>(w2);
 const auto patch24=hn::Sub(hn::Xor(byte24,SU(128)),SU(128));
 const auto g24=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g25),S(0x1.4e5e0a72f0539p-6))),patch24));
 const auto byte23=ByteAt<4>(w2);
 const auto patch23=hn::Sub(hn::Xor(byte23,SU(128)),SU(128));
 const auto g23=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g24),S(0x1.5c9882b931057p-6))),patch23));
 const auto byte22=ByteAt<5>(w2);
 const auto patch22=hn::Sub(hn::Xor(byte22,SU(128)),SU(128));
 const auto g22=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g23),S(0x1.6c16c16c16c17p-6))),patch22));
 const auto byte21=ByteAt<6>(w2);
 const auto patch21=hn::Sub(hn::Xor(byte21,SU(128)),SU(128));
 const auto g21=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g22),S(0x1.7d05f417d05f4p-6))),patch21));
 const auto byte20=ByteAt<7>(w2);
 const auto patch20=hn::Sub(hn::Xor(byte20,SU(128)),SU(128));
 const auto g20=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g21),S(0x1.8f9c18f9c18fap-6))),patch20));
 const auto byte19=ByteAt<0>(w3);
 const auto patch19=hn::Sub(hn::Xor(byte19,SU(128)),SU(128));
 const auto g19=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g20),S(0x1.a41a41a41a41ap-6))),patch19));
 const auto byte18=ByteAt<1>(w3);
 const auto patch18=hn::Sub(hn::Xor(byte18,SU(128)),SU(128));
 const auto g18=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g19),S(0x1.bacf914c1bad0p-6))),patch18));
 const auto byte17=ByteAt<2>(w3);
 const auto patch17=hn::Sub(hn::Xor(byte17,SU(128)),SU(128));
 const auto g17=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g18),S(0x1.d41d41d41d41dp-6))),patch17));
 const auto byte16=ByteAt<3>(w3);
 const auto patch16=hn::Sub(hn::Xor(byte16,SU(128)),SU(128));
 const auto g16=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g17),S(0x1.f07c1f07c1f08p-6))),patch16));
 const auto byte15=ByteAt<4>(w3);
 const auto patch15=hn::Sub(hn::Xor(byte15,SU(128)),SU(128));
 const auto g15=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g16),S(0x1.0842108421084p-5))),patch15));
 const auto byte14=ByteAt<5>(w3);
 const auto patch14=hn::Sub(hn::Xor(byte14,SU(128)),SU(128));
 const auto g14=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g15),S(0x1.1a7b9611a7b96p-5))),patch14));
 const auto byte13=ByteAt<6>(w3);
 const auto patch13=hn::Sub(hn::Xor(byte13,SU(128)),SU(128));
 const auto g13=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g14),S(0x1.2f684bda12f68p-5))),patch13));
 const auto byte12=ByteAt<7>(w3);
 const auto patch12=hn::Sub(hn::Xor(byte12,SU(128)),SU(128));
 const auto g12=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g13),S(0x1.47ae147ae147bp-5))),patch12));
 const auto byte11=ByteAt<0>(w4);
 const auto patch11=hn::Sub(hn::Xor(byte11,SU(128)),SU(128));
 const auto g11=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g12),S(0x1.642c8590b2164p-5))),patch11));
 const auto byte10=ByteAt<1>(w4);
 const auto patch10=hn::Sub(hn::Xor(byte10,SU(128)),SU(128));
 const auto g10=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g11),S(0x1.8618618618618p-5))),patch10));
 const auto byte9=ByteAt<2>(w4);
 const auto patch9=hn::Sub(hn::Xor(byte9,SU(128)),SU(128));
 const auto g9=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g10),S(0x1.af286bca1af28p-5))),patch9));
 const auto byte8=ByteAt<3>(w4);
 const auto patch8=hn::Sub(hn::Xor(byte8,SU(128)),SU(128));
 const auto g8=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g9),S(0x1.e1e1e1e1e1e1ep-5))),patch8));
 const auto byte7=ByteAt<4>(w4);
 const auto patch7=hn::Sub(hn::Xor(byte7,SU(128)),SU(128));
 const auto g7=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g8),S(0x1.1111111111111p-4))),patch7));
 const auto byte6=ByteAt<5>(w4);
 const auto patch6=hn::Sub(hn::Xor(byte6,SU(128)),SU(128));
 const auto g6=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g7),S(0x1.3b13b13b13b14p-4))),patch6));
 const auto byte5=ByteAt<6>(w4);
 const auto patch5=hn::Sub(hn::Xor(byte5,SU(128)),SU(128));
 const auto g5=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g6),S(0x1.745d1745d1746p-4))),patch5));
 const auto byte4=ByteAt<7>(w4);
 const auto patch4=hn::Sub(hn::Xor(byte4,SU(128)),SU(128));
 const auto g4=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g5),S(0x1.c71c71c71c71cp-4))),patch4));
 const auto byte3=ByteAt<0>(w5);
 const auto patch3=hn::Sub(hn::Xor(byte3,SU(128)),SU(128));
 const auto g3=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g4),S(0x1.2492492492492p-3))),patch3));
 const auto byte2=ByteAt<1>(w5);
 const auto patch2=hn::Sub(hn::Xor(byte2,SU(128)),SU(128));
 const auto g2=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g3),S(0x1.999999999999ap-3))),patch2));
 const auto byte1=ByteAt<2>(w5);
 const auto patch1=hn::Sub(hn::Xor(byte1,SU(128)),SU(128));
 const auto g1=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g2),S(0x1.5555555555555p-2))),patch1));
 const auto byte0=ByteAt<3>(w5);
 const auto patch0=hn::Sub(hn::Xor(byte0,SU(128)),SU(128));
 const auto g0=Float(hn::Add(Bits(RoundedMul(RoundedMul(t,g1),S(0x1.0000000000000p+0))),patch0));
 const auto a2=RoundedMul(h,S(0x1.0000000000000p-1));
 const auto a3=RoundedMul(h,S(0x1.5555555555555p-2));
 const auto a4=RoundedMul(h,S(0x1.0000000000000p-2));
 const auto a5=RoundedMul(h,S(0x1.999999999999ap-3));
 const auto a6=RoundedMul(h,S(0x1.5555555555555p-3));
 const auto a7=RoundedMul(h,S(0x1.2492492492492p-3));
 const auto a8=RoundedMul(h,S(0x1.0000000000000p-3));
 const auto a9=RoundedMul(h,S(0x1.c71c71c71c71cp-4));
 const auto a10=RoundedMul(h,S(0x1.999999999999ap-4));
 const auto a11=RoundedMul(h,S(0x1.745d1745d1746p-4));
 const auto a12=RoundedMul(h,S(0x1.5555555555555p-4));
 if constexpr(First<=0 && 0<=Last) {
 V q=g12;
 q=Fma(a12,q,g11);
 q=Fma(a11,q,g10);
 q=Fma(a10,q,g9);
 q=Fma(a9,q,g8);
 q=Fma(a8,q,g7);
 q=Fma(a7,q,g6);
 q=Fma(a6,q,g5);
 q=Fma(a5,q,g4);
 q=Fma(a4,q,g3);
 q=Fma(a3,q,g2);
 q=Fma(a2,q,g1);
 const auto hi=Bits(g0);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<4>(w5))));
 At<0-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<1,511>(k)),At<0-First>(out...));
 }
 if constexpr(First<=1 && 1<=Last) {
 V q=g13;
 q=Fma(a12,q,g12);
 q=Fma(a11,q,g11);
 q=Fma(a10,q,g10);
 q=Fma(a9,q,g9);
 q=Fma(a8,q,g8);
 q=Fma(a7,q,g7);
 q=Fma(a6,q,g6);
 q=Fma(a5,q,g5);
 q=Fma(a4,q,g4);
 q=Fma(a3,q,g3);
 q=Fma(a2,q,g2);
 const auto hi=Bits(g1);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<5>(w5))));
 At<1-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<3,511>(k)),At<1-First>(out...));
 }
 if constexpr(First<=2 && 2<=Last) {
 V q=g14;
 q=Fma(a12,q,g13);
 q=Fma(a11,q,g12);
 q=Fma(a10,q,g11);
 q=Fma(a9,q,g10);
 q=Fma(a8,q,g9);
 q=Fma(a7,q,g8);
 q=Fma(a6,q,g7);
 q=Fma(a5,q,g6);
 q=Fma(a4,q,g5);
 q=Fma(a3,q,g4);
 q=Fma(a2,q,g3);
 const auto hi=Bits(g2);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<6>(w5))));
 At<2-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<5,511>(k)),At<2-First>(out...));
 }
 if constexpr(First<=3 && 3<=Last) {
 V q=g15;
 q=Fma(a12,q,g14);
 q=Fma(a11,q,g13);
 q=Fma(a10,q,g12);
 q=Fma(a9,q,g11);
 q=Fma(a8,q,g10);
 q=Fma(a7,q,g9);
 q=Fma(a6,q,g8);
 q=Fma(a5,q,g7);
 q=Fma(a4,q,g6);
 q=Fma(a3,q,g5);
 q=Fma(a2,q,g4);
 const auto hi=Bits(g3);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<7>(w5))));
 At<3-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<7,511>(k)),At<3-First>(out...));
 }
 if constexpr(First<=4 && 4<=Last) {
 V q=g16;
 q=Fma(a12,q,g15);
 q=Fma(a11,q,g14);
 q=Fma(a10,q,g13);
 q=Fma(a9,q,g12);
 q=Fma(a8,q,g11);
 q=Fma(a7,q,g10);
 q=Fma(a6,q,g9);
 q=Fma(a5,q,g8);
 q=Fma(a4,q,g7);
 q=Fma(a3,q,g6);
 q=Fma(a2,q,g5);
 const auto hi=Bits(g4);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<0>(w6))));
 At<4-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<9,511>(k)),At<4-First>(out...));
 }
 if constexpr(First<=5 && 5<=Last) {
 V q=g17;
 q=Fma(a12,q,g16);
 q=Fma(a11,q,g15);
 q=Fma(a10,q,g14);
 q=Fma(a9,q,g13);
 q=Fma(a8,q,g12);
 q=Fma(a7,q,g11);
 q=Fma(a6,q,g10);
 q=Fma(a5,q,g9);
 q=Fma(a4,q,g8);
 q=Fma(a3,q,g7);
 q=Fma(a2,q,g6);
 const auto hi=Bits(g5);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<1>(w6))));
 At<5-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<11,511>(k)),At<5-First>(out...));
 }
 if constexpr(First<=6 && 6<=Last) {
 V q=g18;
 q=Fma(a12,q,g17);
 q=Fma(a11,q,g16);
 q=Fma(a10,q,g15);
 q=Fma(a9,q,g14);
 q=Fma(a8,q,g13);
 q=Fma(a7,q,g12);
 q=Fma(a6,q,g11);
 q=Fma(a5,q,g10);
 q=Fma(a4,q,g9);
 q=Fma(a3,q,g8);
 q=Fma(a2,q,g7);
 const auto hi=Bits(g6);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<2>(w6))));
 At<6-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<13,511>(k)),At<6-First>(out...));
 }
 if constexpr(First<=7 && 7<=Last) {
 V q=g19;
 q=Fma(a12,q,g18);
 q=Fma(a11,q,g17);
 q=Fma(a10,q,g16);
 q=Fma(a9,q,g15);
 q=Fma(a8,q,g14);
 q=Fma(a7,q,g13);
 q=Fma(a6,q,g12);
 q=Fma(a5,q,g11);
 q=Fma(a4,q,g10);
 q=Fma(a3,q,g9);
 q=Fma(a2,q,g8);
 const auto hi=Bits(g7);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<3>(w6))));
 At<7-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<15,511>(k)),At<7-First>(out...));
 }
 if constexpr(First<=8 && 8<=Last) {
 V q=g20;
 q=Fma(a12,q,g19);
 q=Fma(a11,q,g18);
 q=Fma(a10,q,g17);
 q=Fma(a9,q,g16);
 q=Fma(a8,q,g15);
 q=Fma(a7,q,g14);
 q=Fma(a6,q,g13);
 q=Fma(a5,q,g12);
 q=Fma(a4,q,g11);
 q=Fma(a3,q,g10);
 q=Fma(a2,q,g9);
 const auto hi=Bits(g8);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<4>(w6))));
 At<8-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<17,511>(k)),At<8-First>(out...));
 }
 if constexpr(First<=9 && 9<=Last) {
 V q=g21;
 q=Fma(a12,q,g20);
 q=Fma(a11,q,g19);
 q=Fma(a10,q,g18);
 q=Fma(a9,q,g17);
 q=Fma(a8,q,g16);
 q=Fma(a7,q,g15);
 q=Fma(a6,q,g14);
 q=Fma(a5,q,g13);
 q=Fma(a4,q,g12);
 q=Fma(a3,q,g11);
 q=Fma(a2,q,g10);
 const auto hi=Bits(g9);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<5>(w6))));
 At<9-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<19,511>(k)),At<9-First>(out...));
 }
 if constexpr(First<=10 && 10<=Last) {
 V q=g22;
 q=Fma(a12,q,g21);
 q=Fma(a11,q,g20);
 q=Fma(a10,q,g19);
 q=Fma(a9,q,g18);
 q=Fma(a8,q,g17);
 q=Fma(a7,q,g16);
 q=Fma(a6,q,g15);
 q=Fma(a5,q,g14);
 q=Fma(a4,q,g13);
 q=Fma(a3,q,g12);
 q=Fma(a2,q,g11);
 const auto hi=Bits(g10);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<6>(w6))));
 At<10-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<21,511>(k)),At<10-First>(out...));
 }
 if constexpr(First<=11 && 11<=Last) {
 V q=g23;
 q=Fma(a12,q,g22);
 q=Fma(a11,q,g21);
 q=Fma(a10,q,g20);
 q=Fma(a9,q,g19);
 q=Fma(a8,q,g18);
 q=Fma(a7,q,g17);
 q=Fma(a6,q,g16);
 q=Fma(a5,q,g15);
 q=Fma(a4,q,g14);
 q=Fma(a3,q,g13);
 q=Fma(a2,q,g12);
 const auto hi=Bits(g11);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<7>(w6))));
 At<11-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<23,511>(k)),At<11-First>(out...));
 }
 if constexpr(First<=12 && 12<=Last) {
 V q=g24;
 q=Fma(a12,q,g23);
 q=Fma(a11,q,g22);
 q=Fma(a10,q,g21);
 q=Fma(a9,q,g20);
 q=Fma(a8,q,g19);
 q=Fma(a7,q,g18);
 q=Fma(a6,q,g17);
 q=Fma(a5,q,g16);
 q=Fma(a4,q,g15);
 q=Fma(a3,q,g14);
 q=Fma(a2,q,g13);
 const auto hi=Bits(g12);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<0>(w7))));
 At<12-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<25,511>(k)),At<12-First>(out...));
 }
 if constexpr(First<=13 && 13<=Last) {
 V q=g25;
 q=Fma(a12,q,g24);
 q=Fma(a11,q,g23);
 q=Fma(a10,q,g22);
 q=Fma(a9,q,g21);
 q=Fma(a8,q,g20);
 q=Fma(a7,q,g19);
 q=Fma(a6,q,g18);
 q=Fma(a5,q,g17);
 q=Fma(a4,q,g16);
 q=Fma(a3,q,g15);
 q=Fma(a2,q,g14);
 const auto hi=Bits(g13);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<1>(w7))));
 At<13-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<27,511>(k)),At<13-First>(out...));
 }
 if constexpr(First<=14 && 14<=Last) {
 V q=g26;
 q=Fma(a12,q,g25);
 q=Fma(a11,q,g24);
 q=Fma(a10,q,g23);
 q=Fma(a9,q,g22);
 q=Fma(a8,q,g21);
 q=Fma(a7,q,g20);
 q=Fma(a6,q,g19);
 q=Fma(a5,q,g18);
 q=Fma(a4,q,g17);
 q=Fma(a3,q,g16);
 q=Fma(a2,q,g15);
 const auto hi=Bits(g14);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<2>(w7))));
 At<14-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<29,511>(k)),At<14-First>(out...));
 }
 if constexpr(First<=15 && 15<=Last) {
 V q=g27;
 q=Fma(a12,q,g26);
 q=Fma(a11,q,g25);
 q=Fma(a10,q,g24);
 q=Fma(a9,q,g23);
 q=Fma(a8,q,g22);
 q=Fma(a7,q,g21);
 q=Fma(a6,q,g20);
 q=Fma(a5,q,g19);
 q=Fma(a4,q,g18);
 q=Fma(a3,q,g17);
 q=Fma(a2,q,g16);
 const auto hi=Bits(g15);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<3>(w7))));
 At<15-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<31,511>(k)),At<15-First>(out...));
 }
 if constexpr(First<=16 && 16<=Last) {
 V q=g28;
 q=Fma(a12,q,g27);
 q=Fma(a11,q,g26);
 q=Fma(a10,q,g25);
 q=Fma(a9,q,g24);
 q=Fma(a8,q,g23);
 q=Fma(a7,q,g22);
 q=Fma(a6,q,g21);
 q=Fma(a5,q,g20);
 q=Fma(a4,q,g19);
 q=Fma(a3,q,g18);
 q=Fma(a2,q,g17);
 const auto hi=Bits(g16);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<4>(w7))));
 At<16-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<33,511>(k)),At<16-First>(out...));
 }
 if constexpr(First<=17 && 17<=Last) {
 V q=g29;
 q=Fma(a12,q,g28);
 q=Fma(a11,q,g27);
 q=Fma(a10,q,g26);
 q=Fma(a9,q,g25);
 q=Fma(a8,q,g24);
 q=Fma(a7,q,g23);
 q=Fma(a6,q,g22);
 q=Fma(a5,q,g21);
 q=Fma(a4,q,g20);
 q=Fma(a3,q,g19);
 q=Fma(a2,q,g18);
 const auto hi=Bits(g17);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<5>(w7))));
 At<17-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<35,511>(k)),At<17-First>(out...));
 }
 if constexpr(First<=18 && 18<=Last) {
 V q=g30;
 q=Fma(a12,q,g29);
 q=Fma(a11,q,g28);
 q=Fma(a10,q,g27);
 q=Fma(a9,q,g26);
 q=Fma(a8,q,g25);
 q=Fma(a7,q,g24);
 q=Fma(a6,q,g23);
 q=Fma(a5,q,g22);
 q=Fma(a4,q,g21);
 q=Fma(a3,q,g20);
 q=Fma(a2,q,g19);
 const auto hi=Bits(g18);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<6>(w7))));
 At<18-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<37,511>(k)),At<18-First>(out...));
 }
 if constexpr(First<=19 && 19<=Last) {
 V q=g31;
 q=Fma(a12,q,g30);
 q=Fma(a11,q,g29);
 q=Fma(a10,q,g28);
 q=Fma(a9,q,g27);
 q=Fma(a8,q,g26);
 q=Fma(a7,q,g25);
 q=Fma(a6,q,g24);
 q=Fma(a5,q,g23);
 q=Fma(a4,q,g22);
 q=Fma(a3,q,g21);
 q=Fma(a2,q,g20);
 const auto hi=Bits(g19);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<7>(w7))));
 At<19-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<39,511>(k)),At<19-First>(out...));
 }
 if constexpr(First<=20 && 20<=Last) {
 V q=g32;
 q=Fma(a12,q,g31);
 q=Fma(a11,q,g30);
 q=Fma(a10,q,g29);
 q=Fma(a9,q,g28);
 q=Fma(a8,q,g27);
 q=Fma(a7,q,g26);
 q=Fma(a6,q,g25);
 q=Fma(a5,q,g24);
 q=Fma(a4,q,g23);
 q=Fma(a3,q,g22);
 q=Fma(a2,q,g21);
 const auto hi=Bits(g20);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<0>(w8))));
 At<20-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<41,511>(k)),At<20-First>(out...));
 }
 if constexpr(First<=21 && 21<=Last) {
 V q=g33;
 q=Fma(a12,q,g32);
 q=Fma(a11,q,g31);
 q=Fma(a10,q,g30);
 q=Fma(a9,q,g29);
 q=Fma(a8,q,g28);
 q=Fma(a7,q,g27);
 q=Fma(a6,q,g26);
 q=Fma(a5,q,g25);
 q=Fma(a4,q,g24);
 q=Fma(a3,q,g23);
 q=Fma(a2,q,g22);
 const auto hi=Bits(g21);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<1>(w8))));
 At<21-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<43,511>(k)),At<21-First>(out...));
 }
 if constexpr(First<=22 && 22<=Last) {
 V q=g34;
 q=Fma(a12,q,g33);
 q=Fma(a11,q,g32);
 q=Fma(a10,q,g31);
 q=Fma(a9,q,g30);
 q=Fma(a8,q,g29);
 q=Fma(a7,q,g28);
 q=Fma(a6,q,g27);
 q=Fma(a5,q,g26);
 q=Fma(a4,q,g25);
 q=Fma(a3,q,g24);
 q=Fma(a2,q,g23);
 const auto hi=Bits(g22);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<2>(w8))));
 At<22-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<45,511>(k)),At<22-First>(out...));
 }
 if constexpr(First<=23 && 23<=Last) {
 V q=g35;
 q=Fma(a12,q,g34);
 q=Fma(a11,q,g33);
 q=Fma(a10,q,g32);
 q=Fma(a9,q,g31);
 q=Fma(a8,q,g30);
 q=Fma(a7,q,g29);
 q=Fma(a6,q,g28);
 q=Fma(a5,q,g27);
 q=Fma(a4,q,g26);
 q=Fma(a3,q,g25);
 q=Fma(a2,q,g24);
 const auto hi=Bits(g23);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<3>(w8))));
 At<23-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<47,511>(k)),At<23-First>(out...));
 }
 if constexpr(First<=24 && 24<=Last) {
 V q=g36;
 q=Fma(a12,q,g35);
 q=Fma(a11,q,g34);
 q=Fma(a10,q,g33);
 q=Fma(a9,q,g32);
 q=Fma(a8,q,g31);
 q=Fma(a7,q,g30);
 q=Fma(a6,q,g29);
 q=Fma(a5,q,g28);
 q=Fma(a4,q,g27);
 q=Fma(a3,q,g26);
 q=Fma(a2,q,g25);
 const auto hi=Bits(g24);
 const auto v=RoundedAdd(Float(hn::Add(hi,SU(1))),FmaSub(h,q,Correction(hi,ByteAt<4>(w8))));
 At<24-First>(out...)=hn::IfThenElse(active,Scale(Bits(v),MultiplyConstant<49,511>(k)),At<24-First>(out...));
 }
 }
};
} } }
HWY_AFTER_NAMESPACE();
#endif
