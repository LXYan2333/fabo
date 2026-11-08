// Untimed strict binary64 recurrence probe; references use enclosing binary128.
#include "rounded_reference_v3.h"
#include <array>
#include <limits>

namespace {
constexpr unsigned orders = 13, gates = 5;
constexpr std::uint64_t denominator = 1000000, final_index = 1000000000;
constexpr const char* protocol = "upward-window-v1";

void generate_exp(Table& t, unsigned workers) {
  t.order = 0; t.cells = std::uint64_t(t.end/t.width);
  t.coefficients.resize(t.cells*t.stride());
  parallel(t.cells, workers, [&](std::size_t cell) {
    MP x(t.precision), lo(t.precision), hi(t.precision), left(t.precision), factorial(t.precision), a(t.precision), b(t.precision);
    mpfr_set_d(x.x, -(cell+.5)*t.width, MPFR_RNDN);
    mpfr_exp(lo.x, x.x, MPFR_RNDD); mpfr_exp(hi.x, x.x, MPFR_RNDU);
    mpfr_set_d(x.x, -double(cell)*t.width, MPFR_RNDN); mpfr_exp(left.x, x.x, MPFR_RNDU);
    mpfr_set_ui(factorial.x, 1, MPFR_RNDN);
    for (unsigned j=0; j<=t.degree+1; ++j) {
      if (j) check(mpfr_mul_ui(factorial.x, factorial.x, j, MPFR_RNDN)==0, "inexact factorial");
      mpfr_div(a.x, j<=t.degree ? lo.x : left.x, factorial.x, MPFR_RNDD);
      mpfr_div(b.x, j<=t.degree ? hi.x : left.x, factorial.x, MPFR_RNDU);
      Interval v{mpfr_get_float128(a.x,MPFR_RNDD),mpfr_get_float128(b.x,MPFR_RNDU)};
      if (j<=t.degree && j%2) v={-v.hi,-v.lo};
      t.coefficients[cell*t.stride()+j]=v;
    }
  });
}


// Resolve decisions directly in MPFR rather than repeatedly narrowing an
// interval only to round it back to binary128. This also handles exact equality.
int mp_gate(double actual,double x,unsigned n,double ulp,unsigned k,unsigned precision,double& low,double& high) {
  const auto ref=prefix(n,x,precision);
  MP a(precision),lo(precision),hi(precision),lower(precision),upper(precision),threshold(precision),scale(precision);
  mpfr_set_d(a.x,actual,MPFR_RNDN);
  mpfr_sub(lo.x,a.x,ref[n].hi.x,MPFR_RNDD);mpfr_sub(hi.x,a.x,ref[n].lo.x,MPFR_RNDU);
  const bool crosses=mpfr_sgn(lo.x)<=0 && mpfr_sgn(hi.x)>=0;
  mpfr_abs(lo.x,lo.x,MPFR_RNDN);mpfr_abs(hi.x,hi.x,MPFR_RNDN);
  mpfr_max(upper.x,lo.x,hi.x,MPFR_RNDU);
  if(crosses)mpfr_set_zero(lower.x,1);else mpfr_min(lower.x,lo.x,hi.x,MPFR_RNDD);
  mpfr_set_d(scale.x,ulp,MPFR_RNDN);mpfr_mul_2ui(threshold.x,scale.x,k,MPFR_RNDN);
  const int decision=mpfr_cmp(upper.x,threshold.x)<=0 ? 1 : mpfr_cmp(lower.x,threshold.x)>0 ? -1 : 0;
  mpfr_div(lower.x,lower.x,scale.x,MPFR_RNDD);mpfr_div(upper.x,upper.x,scale.x,MPFR_RNDU);
  low=mpfr_get_d(lower.x,MPFR_RNDD);high=mpfr_get_d(upper.x,MPFR_RNDU);
  return decision;
}

struct Error { double lo,hi; unsigned first_pass; };
Error classify(double a, const Reference& r, double x, unsigned n) {
  if(!std::isfinite(a)) return {INFINITY,INFINITY,gates};
  double lo,hi;
  if(a>=r.rounded*.5 && a*.5<=r.rounded) {
    // Sterbenz makes a-rounded exact. The residual and reference-radius guard
    // avoid binary128 arithmetic in the common comparison path.
    const double e=std::abs((a-r.rounded)-r.split.lo)/r.ulp;
    const double g=r.split.radius/r.ulp+e*(4*std::numeric_limits<double>::epsilon())+4*std::numeric_limits<double>::denorm_min();
    lo=std::max(0.,std::nextafter(e-g,-INFINITY)); hi=std::nextafter(e+g,INFINITY);
  } else {
    const auto e=hp::error(a,r.bounds);
    lo=std::max(0.,std::nextafter(double(down(e.lo/Q(r.ulp))),-INFINITY));
    hi=std::nextafter(double(up(e.hi/Q(r.ulp))),INFINITY);
  }
  for(unsigned k=0;k<gates;++k) {
    const double limit=double(1u<<k);
    if(hi<=limit) return {lo,hi,k};
    if(lo>limit) continue;
    ++gate_fallbacks;
    bool decided=false;
    for(unsigned p=256;p<=4096;p*=2) {
      const int decision=mp_gate(a,x,n,r.ulp,k,p,lo,hi);
      if(decision>0) return {lo,hi,k};
      if(decision<0) {decided=true;break;}
    }
    check(decided,"unresolved ULP gate");
  }
  return {lo,hi,gates};
}

void scan(const char* boys_path,const char* exp_path,uint64_t begin,uint64_t end,const char* output) {
  check(begin>=1 && begin<end && end<=final_index+1 && end-begin<1000000,"invalid window shard");
  FastReference boys(boys_path,1000), exponential(exp_path,1000);
  check(boys.table.order==12 && exponential.table.order==0,"reference orders");
  std::array<std::array<int64_t,5>,12> first,last;
  for(auto& r:first)r.fill(-1);for(auto& r:last)r.fill(-1);
  for(uint64_t i=begin;i<end;++i) {
    const double x=double(i)/1000000.,t=x+x,rho=1./t;
    double f=reference(boys,x,0).rounded;
    const double e=reference(exponential,x,0,true).rounded,q=e*rho;
    unsigned chain=0;
    for(unsigned n=1;n<=12;++n) {
      const double a=double(2*n-1)*rho;
      f=std::fma(a,f,-q);
      chain=std::max(chain,classify(f,reference(boys,x,n),x,n).first_pass);
      for(unsigned k=0;k<chain;++k) {if(first[n-1][k]<0)first[n-1][k]=i;last[n-1][k]=i;}
    }
  }
  check(std::fegetround()==FE_TONEAREST && (_mm_getcsr()&~0x3fu)==0x1f80,"floating controls changed");
  std::ofstream out(output);
  out<<"{\"protocol\":\"upward-window-v1\",\"begin\":"<<begin<<",\"end\":"<<end<<",\"rows\":[";
  for(unsigned n=0;n<12;++n)for(unsigned k=0;k<5;++k) {
    if(n||k)out<<',';
    out<<"{\"N\":"<<n+1<<",\"gate\":"<<(1u<<k)<<",\"first_fail\":"<<first[n][k]<<",\"last_fail\":"<<last[n][k]<<"}";
  }
  out<<"],\"rounding_fallbacks\":"<<rounding_fallbacks<<",\"gate_fallbacks\":"<<gate_fallbacks<<"}\n";
  check(bool(out),"write failed");
}
}
int main(int argc,char** argv) try {
  check(mpfr_buildopt_tls_p() && mpfr_buildopt_float128_p(),"MPFR requires TLS/binary128");
  check(std::fesetround(FE_TONEAREST)==0,"rounding mode");_mm_setcsr(0x1f80);
  if(argc==4 && std::string(argv[1])=="--check") {
    FastReference boys(argv[2],1000),exp(argv[3],1000);
    for(double x:{0.,0.000001,1.,36.,128.,500.,744.,745.,746.,1000.}) {
      for(unsigned n=0;n<=12;++n) {
        auto r=reference(boys,x,n);auto direct=hp::mp_reference(n,x,512);
        check(r.bounds.lo<=direct.lo && r.bounds.hi>=direct.hi,"Boys enclosure mismatch");
        check(r.rounded==double(direct.lo) && r.rounded==double(direct.hi),"Boys rounding mismatch");
      }
      auto r=reference(exp,x,0,true);auto direct=hp::mp_reference(0,x,512,true);
      check(r.bounds.lo<=direct.lo && r.bounds.hi>=direct.hi,"exp enclosure mismatch");
      check(r.rounded==double(direct.lo) && r.rounded==double(direct.hi),"exp rounding mismatch");
    }
    std::cout<<"140 reference enclosure/rounding checks passed\n";return 0;
  }
  if(argc==5 && std::string(argv[1])=="--tables") {
    Table b;b.order=12;b.degree=12;b.precision=256;b.width=0x1p-4;b.end=1000;
    generate(b,std::stoul(argv[4]));write_table(b,argv[2]);
    Table e=b;e.coefficients.clear();generate_exp(e,std::stoul(argv[4]));write_table(e,argv[3]);return 0;
  }
  if(argc==7 && std::string(argv[1])=="--scan") {
    scan(argv[2],argv[3],std::stoull(argv[4]),std::stoull(argv[5]),argv[6]);return 0;
  }
  throw std::runtime_error("--tables boys.tbl exp.tbl workers | --scan boys.tbl exp.tbl begin end result.json");
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
