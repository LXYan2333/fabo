// Strict collector: no DUT or fast-math flags belong in this translation unit.
#include <array>
#include "accuracy_reference_v3.h"
#include <dlfcn.h>
#include <chrono>
#include <limits>
#include <sys/resource.h>
#include <numeric>
#ifdef __FAST_MATH__
#error The collector must be compiled strictly
#endif
namespace {
using Kernel = void (*)(size_t, const double*, double*);
struct Stat {
  Q sum_lo=0,sum_hi=0,max_lo=0,max_hi=0;
  double x=0,actual=0;
  void update(Interval e,double input,double value) {
    sum_lo=std::max(Q(0),down(sum_lo+e.lo)); sum_hi=up(sum_hi+e.hi);
    max_lo=std::max(max_lo,e.lo);
    if(e.hi>max_hi) {max_hi=e.hi;x=input;actual=value;}
  }
};
struct Adapter {
  std::string id,path;unsigned n;Kernel fn;
  std::array<std::array<Stat,3>,13> stats{};
  std::array<uint64_t,13> invalid{};
};
Interval divide(Interval a,Interval b) {return {down(a.lo/b.hi),up(a.hi/b.lo)};}
void environment() {
  check(std::fegetround()==FE_TONEAREST && (_mm_getcsr()&0xffc0)==0x1f80,
        "adapter modified rounding/FTZ/DAZ/exception masks");
}
std::string number(Q x) {return "\""+hp::decimal(x)+"\"";}
std::string hexadecimal(double x) {std::ostringstream s;s<<std::hexfloat<<x;return s.str();}
}
int main(int argc,char** argv) try {
  if(argc>1 && std::string(argv[1])=="--table") return fb3_reference_unused_main(argc,argv);
  if(argc==3 && std::string(argv[1])=="--check-reference") {
    const Table table=read_table(argv[2]);
    for(unsigned i=0;i<80;++i) {
      double x=i==0?0:i==1?table.end:i==2?std::nextafter(table.width/2,0.):table.end*((i*37)%79)/79.;
      std::array<Interval,13> refs;hp::reference(table,x,12,refs.data());
      for(unsigned n=0;n<=12;++n) {
        auto exact=hp::mp_reference(n,x,512);
        check(refs[n].lo<=exact.lo && refs[n].hi>=exact.hi,"accelerated reference failed MPFR enclosure check");
      }
    }
    std::cout<<"{\"reference_checks\":1040}\n";return 0;
  }
  check(argc==9,"scan TABLE MANIFEST FIRST COUNT DENOMINATOR BATCH OUTPUT");
  check(std::string(argv[1])=="scan","unknown command");
  std::fesetround(FE_TONEAREST);_mm_setcsr(0x1f80);
  const Table table=read_table(argv[2]);
  std::ifstream manifest(argv[3]);std::vector<Adapter> adapters;
  for(;;) {
    Adapter a;
    if(!(manifest>>std::quoted(a.id)>>std::quoted(a.path)>>a.n)) break;
    check(a.n<=12&&a.n<=table.order,"unsupported order");
    void* handle=dlopen(a.path.c_str(),RTLD_NOW|RTLD_LOCAL);
    if(!handle) throw std::runtime_error(dlerror());
    a.fn=reinterpret_cast<Kernel>(dlsym(handle,"boys_accuracy"));
    check(a.fn,"missing boys_accuracy ABI");adapters.push_back(a);
  }
  check(manifest.eof()&&!adapters.empty(),"invalid/empty manifest");environment();
  const uint64_t first=std::stoull(argv[4]),count=std::stoull(argv[5]),denom=std::stoull(argv[6]);
  const size_t batch=std::stoull(argv[7]);
  check(count&&denom&&batch&&batch<=1048576&&denom<(1ULL<<53)&&first<(1ULL<<53)&&count<(1ULL<<53)-first,"invalid scan bounds");
  check(double(first+count-1)/double(denom)<=table.end,"scan exceeds reference table");
  std::vector<double> xs(batch),output(batch*13+16);
  double* out=output.data()+8;
  std::vector<std::array<Interval,13>> refs(batch);
  const bool mixed=std::getenv("FABO_ACCURACY_MIXED")!=nullptr;
  const uint64_t grid_total=mixed?std::stoull(std::getenv("FABO_ACCURACY_GRID_TOTAL")?std::getenv("FABO_ACCURACY_GRID_TOTAL"):"0"):first+count;
  check(grid_total>=first+count && grid_total<(1ULL<<53),"invalid mixed grid total");
  uint64_t stride=1000003;while(std::gcd(stride,grid_total)!=1)++stride;
  if(mixed)check(double(grid_total-1)/double(denom)<=table.end,"mixed grid exceeds reference table");
  uint64_t input_count=0;
  const auto start=std::chrono::steady_clock::now();
  for(uint64_t offset=0;offset<count;offset+=batch) {
    const size_t active=std::min<uint64_t>(batch,count-offset);
    for(size_t i=0;i<active;++i) {
      const uint64_t position=first+offset+i;
      const uint64_t index=mixed?uint64_t((__uint128_t(position)*stride+17)%grid_total):position;
      xs[i]=double(index)/double(denom);
      hp::reference(table,xs[i],12,refs[i].data());
    }
    for(auto& a:adapters) {
      std::fill(output.begin(),output.end(),std::numeric_limits<double>::quiet_NaN());
      const auto original=xs;
      a.fn(active,xs.data(),out);environment();
      check(std::memcmp(xs.data(),original.data(),active*sizeof(double))==0,"adapter modified inputs");
      for(size_t j=0;j<8;++j)check(std::isnan(output[j]),"adapter overwrote output prefix guard");
      for(size_t j=8+(a.n+1)*active;j<output.size();++j)check(std::isnan(output[j]),"adapter overwrote output guard");
      for(unsigned n=0;n<=a.n;++n) for(size_t i=0;i<active;++i) {
        double v=out[n*active+i];
        if(!std::isfinite(v)){++a.invalid[n];continue;}
        Interval r=refs[i][n];
        double lo=static_cast<double>(r.lo),hi=static_cast<double>(r.hi);
        if(std::ilogb(lo)!=std::ilogb(hi)) r=hp::mp_reference(n,xs[i],512);
        lo=static_cast<double>(r.lo);hi=static_cast<double>(r.hi);
        check(r.lo>0&&std::ilogb(lo)==std::ilogb(hi),"unresolved reference spacing");
        const Q ulp=ldexpq(1,std::max(-1074,std::ilogb(lo)-52));
        Interval abs=hp::error(v,r);
        const Interval errors[]={abs,divide(abs,r),divide(abs,{ulp,ulp})};
        for(int m=0;m<3;++m)a.stats[n][m].update(errors[m],xs[i],v);
      }
    }
    input_count+=active;
  }
  std::ofstream f(argv[8]);check(bool(f),"cannot open output");
  f<<std::setprecision(17)<<"{\"first\":"<<first<<",\"count\":"<<count<<",\"seconds\":"
   <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"rows\":[";
  bool comma=false;
  for(auto& a:adapters)for(unsigned n=0;n<=a.n;++n)for(int m=0;m<3;++m) {
    if(comma)f<<',';comma=true;auto& s=a.stats[n][m];
    // Reevaluate the retained witness directly; maxima remain interval bounds.
    auto r=hp::mp_reference(n,s.x,512);auto e=hp::error(s.actual,r);
    if(m==1)e=divide(e,r);
    if(m==2){Q u=ldexpq(1,std::max(-1074,std::ilogb(static_cast<double>(r.lo))-52));e=divide(e,{u,u});}
    f<<"{\"id\":"<<std::quoted(a.id)<<",\"N\":"<<a.n<<",\"n\":"<<n<<",\"metric\":"<<std::quoted(m==0?"absolute":m==1?"relative":"ulp")
     <<",\"invalid\":"<<a.invalid[n]<<",\"sum_lo\":"<<number(s.sum_lo)<<",\"sum_hi\":"<<number(s.sum_hi)
     <<",\"max_lo\":"<<number(s.max_lo)<<",\"max_hi\":"<<number(s.max_hi)<<",\"witness_x\":"<<s.x<<",\"witness_actual\":"<<s.actual
     <<",\"witness_x_hex\":"<<std::quoted(hexadecimal(s.x))<<",\"witness_actual_hex\":"<<std::quoted(hexadecimal(s.actual))
     <<",\"witness_error_lo\":"<<number(e.lo)<<",\"witness_error_hi\":"<<number(e.hi)<<"}";
  }
  struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
  f<<"],\"peak_rss_kib\":"<<usage.ru_maxrss<<",\"inputs_processed\":"<<input_count<<"}\n";check(bool(f),"output write failed");
} catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
