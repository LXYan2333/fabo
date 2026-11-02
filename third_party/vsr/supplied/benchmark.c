#include "constants.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifdef _OPENACC
  #include <openacc.h>
#endif

typedef void (*Method)(size_t N,
                       const double* x,
                       const double* y,
                       const double* c,
                       double* z);

void minimax(size_t,const double*,const double*,const double*,double*);
void beylkin(size_t,const double*,const double*,const double*,double*);
void ishida(size_t,const double*,const double*,const double*,double*);

void benchmark(char* name,
               Method method,
               const size_t N,
               const double*__restrict x,
               const double*__restrict y,
               const double*__restrict c,
               double*__restrict z) {
  clock_t start = clock();
  method(N,x,y,c,z);
  clock_t end = clock();
  double result = 0;
  for (int n = 0; n < N; n++) {
    result += z[n];
  }
  printf("Time of %s: %f s with result %f\n",name,(double)(end-start)/CLOCKS_PER_SEC,result);
}


char* get_device() {
  char* device;
  switch (acc_get_device_type()) {
  case (acc_device_none):
    device = "none";
    break;
  case (acc_device_default):
    device = "default";
    break;
  case (acc_device_host):
    device = "host";
    break;
  case (acc_device_not_host):
    device = "not host";
    break;
  case (acc_device_current):
    device = "current";
    break;
  case (acc_device_nvidia):
    device = "nvidia";
    break;
  default:
    device = "non-standard";
  }
  return device;
}


int main() {
  #ifdef _OPENACC
  printf("Running on %s\n\n",get_device());
  #endif
  
  // Constants
  const size_t N = 2 << 19;  // Length of input array x and y
  const double x_max = 15;   // Boys function argument is in the interval [0,2*x_max]
  const double y_max = 1;    // y vector has elements in [-y_max,y_max]
  const double c_max = 1;    // Coefficient vector has elemnts in [-c_max,c_max]

  // Generate random input
  double* x = (double*)malloc(N*sizeof(double));
  double* y = (double*)malloc(N*sizeof(double));
  double* c = (double*)malloc((k+1)*sizeof(double));
  double* z = (double*)malloc(N*sizeof(double));
  const int seed = 42;
  srand(seed);
  for (size_t n = 0; n < N; n++)
    x[n] = (rand()*x_max)/RAND_MAX;
  for (size_t n = 0; n < N; n++)
    y[n] = ((rand()-RAND_MAX/2)*2*y_max)/RAND_MAX;
  for (size_t l = 0; l < k+1; l++)
    c[l] = ((rand()-RAND_MAX/2)*2*c_max)/RAND_MAX;

  // Run benchmark
  benchmark("minimax",minimax,N,x,y,c,z);
  benchmark("beylkin",beylkin,N,x,y,c,z);
  benchmark("ishida",ishida,N,x,y,c,z);

  free(x);
  free(y);
  free(c);
  free(z);
  return 0;
}
