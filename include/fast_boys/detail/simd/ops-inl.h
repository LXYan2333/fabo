// Per-target helpers. Include through fast_boys/simd.h.
#if defined(FAST_BOYS_SIMD_OPS_INL_H_) == defined(HWY_TARGET_TOGGLE)
#ifdef FAST_BOYS_SIMD_OPS_INL_H_
#undef FAST_BOYS_SIMD_OPS_INL_H_
#else
#define FAST_BOYS_SIMD_OPS_INL_H_
#endif

#include "fast_boys/simd_config.h"
#include "hwy/highway.h"

#include "fast_boys/table.h"
#include <cmath>
#include <type_traits>

HWY_BEFORE_NAMESPACE();
namespace fast_boys {
namespace simd {
namespace HWY_NAMESPACE {
namespace hn = hwy::HWY_NAMESPACE;
using D = hn::ScalableTag<double>;
using DU = hn::RebindToUnsigned<D>;
using DI = hn::RebindToSigned<D>;
using V = hn::VFromD<D>;
using U = hn::VFromD<DU>;
using I = hn::VFromD<DI>;
using Mask = hn::Mask<D>;
// Conservative default by ISA, not a runtime CPU vulnerability detector.
inline constexpr bool kDefaultUseSoftwareGather = HWY_TARGET == HWY_AVX2 ||
                                                  HWY_TARGET == HWY_AVX3 ||
                                                  HWY_TARGET == HWY_AVX3_DL;

namespace detail {
HWY_INLINE auto S(double x) { return hn::Set(D(), x); }
HWY_INLINE auto SU(std::uint64_t x) { return hn::Set(DU(), x); }
constexpr int Log2(std::uint64_t n) { return n <= 1 ? 0 : 1 + Log2(n >> 1); }
template <std::uint64_t Factor, std::uint64_t Maximum>
HWY_INLINE U MultiplyConstant(U value) {
  static_assert(Factor > 0, "stride must be positive");
  static_assert(Maximum <= UINT64_MAX / Factor, "index product overflows");
  if constexpr (Factor == 1)
    return value;
  else if constexpr ((Factor & (Factor - 1)) == 0)
    return hn::ShiftLeft<Log2(Factor)>(value);
#if HWY_TARGET != HWY_SCALAR && HWY_IS_LITTLE_ENDIAN
  else if constexpr (Factor <= UINT32_MAX && Maximum <= UINT32_MAX) {
    const hn::Repartition<std::uint32_t, DU> d32;
    return hn::MulEven(hn::BitCast(d32, value),
                       hn::Set(d32, std::uint32_t(Factor)));
  }
#endif
  else
    return hn::Mul(value, SU(Factor));
}
HWY_INLINE auto Bits(V x) { return hn::BitCast(DU(), x); }
HWY_INLINE auto Float(U x) { return hn::BitCast(D(), x); }

// Numerical fence only: no dependencies between unrelated loads/arithmetic.
HWY_INLINE V ArithmeticFence(V x) {
#if defined(__has_builtin)
#if !HWY_HAVE_SCALABLE && !(HWY_TARGET & HWY_ALL_SVE) &&                       \
    HWY_TARGET != HWY_RVV && HWY_TARGET != HWY_EMU128 &&                       \
    HWY_TARGET != HWY_SCALAR
#if __has_builtin(__builtin_assoc_barrier) &&                                  \
    !(HWY_COMPILER_GCC_ACTUAL && HWY_TARGET_IS_NEON)
  x.raw = __builtin_assoc_barrier(x.raw);
  return x;
#elif __has_builtin(__arithmetic_fence) &&                                     \
    (HWY_ARCH_X86 || (HWY_ARCH_ARM_A64 && HWY_COMPILER_CLANG >= 1700))
  x.raw = __arithmetic_fence(x.raw);
  return x;
#endif
#endif
#endif
#if HWY_COMPILER_GCC && HWY_ARCH_X86 && HWY_TARGET != HWY_SCALAR &&            \
    HWY_TARGET != HWY_EMU128
  __asm__("" : "+x"(x.raw));
  return x;
#elif HWY_COMPILER_GCC && (HWY_TARGET & HWY_ALL_SVE)
  __asm__("" : "+w"(x));
  return x;
#elif HWY_COMPILER_GCC && HWY_TARGET == HWY_RVV
  __asm__("" : "+vr"(x));
  return x;
#elif HWY_COMPILER_GCC && HWY_ARCH_ARM_A64 && HWY_TARGET_IS_NEON
  __asm__("" : "+w"(x.raw));
  return x;
#else
  HWY_ALIGN_MAX double lanes[hn::MaxLanes(D())];
  hn::Store(x, D(), lanes);
  for (std::size_t i = 0; i < hn::Lanes(D()); ++i) {
    volatile double rounded = lanes[i];
    lanes[i] = rounded;
  }
  return hn::Load(D(), lanes);
#endif
}
HWY_INLINE V Fma(V a, V b, V c) {
#if HWY_NATIVE_FMA
  return hn::MulAdd(a, b, c);
#else
  // Portability/testing convenience, not a performance-tuned implementation.
  // Patches require fused rounding even when this ISA has no native FMA.
  HWY_ALIGN_MAX double aa[hn::MaxLanes(D())], bb[hn::MaxLanes(D())],
      cc[hn::MaxLanes(D())];
  hn::Store(a, D(), aa);
  hn::Store(b, D(), bb);
  hn::Store(c, D(), cc);
  for (std::size_t i = 0; i < hn::Lanes(D()); ++i)
    cc[i] = std::fma(aa[i], bb[i], cc[i]);
  return hn::Load(D(), cc);
#endif
}

HWY_INLINE V FmaSub(V a, V b, V c) {
#if HWY_NATIVE_FMA
  return hn::MulSub(a, b, c);
#else
  // Highway's non-FMA MulSub is not fused; retain the std::fma fallback.
  return Fma(a, b, hn::Neg(c));
#endif
}

// Reference packs only: never create a container of (possibly sizeless) V.
template <int N, class Head, class... Rest>
HWY_INLINE decltype(auto) At(Head &head, Rest &...rest) {
  if constexpr (N == 0)
    return (head);
  else
    return At<N - 1>(rest...);
}

#if HWY_ARCH_X86_64 && (HWY_TARGET == HWY_AVX2 || HWY_TARGET <= HWY_AVX3)
template <int Block, class Packed>
HWY_INLINE std::uint64_t IndexBlock(Packed packed) {
  std::uint64_t bits;
  if constexpr (sizeof(Packed) == 16)
    bits = static_cast<std::uint64_t>(_mm_extract_epi64(packed, Block));
  else
    bits = static_cast<std::uint64_t>(_mm256_extract_epi64(packed, Block));
#if HWY_COMPILER_GCC
  // Prevent re-extracting individual narrow indices from SIMD registers.
  __asm__("" : "+r"(bits));
#endif
  return bits;
}
template <int Lane, int Width, class Packed>
HWY_INLINE std::uint64_t PackedIndex(Packed packed) {
  return (IndexBlock<Lane / (64 / Width)>(packed) >>
          ((Lane % (64 / Width)) * Width)) &
         ((1ULL << Width) - 1);
}
template <int Pair, int Width, class Packed>
HWY_INLINE __m128i LoadPair(const std::uint64_t *table, Packed packed) {
  // Direct compiler-intrinsic loads intentionally use double pointers to
  // uint64_t storage; this is not a portable C++ aliasing guarantee. Each
  // intrinsic reads exactly eight bytes, without neighboring-word padding.
  const auto low = _mm_load_sd(reinterpret_cast<const double *>(
      table + PackedIndex<2 * Pair, Width>(packed)));
  return _mm_castpd_si128(
      _mm_loadh_pd(low, reinterpret_cast<const double *>(
                            table + PackedIndex<2 * Pair + 1, Width>(packed))));
}
template <int Width, class Packed>
HWY_INLINE U PairGather(const std::uint64_t *table, Packed packed) {
  const auto p0 = LoadPair<0, Width>(table, packed),
             p1 = LoadPair<1, Width>(table, packed);
  const auto lo = _mm256_inserti128_si256(_mm256_castsi128_si256(p0), p1, 1);
#if HWY_TARGET == HWY_AVX2
  return U{lo};
#else
  const auto p2 = LoadPair<2, Width>(table, packed),
             p3 = LoadPair<3, Width>(table, packed);
  const auto hi = _mm256_inserti128_si256(_mm256_castsi128_si256(p2), p3, 1);
  return U{_mm512_inserti64x4(_mm512_castsi256_si512(lo), hi, 1)};
#endif
}
template <int Pair>
HWY_INLINE __m128i WideLoadPair(const std::uint64_t *table, U index) {
  const auto low = _mm_load_sd(reinterpret_cast<const double *>(
      table + hn::ExtractLane(index, 2 * Pair)));
  return _mm_castpd_si128(
      _mm_loadh_pd(low, reinterpret_cast<const double *>(
                            table + hn::ExtractLane(index, 2 * Pair + 1))));
}
#endif

HWY_INLINE U NativeGather(const std::uint64_t *table, U index) {
#if HWY_COMPILER_GCC_ACTUAL && HWY_ARCH_X86 && HWY_TARGET <= HWY_AVX2 &&       \
    !defined(HWY_DISABLE_GCC_GATHER_WORKAROUND)
  // Highway PR #3519 / GCC PR #127946: hiding the all-active mask keeps
  // the zero merge source, breaking the gather destination's false dependency.
  // No volatile or memory clobber: the intrinsic describes the memory read.
  // Keep this here for callers using Highway versions without the workaround.
  // https://github.com/google/highway/pull/3519
#if HWY_TARGET == HWY_AVX2
  // Highway's AVX2 uint64 gather uses the double intrinsic. Hide its native
  // mask type to avoid a redundant mask copy (GCC PR #128233).
  auto native_mask = hn::SetMask(D(), true);
  __asm__("" : "+x"(native_mask.raw));
  const auto mask = hn::RebindMask(DU(), native_mask);
#else
  auto mask = hn::SetMask(DU(), true);
  __asm__("" : "+k"(mask.raw));
#endif
  return hn::MaskedGatherIndexOr(hn::Zero(DU()), mask, DU(), table,
                                hn::BitCast(DI(), index));
#else
  return hn::GatherIndex(DU(), table, hn::BitCast(DI(), index));
#endif
}

template <bool Software, std::uint64_t MaxIndex>
HWY_INLINE U Gather(const std::uint64_t *table, U index) {
  static_assert(MaxIndex <= INT64_MAX, "gather index exceeds signed range");
#if HWY_ARCH_X86_64 && (HWY_TARGET == HWY_AVX2 || HWY_TARGET <= HWY_AVX3)
  if constexpr (Software) {
#if HWY_TARGET == HWY_AVX2
    if constexpr (MaxIndex < 256)
      return PairGather<8>(
          table, hn::TruncateTo(hn::FixedTag<std::uint8_t, 4>(), index).raw);
    else if constexpr (MaxIndex < 65536)
      return PairGather<16>(
          table, hn::TruncateTo(hn::FixedTag<std::uint16_t, 4>(), index).raw);
    else if constexpr (MaxIndex <= 0xffffffffULL)
      return PairGather<32>(
          table, hn::TruncateTo(hn::FixedTag<std::uint32_t, 4>(), index).raw);
    else
#else
    if constexpr (MaxIndex < 256)
      return PairGather<8>(table, _mm512_cvtepi64_epi8(index.raw));
    else if constexpr (MaxIndex < 65536)
      return PairGather<16>(table, _mm512_cvtepi64_epi16(index.raw));
    else if constexpr (MaxIndex <= 0xffffffffULL)
      return PairGather<32>(table, _mm512_cvtepi64_epi32(index.raw));
    else
#endif
    {
      const auto p0 = WideLoadPair<0>(table, index),
                 p1 = WideLoadPair<1>(table, index);
      const auto lo =
          _mm256_inserti128_si256(_mm256_castsi128_si256(p0), p1, 1);
#if HWY_TARGET == HWY_AVX2
      return U{lo};
#else
      const auto p2 = WideLoadPair<2>(table, index),
                 p3 = WideLoadPair<3>(table, index);
      const auto hi =
          _mm256_inserti128_si256(_mm256_castsi128_si256(p2), p3, 1);
      return U{_mm512_inserti64x4(_mm512_castsi256_si512(lo), hi, 1)};
#endif
    }
  } else
#endif
  {
    return NativeGather(table, index);
  }
}

HWY_INLINE V Scale(U bits, U scale) {
  const auto result_biased_exponent = hn::ShiftRight<52>(bits);
  const auto normal = hn::Lt(scale, result_biased_exponent);
  if (HWY_LIKELY(hn::AllTrue(DU(), normal)))
    return Float(hn::Sub(bits, hn::ShiftLeft<52>(scale)));
  // Cold mixed/underflow path: delegate rounding and zero handling to Highway.
  // The nonnegative scale fits int64_t; reinterpretation is exact here.
  return hn::MulByPow2(Float(bits), hn::Neg(hn::BitCast(DI(), scale)));
}

HWY_INLINE V RoundedAdd(V a, V b) {
  return detail::ArithmeticFence(hn::Add(a, b));
}
HWY_INLINE V RoundedSub(V a, V b) {
  return detail::ArithmeticFence(hn::Sub(a, b));
}
HWY_INLINE V RoundedMul(V a, V b) {
  return detail::ArithmeticFence(hn::Mul(a, b));
}
// Vector-length agnostic: no aggregate or array of potentially sizeless vectors.
template<class M>
HWY_INLINE void PrepareCombinedCoordinates(const V x,U& row,V& h,U& k) {
  const auto in_main=hn::Le(x,S(M::domain_end));
  const auto main_mask=hn::RebindMask(DU(),in_main);
  const auto main_x=hn::IfThenElseZero(in_main,x);
  const auto y=RoundedAdd(main_x,S(M::offset));
  const auto exponent_bias=SU(1023ULL<<52);
  const auto unbiased_bits=hn::Sub(Bits(x),exponent_bias);
  // Unsigned normalization is harmless in unused main lanes. Addition,
  // rather than OR, restores exponent 1023 or 1024 including the carry.
  k=hn::IfThenZeroElse(main_mask,hn::ShiftRight<53>(unbiased_bits));
  const auto u=Float(hn::Add(hn::And(unbiased_bits,SU((1ULL<<53)-1)),exponent_bias));
  const auto coordinate=hn::IfThenElse(in_main,y,u);
  const auto argument=hn::IfThenElse(in_main,x,coordinate);
  const auto reference_offset=hn::IfThenElseZero(in_main,S(M::offset));
  const auto key_origin=hn::IfThenElse(main_mask,SU(M::key_min),
      SU((1023ULL<<M::tail_retained_bits)-M::tail_row_offset));
  U key FAST_BOYS_INDETERMINATE;
  U reference_bits FAST_BOYS_INDETERMINATE;
  if constexpr(M::discarded_bits==M::tail_discarded_bits) {
    key=hn::ShiftRight<M::discarded_bits>(hn::Add(Bits(coordinate),SU(1ULL<<(M::discarded_bits-1))));
    reference_bits=hn::ShiftLeft<M::discarded_bits>(key);
  } else {
    // Keep immediate shifts on targets without efficient per-lane shifts.
    const auto main_key=hn::ShiftRight<M::discarded_bits>(hn::Add(Bits(coordinate),SU(1ULL<<(M::discarded_bits-1))));
    const auto tail_key=hn::ShiftRight<M::tail_discarded_bits>(hn::Add(Bits(coordinate),SU(1ULL<<(M::tail_discarded_bits-1))));
    key=hn::IfThenElse(main_mask,main_key,tail_key);
    reference_bits=hn::IfThenElse(main_mask,hn::ShiftLeft<M::discarded_bits>(main_key),hn::ShiftLeft<M::tail_discarded_bits>(tail_key));
  }
  const auto reference=RoundedSub(Float(reference_bits),reference_offset);
  h=RoundedSub(reference,argument);
  const auto logical_row=hn::Sub(key,key_origin);
  row=MultiplyConstant<M::row_words,M::row_count+M::tail_row_count-1>(logical_row);
}
HWY_INLINE V Correction(U hi, U code) {
  return Float(
      hn::Add(hn::Sub(hn::And(hi, SU(0x7ff0000000000000ULL)), SU(53ULL << 52)),
              hn::ShiftLeft<45>(code)));
}
template <int Byte> HWY_INLINE V CorrectionFromWord(U hi, U word) {
  static_assert(0 <= Byte && Byte < 8, "byte index must be inside a u64 lane");
  constexpr int shift = 45 - 8 * Byte;
  U positioned;
  if constexpr (shift >= 0)
    positioned = hn::ShiftLeft<shift>(word);
  else
    positioned = hn::ShiftRight<-shift>(word);
  positioned = hn::And(positioned, SU(255ULL << 45));
  // Bit 52 contributes to the exponent: preserve the integer addition.
  return Float(
      hn::Add(hn::Sub(hn::And(hi, SU(0x7ff0000000000000ULL)), SU(53ULL << 52)),
              positioned));
}
template <int Byte> HWY_INLINE U ByteAt(U word) {
  static_assert(0 <= Byte && Byte < 8, "byte index must be inside a u64 lane");
  if constexpr (Byte == 0)
    return hn::And(word, SU(255));
#if HWY_ARCH_X86 && HWY_TARGET != HWY_SCALAR && HWY_TARGET != HWY_EMU128
  // x86 byte shifts use the shuffle execution resources rather than the
  // lane-shift resources that can contend with FMA. The shift operates within
  // 128-bit blocks, but each u64 lane's low byte still comes from that same
  // lane for Byte < 8. Mask away all other bytes, including cross-lane data.
  auto shifted = hn::ShiftRightBytes<Byte>(DU(), word);
#if HWY_COMPILER_GCC
  // Clang's demanded-bits optimization otherwise replaces the byte shuffle
  // with word/dword lane shifts once it sees the mask. Keep the whole shifted
  // vector observable to the compiler. No instruction, memory clobber, or
  // dependency on unrelated arithmetic; +v also permits upper EVEX registers.
  __asm__("" : "+v"(shifted.raw));
#endif
  return hn::And(shifted, SU(255));
#else
  // Other architectures retain lane shifts until separately investigated.
  return hn::And(hn::ShiftRight<Byte * 8>(word), SU(255));
#endif
}
} // namespace detail
template <class Model> struct Kernel;
template <class Tail> struct TailKernel;
} // namespace HWY_NAMESPACE
} // namespace simd
} // namespace fast_boys
HWY_AFTER_NAMESPACE();
#endif
