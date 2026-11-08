#ifndef FAST_BOYS_ACCURACY_REFERENCE_V3_H
#define FAST_BOYS_ACCURACY_REFERENCE_V3_H
// Shared scientific reference. DUT arithmetic remains strict binary64.
#define main fb3_reference_unused_main
#include "taylor_boys_reference_v2.cc"
#undef main
#include <iomanip>
#include <sstream>
#ifdef __FAST_MATH__
#error The scientific reference must not use fast math
#endif

namespace { namespace hp {
constexpr const char* contract = "binary128-interval-error-v1";
struct Split { double hi, lo, radius; };
inline Interval mp_reference(unsigned order, double x, unsigned precision=256, bool exponential=false) {
  if (exponential || order==0) {
    MP arg(precision), a(precision), b(precision), pi(precision), root(precision);
    mpfr_set_d(arg.x, x, MPFR_RNDN);
    if (exponential) {
      mpfr_neg(arg.x,arg.x,MPFR_RNDN);
      mpfr_exp(a.x,arg.x,MPFR_RNDD); mpfr_exp(b.x,arg.x,MPFR_RNDU);
      return {mpfr_get_float128(a.x,MPFR_RNDD),mpfr_get_float128(b.x,MPFR_RNDU)};
    }
    // The positive series below is efficient in the search domain. Public F0
    // checks also include very large x; erf(sqrt(x)) differs from 1 by less
    // than exp(-x)/sqrt(pi*x). For x>10000 that tail is below this enclosure.
    if (x>10000) {
      mpfr_const_pi(pi.x,MPFR_RNDD); mpfr_div(pi.x,pi.x,arg.x,MPFR_RNDD);
      mpfr_sqrt(a.x,pi.x,MPFR_RNDD); mpfr_div_2ui(a.x,a.x,1,MPFR_RNDD);
      mpfr_const_pi(pi.x,MPFR_RNDU); mpfr_div(pi.x,pi.x,arg.x,MPFR_RNDU);
      mpfr_sqrt(b.x,pi.x,MPFR_RNDU); mpfr_div_2ui(b.x,b.x,1,MPFR_RNDU);
      check(precision<=4096,"large-x F0 reference precision exceeds tail enclosure");
      mpfr_nextbelow(a.x);
      return {mpfr_get_float128(a.x,MPFR_RNDD),mpfr_get_float128(b.x,MPFR_RNDU)};
    }
  }
  const auto v=prefix(order,x,precision);
  return {mpfr_get_float128(v[order].lo.x,MPFR_RNDD),mpfr_get_float128(v[order].hi.x,MPFR_RNDU)};
}
inline void reference(const Table& t, double x, unsigned order, Interval* out) {
  check(std::isfinite(x)&&x>=0&&x<=t.end&&order<=t.order,"reference outside table");
  if(x==0) {
    for(unsigned n=0;n<=order;++n) out[n]={down(Q(1)/Q(2*n+1)),up(Q(1)/Q(2*n+1))};
    return;
  }
  const auto cell=std::min<std::uint64_t>(std::uint64_t(x/t.width),t.cells-1);
  const Q diff=Q(x)-Q((cell+.5)*t.width);
  const Interval delta{down(diff),up(diff)};
  Q power=1,distance=std::max(fabsq(delta.lo),fabsq(delta.hi));
  for(unsigned j=0;j<=t.degree;++j) power=up(power*distance);
  for(unsigned n=0;n<=order;++n) {
    const auto* c=t.coefficients.data()+cell*t.stride()+n*(t.degree+2);
    auto v=c[t.degree];
    for(unsigned j=t.degree;j>0;--j) v=add(mul(v,delta),c[j-1]);
    const Q remainder=up(power*c[t.degree+1].hi);
    out[n]={down(v.lo-remainder),up(v.hi+remainder)};
  }
}
inline Split split(Interval r) {
  const Q middle=(r.lo+r.hi)/2;
  const double hi=static_cast<double>(middle),lo=static_cast<double>(middle-Q(hi));
  const Q reconstructed=Q(hi)+Q(lo);
  return {hi,lo,std::nextafter(static_cast<double>(std::max(fabsq(r.lo-reconstructed),fabsq(r.hi-reconstructed))),INFINITY)};
}
inline Interval error(double a,Interval r) {
  if(!std::isfinite(a)) return {HUGE_VALQ,HUGE_VALQ};
  const Q lo=down(Q(a)-r.hi),hi=up(Q(a)-r.lo);
  return {lo<=0&&hi>=0?Q(0):std::min(fabsq(lo),fabsq(hi)),std::max(fabsq(lo),fabsq(hi))};
}
struct Limit {
  Interval value; double lo,hi;
  explicit Limit(const char* decimal) {
    MP l(256),h(256);
    check(mpfr_set_str(l.x,decimal,10,MPFR_RNDD)==0&&mpfr_set_str(h.x,decimal,10,MPFR_RNDU)==0,"invalid decimal accuracy limit");
    check(mpfr_number_p(l.x)&&mpfr_sgn(l.x)>0,"invalid accuracy limit");
    value={mpfr_get_float128(l.x,MPFR_RNDD),mpfr_get_float128(h.x,MPFR_RNDU)};
    lo=mpfr_get_d(l.x,MPFR_RNDD);hi=mpfr_get_d(h.x,MPFR_RNDU);
  }
};
struct Comparison {double estimate; bool failed; unsigned refinements;};
inline Comparison compare(double a,Interval r,Split s,const Limit& limit,double x,unsigned order,bool exponential=false,bool filtered=true) {
  if(!std::isfinite(a)) return {INFINITY,true,0};
  if(filtered&&a>=s.hi*.5&&a*.5<=s.hi) {
    const double estimate=std::abs((a-s.hi)-s.lo);
    const double guard=s.radius+estimate*(4*std::numeric_limits<double>::epsilon())+4*std::numeric_limits<double>::denorm_min();
    if(estimate+guard<limit.lo) return {estimate,false,0};
    if(estimate-guard>limit.hi) return {estimate,true,0};
  }
  for(unsigned precision=0;precision<=1024;precision=precision?precision*2:256) {
    if(precision) r=mp_reference(order,x,precision,exponential);
    const auto e=error(a,r); const double estimate=static_cast<double>((e.lo+e.hi)/2);
    if(e.hi<=limit.value.lo) return {estimate,false,precision?1u:0u};
    if(e.lo>limit.value.hi) return {estimate,true,precision?1u:0u};
  }
  throw std::runtime_error("unresolved high-precision accuracy comparison after 1024-bit refinement");
}
inline std::string decimal(Q x) {char b[128];quadmath_snprintf(b,sizeof(b),"%.36Qg",x);return b;}
}
} // namespace
#endif
