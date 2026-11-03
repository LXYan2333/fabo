// Untimed correctly-rounded Boys oracle. Caller MXCSR is restored exactly.
#include <mpfr.h>
#include <immintrin.h>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <array>
#include <fstream>

namespace {
std::uint64_t bits(double value) {
  std::uint64_t result;std::memcpy(&result,&value,sizeof result);return result;
}
struct ArithmeticEnvironment {
  unsigned saved=_mm_getcsr();
  ArithmeticEnvironment() { _mm_setcsr(saved & ~(0x8040u|0x6000u)); }
  ~ArithmeticEnvironment() { _mm_setcsr(saved); }
};
struct Real {
  mpfr_t v;
  Real() { mpfr_init2(v,113); }
  ~Real() { mpfr_clear(v); }
  operator mpfr_ptr() { return v; }
  operator mpfr_srcptr() const { return v; }
};
[[noreturn]] void fail() { std::fputs("Boys reference failed to certify rounding\n",stderr); std::abort(); }
struct Oracle {
  std::array<Real,513*37+26> table;
  Real x,d,h,t,a,b,r,lo,hi,term,sum,ratio,rem,ex;
  Oracle() {
    const char* path=std::getenv("FABO_REFERENCE_TABLE");
    if (!path) fail();
    std::ifstream f(path,std::ios::binary);
    for(auto& value:table) {
      unsigned char raw[16]; if(!f.read(reinterpret_cast<char*>(raw),16)) fail();
      const unsigned exponent=((unsigned(raw[15])<<8)|raw[14])&32767;
      if(raw[15]&128 || !exponent || exponent==32767) {
        bool zero=true; for(auto c:raw) zero &= c==0;
        if(!zero) fail(); mpfr_set_zero(value,1); continue;
      }
      mpfr_set_ui(value,1,MPFR_RNDN);
      for(int i=13;i>=0;--i) { mpfr_mul_2ui(value,value,8,MPFR_RNDN); mpfr_add_ui(value,value,raw[i],MPFR_RNDN); }
      mpfr_mul_2si(value,value,int(exponent)-16383-112,MPFR_RNDN);
    }
    char extra;if(f.read(&extra,1)) fail();
  }
  bool rounded(double& result) {
    mpfr_sub(lo,h,r,MPFR_RNDD); if(mpfr_sgn(lo.v)<0) mpfr_set_zero(lo,1);
    mpfr_add(hi,h,r,MPFR_RNDU);
    double lower=mpfr_get_d(lo,MPFR_RNDN),upper=mpfr_get_d(hi,MPFR_RNDN);
    if(bits(lower)!=bits(upper))return false;
    result=lower;return true;
  }
  double get(int n,double input) {
    if(n<0||n>8||std::isnan(input)||input<0)fail();
    if(std::isinf(input))return 0;
    // Same conservative Taylor/large-x bounds as QUICK_REFERENCE.md.
    for(Real* p:{&x,&d,&h,&t,&a,&b,&r,&lo,&hi,&term,&sum,&ratio,&rem,&ex})mpfr_set_prec(*p,113);
    mpfr_set_d(x,input,MPFR_RNDN);
    if(input<=128) {
      int row=int(input*4+0.5);
      mpfr_set_ui(d,row,MPFR_RNDN);mpfr_div_2ui(d,d,2,MPFR_RNDN);mpfr_sub(d,x,d,MPFR_RNDN);
      mpfr_set(h,table[row*37+n+24],MPFR_RNDN);
      for(int k=23;k>=0;--k) {
        mpfr_mul(t,d,table[513*37+k+1],MPFR_RNDN);mpfr_neg(t,t,MPFR_RNDN);
        mpfr_fma(h,t,h,table[row*37+n+k],MPFR_RNDN);
      }
      mpfr_mul_2si(r,table[row*37+n],-88,MPFR_RNDU);
    } else {
      mpfr_sqrt(t,x,MPFR_RNDN);mpfr_div(h,table.back(),t,MPFR_RNDN);
      mpfr_ui_div(a,1,x,MPFR_RNDN);mpfr_div_2ui(a,a,1,MPFR_RNDN);
      for(int l=1;l<=n;++l){mpfr_mul_ui(t,a,2*l-1,MPFR_RNDN);mpfr_mul(h,h,t,MPFR_RNDN);}
      int exponent=input<8192?int(input*23/16):8192;
      mpfr_set_ui_2exp(t,1,-exponent,MPFR_RNDU);
      mpfr_mul_2si(r,h,-88,MPFR_RNDU);mpfr_add(r,r,t,MPFR_RNDU);
    }
    double result;if(!std::getenv("FABO_REFERENCE_FORCE_FALLBACK")&&rounded(result))return result;
    // Positive series with directed rounding, geometrically bounded tail.
    // Large inputs use a complete-integral enclosure and bounded omitted tail.
    for(int precision=256;precision<=8192;precision*=2) {
      for(Real* p:{&x,&d,&h,&t,&a,&b,&r,&lo,&hi,&term,&sum,&ratio,&rem,&ex})mpfr_set_prec(*p,precision);
      mpfr_set_d(x,input,MPFR_RNDN);
      for(int side=0;side<2;++side) {
        auto rnd=side?MPFR_RNDU:MPFR_RNDD;
        if(input>=precision+2048) {
          mpfr_const_pi(a,rnd);mpfr_sqrt(a,a,rnd);
          mpfr_sqrt(b,x,side?MPFR_RNDD:MPFR_RNDU);mpfr_mul_2ui(b,b,1,side?MPFR_RNDD:MPFR_RNDU);
          mpfr_div(sum,a,b,rnd);
          for(int l=1;l<=n;++l){mpfr_mul_ui(sum,sum,2*l-1,rnd);mpfr_div(sum,sum,x,rnd);mpfr_div_2ui(sum,sum,1,rnd);}
          if(!side){mpfr_set_ui_2exp(t,1,-precision-2048,MPFR_RNDU);mpfr_sub(sum,sum,t,rnd);if(mpfr_sgn(sum.v)<0)mpfr_set_zero(sum,1);}
        } else {
          mpfr_set_ui(term,1,rnd);mpfr_div_ui(term,term,2*n+1,rnd);mpfr_set(sum,term,rnd);
          bool done=false;
          for(int k=1;k<32768;++k){
            mpfr_mul(term,term,x,rnd);mpfr_mul_2ui(term,term,1,rnd);mpfr_div_ui(term,term,2*n+2*k+1,rnd);mpfr_add(sum,sum,term,rnd);
            mpfr_mul_2ui(ratio,x,1,MPFR_RNDU);mpfr_div_ui(ratio,ratio,2*n+2*k+3,MPFR_RNDU);
            if(mpfr_cmp_ui(ratio,1)<0){
              mpfr_ui_sub(b,1,ratio,MPFR_RNDD);mpfr_mul(rem,term,ratio,MPFR_RNDU);mpfr_div(rem,rem,b,MPFR_RNDU);
              mpfr_mul_2si(t,sum,-precision+16,MPFR_RNDD);
              if(mpfr_cmp(rem,t)<=0){if(side)mpfr_add(sum,sum,rem,rnd);done=true;break;}
            }
          }
          if(!done)fail();
          mpfr_neg(ex,x,MPFR_RNDN);mpfr_exp(ex,ex,rnd);mpfr_mul(sum,sum,ex,rnd);
        }
        mpfr_set(side?hi.v:lo.v,sum,rnd);
      }
      double lower=mpfr_get_d(lo,MPFR_RNDN),upper=mpfr_get_d(hi,MPFR_RNDN);
      if(bits(lower)==bits(upper))return lower;
    }
    fail();
  }
};
}
extern "C" void fabo_reference_boys(int n,int lanes,const double* x,double* out) {
  // Fast-math callers can enable DAZ/FTZ. MPFR conversion and cell indexing
  // must see gradual underflow/RN; no state change escapes this untimed call.
  ArithmeticEnvironment environment;
  static Oracle oracle;
  if(lanes<1||lanes>8)fail();
  for(int l=0;l<=n;++l)for(int i=0;i<8;++i)out[l*8+i]=i<lanes?oracle.get(l,x[i]):0.0;
}
