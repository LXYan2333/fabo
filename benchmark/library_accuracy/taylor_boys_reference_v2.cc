// Strict, CPU-independent reference provider. Never linked into the DUT.
#define MPFR_WANT_FLOAT128 1
#define mpfr_float128 __float128
#include <mpfr.h>
#include <quadmath.h>
#include <algorithm>
#include <atomic>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>
#include <immintrin.h>

namespace {
using Q = __float128;
struct Interval { Q lo, hi; };
Q down(Q x) { return nextafterq(x,-HUGE_VALQ); }
Q up(Q x) { return nextafterq(x,HUGE_VALQ); }
Interval add(Interval a, Interval b) { return {down(a.lo+b.lo),up(a.hi+b.hi)}; }
Interval mul(Interval a, Interval b) {
  const Q p[] = {a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
  return {down(*std::min_element(p,p+4)),up(*std::max_element(p,p+4))};
}
struct MP {
  mpfr_t x;
  explicit MP(mpfr_prec_t p) { mpfr_init2(x,p); }
  ~MP() { mpfr_clear(x); }
  MP(const MP& a) { mpfr_init2(x,mpfr_get_prec(a.x)); mpfr_set(x,a.x,MPFR_RNDN); }
  MP& operator=(const MP& a) { mpfr_set_prec(x,mpfr_get_prec(a.x)); mpfr_set(x,a.x,MPFR_RNDN); return *this; }
};
struct Bounds { MP lo,hi; explicit Bounds(mpfr_prec_t p):lo(p),hi(p){} };
void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }

// Positive series, not a cancellation-prone alternating expansion:
// F_n = exp(-x) sum t_k, t_0=1/(2n+1), t_(k+1)/t_k=2x/(2n+2k+3).
// Once the (decreasing) next-term ratio is below 1, next/(1-r) bounds
// every remaining term. All operations are MPFR directed outwards.
std::vector<Bounds> prefix(unsigned order,double x,mpfr_prec_t precision) {
  std::vector<Bounds> result(order+1,Bounds(precision));
  MP xx(precision),twox(precision),neg(precision),el(precision),eh(precision);
  mpfr_set_d(xx.x,x,MPFR_RNDN); mpfr_mul_2ui(twox.x,xx.x,1,MPFR_RNDN);
  mpfr_neg(neg.x,xx.x,MPFR_RNDN);
  mpfr_exp(el.x,neg.x,MPFR_RNDD); mpfr_exp(eh.x,neg.x,MPFR_RNDU);
  MP tl(precision),th(precision),sl(precision),sh(precision),nl(precision),nh(precision);
  MP ratio(precision),denom(precision),tail(precision),epsilon(precision);
  mpfr_set_ui(tl.x,1,MPFR_RNDN); mpfr_div_ui(tl.x,tl.x,2*order+1,MPFR_RNDD);
  mpfr_set_ui(th.x,1,MPFR_RNDN); mpfr_div_ui(th.x,th.x,2*order+1,MPFR_RNDU);
  mpfr_set(sl.x,tl.x,MPFR_RNDD); mpfr_set(sh.x,th.x,MPFR_RNDU);
  for (unsigned long k=0;;++k) {
    const unsigned long divisor=2UL*order+2*k+3;
    mpfr_mul(nl.x,tl.x,twox.x,MPFR_RNDD); mpfr_div_ui(nl.x,nl.x,divisor,MPFR_RNDD);
    mpfr_mul(nh.x,th.x,twox.x,MPFR_RNDU); mpfr_div_ui(nh.x,nh.x,divisor,MPFR_RNDU);
    mpfr_div_ui(ratio.x,twox.x,divisor,MPFR_RNDU);
    if (mpfr_cmp_ui(ratio.x,1)<0) {
      mpfr_ui_sub(denom.x,1,ratio.x,MPFR_RNDD);
      mpfr_div(tail.x,nh.x,denom.x,MPFR_RNDU);
      mpfr_mul_2si(epsilon.x,sh.x,-precision+16,MPFR_RNDD);
      if (mpfr_cmp(tail.x,epsilon.x)<=0) {
        mpfr_add(sh.x,sh.x,tail.x,MPFR_RNDU); break;
      }
    }
    mpfr_add(sl.x,sl.x,nl.x,MPFR_RNDD); mpfr_add(sh.x,sh.x,nh.x,MPFR_RNDU);
    mpfr_set(tl.x,nl.x,MPFR_RNDD); mpfr_set(th.x,nh.x,MPFR_RNDU);
  }
  mpfr_mul(result[order].lo.x,sl.x,el.x,MPFR_RNDD);
  mpfr_mul(result[order].hi.x,sh.x,eh.x,MPFR_RNDU);
  for (unsigned n=order;n>0;--n) {
    auto& a=result[n-1]; const auto& b=result[n];
    mpfr_mul(a.lo.x,twox.x,b.lo.x,MPFR_RNDD); mpfr_add(a.lo.x,a.lo.x,el.x,MPFR_RNDD);
    mpfr_div_ui(a.lo.x,a.lo.x,2*n-1,MPFR_RNDD);
    mpfr_mul(a.hi.x,twox.x,b.hi.x,MPFR_RNDU); mpfr_add(a.hi.x,a.hi.x,eh.x,MPFR_RNDU);
    mpfr_div_ui(a.hi.x,a.hi.x,2*n-1,MPFR_RNDU);
  }
  return result;
}
bool same(double a,double b) { return std::memcmp(&a,&b,sizeof(double))==0; }
void fallback(unsigned order,double x,unsigned precision,double* out) {
  for (mpfr_prec_t p=precision;;p*=2) {
    const auto values=prefix(order,x,p);
    bool unique=true;
    for(unsigned n=0;n<=order;++n) {
      const double lo=mpfr_get_d(values[n].lo.x,MPFR_RNDN),hi=mpfr_get_d(values[n].hi.x,MPFR_RNDN);
      if (!same(lo,hi)) { unique=false; break; }
      out[n]=lo;
    }
    if(unique) return;
    check(p<=MPFR_PREC_MAX/2,"MPFR precision exhausted");
  }
}
template<class F> void parallel(std::size_t count,unsigned workers,F job) {
  check(workers>0,"reference worker count must be positive");
  std::atomic<std::size_t> next{0}; std::atomic<bool> failed{false};
  std::atomic_flag lock=ATOMIC_FLAG_INIT; std::exception_ptr exception;
  auto worker=[&] {
    try {
      std::fesetround(FE_TONEAREST); _mm_setcsr(0x1f80);
      for(auto i=next.fetch_add(1);i<count&&!failed;i=next.fetch_add(1)) job(i);
    } catch (...) {
      while(lock.test_and_set()) {}
      if(!exception) exception=std::current_exception();
      lock.clear(); failed=true;
    }
    mpfr_free_cache();
  };
  std::vector<std::thread> threads;
  for(std::size_t i=0;i<std::min<std::size_t>(workers,count);++i) threads.emplace_back(worker);
  for(auto& t:threads)t.join();
  if(exception)std::rethrow_exception(exception);
}
struct Table {
  unsigned order=0,degree=0,precision=0; std::uint64_t cells=0; double width=0,end=0;
  std::vector<Interval> coefficients;
  // Each order stores degree+1 coefficients and one positive remainder factor.
  std::size_t stride() const { return (order+1)*(degree+2); }
};
template<class T> void field(std::ostream& out,const T& v) { out.write(reinterpret_cast<const char*>(&v),sizeof(v)); }
template<class T> void field(std::istream& in,T& v) { in.read(reinterpret_cast<char*>(&v),sizeof(v)); }
void write_table(const Table& t,const char* path) {
  std::ofstream out(path,std::ios::binary); const std::uint64_t version=1;
  field(out,version); field(out,t.order); field(out,t.degree); field(out,t.precision);
  field(out,t.cells); field(out,t.width); field(out,t.end);
  out.write(reinterpret_cast<const char*>(t.coefficients.data()),t.coefficients.size()*sizeof(Interval));
  check(bool(out),"table publication failed");
}
Table read_table(const char* path) {
  std::ifstream in(path,std::ios::binary); Table t; std::uint64_t version=0;
  field(in,version); field(in,t.order); field(in,t.degree); field(in,t.precision);
  field(in,t.cells); field(in,t.width); field(in,t.end);
  check(bool(in)&&version==1&&t.cells&&t.width>0,"invalid reference table");
  t.coefficients.resize(t.cells*t.stride());
  in.read(reinterpret_cast<char*>(t.coefficients.data()),t.coefficients.size()*sizeof(Interval));
  check(bool(in)&&in.peek()==EOF,"incomplete or trailing reference table");
  return t;
}
void generate(Table& t,unsigned workers) {
  check(t.precision>=64&&t.degree>0&&t.width>0&&std::isfinite(t.end)&&t.end>0,"invalid Taylor reference policy");
  int exponent=0; check(std::frexp(t.width,&exponent)==.5,"reference cell width must be dyadic");
  t.cells=static_cast<std::uint64_t>(std::ceil(t.end/t.width));
  t.coefficients.resize(t.cells*t.stride());
  parallel(t.cells,workers,[&](std::size_t cell) {
    const double a=cell*t.width,center=(cell+.5)*t.width;
    check(std::isfinite(center)&&center>a,"unrepresentable reference cell");
    const auto values=prefix(t.order+t.degree+1,center,t.precision);
    const auto left=prefix(t.order+t.degree+1,a,t.precision);
    for(unsigned n=0;n<=t.order;++n) {
      MP factorial(t.precision),lo(t.precision),hi(t.precision);
      mpfr_set_ui(factorial.x,1,MPFR_RNDN);
      for(unsigned j=0;j<=t.degree+1;++j) {
        if(j) { // factorial is an exact integer at the configured precision.
          check(mpfr_mul_ui(factorial.x,factorial.x,j,MPFR_RNDN)==0,"factorial requires more table precision");
        }
        const auto& value=j<=t.degree?values[n+j]:left[n+j];
        mpfr_div(lo.x,value.lo.x,factorial.x,MPFR_RNDD);
        mpfr_div(hi.x,value.hi.x,factorial.x,MPFR_RNDU);
        Interval interval{mpfr_get_float128(lo.x,MPFR_RNDD),mpfr_get_float128(hi.x,MPFR_RNDU)};
        if(j<=t.degree&&j%2) interval={-interval.hi,-interval.lo};
        t.coefficients[cell*t.stride()+n*(t.degree+2)+j]=interval;
      }
    }
  });
}
std::vector<double> read_inputs(const char* path) {
  std::ifstream in(path,std::ios::binary|std::ios::ate); const auto bytes=in.tellg();
  check(bytes>0&&bytes%sizeof(double)==0,"invalid input corpus");
  std::vector<double> xs(bytes/sizeof(double)); in.seekg(0);
  in.read(reinterpret_cast<char*>(xs.data()),bytes); check(bool(in),"truncated input corpus"); return xs;
}
void evaluate(const Table& t,const char* input,const char* output,unsigned workers) {
  const auto xs=read_inputs(input); std::vector<double> ys(xs.size()*(t.order+1));
  std::atomic<std::size_t> fallback_points{0};
  parallel(xs.size(),workers,[&](std::size_t i) {
    const double x=xs[i]; check(std::isfinite(x)&&x>=0&&x<=t.end,"reference input outside table domain");
    double* result=ys.data()+i*(t.order+1);
    if(x==0) { fallback(t.order,x,t.precision,result); ++fallback_points; return; }
    const auto cell=std::min<std::uint64_t>(static_cast<std::uint64_t>(x/t.width),t.cells-1);
    const double center=(cell+.5)*t.width;
    const Q diff=Q(x)-Q(center); const Interval delta{down(diff),up(diff)};
    const Q distance=std::max(fabsq(delta.lo),fabsq(delta.hi));
    Q power=1;
    for(unsigned j=0;j<=t.degree;++j) power=up(power*distance);
    bool unique=true;
    for(unsigned n=0;n<=t.order;++n) {
      const auto* coefficients=t.coefficients.data()+cell*t.stride()+n*(t.degree+2);
      Interval value=coefficients[t.degree];
      for(unsigned j=t.degree;j>0;--j) value=add(mul(value,delta),coefficients[j-1]);
      const Q remainder=up(power*coefficients[t.degree+1].hi);
      value={down(value.lo-remainder),up(value.hi+remainder)};
      const double lo=static_cast<double>(value.lo),hi=static_cast<double>(value.hi);
      if(!same(lo,hi)) { unique=false; break; }
      result[n]=lo;
    }
    if(!unique) { fallback(t.order,x,t.precision,result); ++fallback_points; }
  });
  std::ofstream out(output,std::ios::binary);
  out.write(reinterpret_cast<const char*>(ys.data()),ys.size()*sizeof(double)); check(bool(out),"reference output failed");
  std::cout << "{\"point_count\":" << xs.size() << ",\"mpfr_fallback_point_count\":" << fallback_points << "}\n";
}
}
int main(int argc,char** argv) {
  try {
    check(mpfr_buildopt_tls_p()&&mpfr_buildopt_float128_p(),"MPFR needs TLS and binary128 support");
    if(argc==9&&std::string(argv[1])=="--table") {
      Table t; t.order=std::stoul(argv[3]); t.degree=std::stoul(argv[4]); t.width=std::stod(argv[5]);
      t.end=std::stod(argv[6]); t.precision=std::stoul(argv[7]);
      generate(t,std::stoul(argv[8])); write_table(t,argv[2]); return 0;
    }
    if(argc==7&&std::string(argv[1])=="--evaluate") {
      evaluate(read_table(argv[2]),argv[3],argv[4],std::stoul(argv[5]));
      check(std::string(argv[6])=="--certified","explicit certified mode required"); return 0;
    }
    throw std::runtime_error("expected --table out order degree width end precision workers, or --evaluate table x out workers --certified");
  } catch(const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
