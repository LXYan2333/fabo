#ifndef FAST_BOYS_ROUNDED_REFERENCE_V3_H
#define FAST_BOYS_ROUNDED_REFERENCE_V3_H
#include "../library_accuracy/accuracy_reference_v3.h"
#include <limits>
namespace {
// Same accelerated Horner forward-error construction as the RHF reference.
// Retain the enclosure, rather than only returning its rounded binary64 value.
struct FastReference {
  Table table;
  std::vector<Q> errors;
  explicit FastReference(const char* path, double expected_end=128):table(read_table(path)) {
    check(table.degree==12 && table.width==0x1p-4 && table.end==expected_end && table.precision==256,
          "unexpected reference table policy");
    const Q u=0x1p-113Q, tau=FLT128_DENORM_MIN, radius=Q(table.width)/2;
    const Q delta_error=up(up(u*radius)+tau), distance=up(radius+delta_error);
    const Q operations=2*table.degree, gamma=up(up(operations*u)/down(1-operations*u));
    errors.resize(table.cells*(table.order+1));
    for (std::size_t cell=0; cell<table.cells; ++cell) for (unsigned n=0;n<=table.order;++n) {
      const auto* c=table.coefficients.data()+cell*table.stride()+n*(table.degree+2);
      Q magnitude=fabsq(c[table.degree].lo), coefficient_error=up(c[table.degree].hi-c[table.degree].lo), derivative=0;
      for (unsigned j=table.degree;j>0;--j) {
        derivative=up(up(derivative*distance)+magnitude);
        magnitude=up(up(magnitude*distance)+fabsq(c[j-1].lo));
        coefficient_error=up(up(coefficient_error*radius)+up(c[j-1].hi-c[j-1].lo));
      }
      Q power=1; for(unsigned j=0;j<=table.degree;++j) power=up(power*radius);
      Q error=up(up(gamma*magnitude)+coefficient_error);
      error=up(error+up(derivative*delta_error));
      error=up(error+up(power*c[table.degree+1].hi));
      errors[cell*(table.order+1)+n]=up(error+up(up(operations*tau)/down(1-operations*u)));
    }
  }
  Interval value(double x, unsigned n) const {
    check(std::isfinite(x) && x>=0 && x<=table.end && n<=table.order,"reference outside table domain");
    const auto cell=std::min<std::uint64_t>(std::uint64_t(x/table.width),table.cells-1);
    const Q d=Q(x)-Q((cell+.5)*table.width);
    const auto* c=table.coefficients.data()+cell*table.stride()+n*(table.degree+2);
    Q v=c[table.degree].lo;
    for(unsigned j=table.degree;j>0;--j) v=v*d+c[j-1].lo;
    const Q e=errors[cell*(table.order+1)+n];
    return {down(v-e),up(v+e)};
  }
};

struct Reference { Interval bounds; hp::Split split; double rounded, ulp; };
std::uint64_t rounding_fallbacks=0, gate_fallbacks=0;
Reference reference(const FastReference& table, double x, unsigned n, bool exponential=false) {
  auto r=table.value(x,n);
  if(x==0) r=exponential ? Interval{Q(1),Q(1)} : Interval{down(Q(1)/Q(2*n+1)),up(Q(1)/Q(2*n+1))};
  double rounded=double(r.lo);
  if(!same(double(r.lo),double(r.hi))) {
    ++rounding_fallbacks;
    for(unsigned p=256;;p*=2) {
      check(p<=4096,"unresolved reference rounding");
      Bounds value(p);
      if(exponential) {
        MP arg(p);mpfr_set_d(arg.x,-x,MPFR_RNDN);
        mpfr_exp(value.lo.x,arg.x,MPFR_RNDD);mpfr_exp(value.hi.x,arg.x,MPFR_RNDU);
      } else value=prefix(n,x,p)[n];
      rounded=mpfr_get_d(value.lo.x,MPFR_RNDN);
      if(same(rounded,mpfr_get_d(value.hi.x,MPFR_RNDN))) {
        r={mpfr_get_float128(value.lo.x,MPFR_RNDD),mpfr_get_float128(value.hi.x,MPFR_RNDU)};break;
      }
    }
  }
  check((rounded>0 || (exponential && rounded==0)) && std::isfinite(rounded),"reference must be positive normal");
  const Q middle=(r.lo+r.hi)/2;
  const double residual=double(middle-Q(rounded));
  const Q reconstructed=Q(rounded)+Q(residual);
  hp::Split s{rounded,residual,std::nextafter(double(std::max(fabsq(r.lo-reconstructed),fabsq(r.hi-reconstructed))),INFINITY)};
  return {r,s,rounded,std::nextafter(rounded,INFINITY)-rounded};
}

}
#endif
