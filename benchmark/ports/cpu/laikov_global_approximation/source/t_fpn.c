#define FN NF

#include <stdlib.h>

#if   NF == 1

#include <math.h>
typedef float real;
#define fsqrt sqrtf
#define fexp expf
#define fPI M_PI

#elif NF == 2

#include <math.h>
typedef double real;
#define fsqrt sqrt
#define fexp exp
#define fPI M_PI

#elif NF == 3

#define __USE_GNU
#include <math.h>
typedef long double real;
#define fsqrt sqrtl
#define fexp expl
#define fPI M_PIl

#else

#include <quadmath.h>
typedef __float128 real;
#define fsqrt sqrtq
#define fexp expq
#define fPI M_PIq
#undef  FN
#define FN

#endif

#define ffff(p,n) p ## n
#define fff(p,n) ffff(p,n)
#define ff(p) fff(p,FN)

void ff(fnsum) (real *f, real x, int L)
{
  real u, v, p, q, e;
  int  k;
  q = L + 0.5Q;
  p = 0.5Q/q;
  u = p;
  do {
    v = u;
    q += 1.0Q;
    p *= x/q;
    u += p;
  } while (u != v);
  e = fexp (-x);
  f[L] = u*e;
  v = x + x;
  for (k = L; k; k--) {
    f[k - 1] = (v*f[k] + e)/(k + k - 1);
  }
  return;
}

real ff(powrn) (real x, unsigned int n)
{
  real p, z;
  p = fsqrt (x);
  z = x;
  if (n & 1) {
    p *= z;
  }
  for (n >>= 1; n; n >>= 1) {
    z *= z;
    if (n & 1) {
      p *= z;
    }
  }
  return p;
}

void ff(fpen) (real *f, real c, real p, real e, real x, int L)
{
  real v;
  int  k;
  v = ff(powrn) (p, L);
  v = c/(x + v*e);
  f[L] = ff(powrn) (v, L);
  v = x + x;
  for (k = L; k; k--) {
    f[k - 1] = (v*f[k] + e)/(k + k - 1);
  }
  return;
}

void ff(fnlim) (real *f, real x, int L)
{
  real v;
  int  k;
  v = 0.5Q/x;
  f[0] = fsqrt (0.5Q*fPI*v);
  for (k = 1; k <= L; k++) {
    f[k] = (k + k - 1)*v*f[k - 1];
  }
  return;
}

real ff(fpqn) (real *c, real x, int n)
{
  real p, q;
  int  k;
    p =   x + c[0];
    q =       c[1];
  for (k = 2; k <= n + n; k += 2) {
    p = p*x + c[    k];
    q = q*x + c[1 + k];
  }
  p /= q;
  return p;
}

real ff(fz0pqn) (real *c, real x, int nu, int nv, int n)
{
  real p, z;
  int  i, k;
  p = c[0];
  i = 1;
  for (k = 0; k < nu + nu; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    p *= z;
    i += 2;
  }
  for (; k < n; k++) {
    z = x   + c[    i];
    p *= z;
    i++;
  }
  p = 1/p;
  for (k = 0; k < nv + nv; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    p *= z;
    i += 2;
  }
  for (; k <= n; k++) {
    z = x   + c[    i];
    p *= z;
    i++;
  }
  return p;
}

real ff(fz1pqn) (real *c, real x, int nu, int nv, int n)
{
  real p, z;
  int  i, k;
  p = c[0];
  i = 1;
  for (k = 0; k < nu + nu; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    p *= z;
    i += 2;
  }
  for (; k < n; k++) {
    z = x   + c[    i];
    p *= z;
    i++;
  }
  p = 1/p;
  for (k = 0; k < nv + nv; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    p *= z;
    i += 2;
  }
  for (; k < n - 1; k++) {
    z = x   + c[    i];
    p *= z;
    i++;
  }
  p = x*p + c[i];
  i++;
  p = x*p + c[i];
  return p;
}

real ff(fzcpqn) (real *c, real x, int nu, int nv, int n)
{
  real p, q, z;
  int  i, k;
  p = c[0];
  i = 1;
  for (k = 1; k <= nu; k++) {
    p = p*x + c[i];
    i++;
  }
  for (; k < n; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    p *= z;
    i += 2;
  }
  if (nv) {
    q = x + c[i];
    i++;
  } else {
    q = 1;
  }
  for (k = 2; k <= nv; k++) {
    q = q*x + c[i];
    i++;
  }
  for (; k <= n; k += 2) {
    z = x   + c[    i];
    z = z*z + c[1 + i];
    q *= z;
    i += 2;
  }
  p /= q;
  p = x*p + c[i];
  i++;
  p = x*p + c[i];
  return p;
}

void ff(fpqen) (real *f, real *c, int *o, real x, int L, int n)
{
  real e, p;
  if (x < c[3 + n + n]) {
    e = fexp (-x);
    if (o == NULL) {
      p = ff(fpqn) (c, x, n);
    } else if (o[2] == 0) {
      p = ff(fz0pqn) (c, x, o[0], o[1], n);
    } else if (o[2] == 1) {
      p = ff(fz1pqn) (c, x, o[0], o[1], n);
    } else {
      p = ff(fzcpqn) (c, x, o[0], o[1], n);
    }
    ff(fpen) (f, c[2 + n + n], p, e, x, L);
  } else {
    ff(fnlim) (f, x, L);
  }
  return;
}

