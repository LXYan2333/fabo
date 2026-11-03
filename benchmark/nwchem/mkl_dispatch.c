/* Untimed runtime evidence, not a promise of cross-machine bitwise identity. */
#include <mkl.h>
#include <stdio.h>
static int report(FILE *out) {
  char version[512];
  mkl_get_version_string(version, sizeof(version));
  fprintf(out,"VERSION %s\nCNR %d\nAUTO_CNR %d\nTHREADS %d\n", version,
         mkl_cbwr_get(MKL_CBWR_ALL), mkl_cbwr_get_auto_branch(), mkl_get_max_threads());
  FILE *maps=fopen("/proc/self/maps","r");
  if (!maps) return 1;
  char line[4096];
  while (fgets(line,sizeof(line),maps)) fprintf(out,"MAP %s",line);
  fclose(maps);
  return 0;
}
#ifdef FABO_NWCHEM_MKL_HOOK
/* Called after timing, in the actual NWChem process. No BLAS warmup. */
void fabo_nw_mkl_report_(void) {
  FILE *out=fopen("mkl-runtime.txt","w");
  if (!out) return;
  report(out);
  fclose(out);
}
#else
int main(void) {
  double a[4]={1,2,3,4}, b[4]={4,3,2,1}, c[4]={0};
  mkl_verbose(1);
  cblas_dgemm(CblasRowMajor,CblasNoTrans,CblasNoTrans,2,2,2,1,a,2,b,2,0,c,2);
  mkl_verbose(0);
  printf("WITNESS %.17g\n",c[0]);
  return report(stdout);
}
#endif
