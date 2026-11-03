#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <cstdio>
#include <cstdlib>
#include <immintrin.h>
#include <limits>
extern "C" void fabo_reference_boys(int,int,const double*,double*);
int main(int argc,char** argv) {
  if(argc!=2)return 2;
  std::ifstream f(argv[1],std::ios::binary);
  std::array<std::uint64_t,3> record;
  std::size_t tested=0;
  while(f.read(reinterpret_cast<char*>(record.data()),24)) {
    if(record[1]>8)continue;
    double x[8],out[9*8];for(auto& value:x)value=std::numeric_limits<double>::quiet_NaN();
    std::memcpy(x,record.data(),8);
    const auto original=_mm_getcsr();
    for(unsigned mode:{0u,0x40u,0x8000u,0x8040u,0xe040u}) {
      const auto requested=(original&~(0x8040u|0x6000u))|mode;
      _mm_setcsr(requested);
      fabo_reference_boys(int(record[1]),1,x,out);
      if(_mm_getcsr()!=requested)return 3;
      _mm_setcsr(original);
      std::uint64_t bits;std::memcpy(&bits,out+record[1]*8,8);
      if(bits!=record[2]){std::fprintf(stderr,"reference mismatch order=%llu x=%a\n",(unsigned long long)record[1],x[0]);return 1;}
      for(unsigned l=0;l<=record[1];++l)for(int i=1;i<8;++i)if(out[l*8+i]!=0)return 1;
    }
    ++tested;
    if(std::getenv("FABO_REFERENCE_FORCE_FALLBACK")&&tested==64)break;
  }
  if((!f.eof()&&!std::getenv("FABO_REFERENCE_FORCE_FALLBACK"))||tested==0)return 2;
  std::printf("certified %zu MPFR fixtures\n",tested);
}
