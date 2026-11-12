#include <quadmath.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <fenv.h>

typedef __float128 real;

real c1fn (int L);

real x1fn_24 (int L);
real x1fn_53 (int L);
real x1fn_64 (int L);
real x1fn_113 (int L);

int cpqfn (real **c, int L, int n);
int z0pqfn (real **c, int *o, int L, int n);
int z1pqfn (real **c, int *o, int L, int n);
int zcpqfn (real **c, int *o, int L, int n);

void fnsum (real *f, real x, int L);
void fnlim (real *f, real x, int L);
void fpqen (real *f, real *c, int *o, real x, int L, int n);

void fnsum3 (long double *f, long double x, int L);
void fnlim3 (long double *f, long double x, int L);
void fpqen3 (long double *f, long double *c, int *o, long double x, int L, int n);

void fnsum2 (double *f, double x, int L);
void fnlim2 (double *f, double x, int L);
void fpqen2 (double *f, double *c, int *o, double x, int L, int n);

void fnsum1 (float *f, float x, int L);
void fnlim1 (float *f, float x, int L);
void fpqen1 (float *f, float *c, int *o, float x, int L, int n);

int ncpq (int b, int L)
{
  int n, p;
  for (n = 2; ; n++) {
    p = cpqfn (NULL, L, n);
    if (p < 0) {
      break;
    }
    if (p == 0) {
      continue;
    }
    if (p >= b) {
      return n;
    }
  }
  return -1;
}

int czpqfn (real **b, int *o, int L, int n)
{
  int p;
  if (o == NULL) {
    p = cpqfn  (b,    L, n);
  } else if (o[2] == 0) {
    p = z0pqfn (b, o, L, n);
  } else if (o[2] == 1) {
    p = z1pqfn (b, o, L, n);
  } else {
    p = zcpqfn (b, o, L, n);
  }
  return p;
}

int cpqn (real *c, int *o, int L, int n)
{
  real *b;
  int  p, k;
  if (n <= 0) {
    c[0] = x1fn_113 (L);
    return 113;
  }
  p = czpqfn (&b, o, L, n);
  if (p <= 0) {
    return -1;
  }
  for (k = 0; k <= 1 + n + n; k++) {
    c[k] = b[k];
  }
  c[2 + n + n] = c1fn (L);
  c[3 + n + n] = x1fn_113 (L);
  return p;
}

int cpqn3 (long double *c, int *o, int L, int n)
{
  real *b;
  int  p, k;
  if (n <= 0) {
    c[0] = x1fn_64 (L);
    return 64;
  }
  p = czpqfn (&b, o, L, n);
  if (p <= 0) {
    return -1;
  }
  for (k = 0; k <= 1 + n + n; k++) {
    c[k] = b[k];
  }
  c[2 + n + n] = c1fn (L);
  c[3 + n + n] = x1fn_64 (L);
  return p;
}

int cpqn2 (double *c, int *o, int L, int n)
{
  real *b;
  int  p, k;
  if (n <= 0) {
    c[0] = x1fn_53 (L);
    return 53;
  }
  p = czpqfn (&b, o, L, n);
  if (p <= 0) {
    return -1;
  }
  for (k = 0; k <= 1 + n + n; k++) {
    c[k] = b[k];
  }
  c[2 + n + n] = c1fn (L);
  c[3 + n + n] = x1fn_53 (L);
  return p;
}

int cpqn1 (float *c, int *o, int L, int n)
{
  real *b;
  int  p, k;
  if (n <= 0) {
    c[0] = x1fn_24 (L);
    return 24;
  }
  p = czpqfn (&b, o, L, n);
  if (p <= 0) {
    return -1;
  }
  for (k = 0; k <= 1 + n + n; k++) {
    c[k] = b[k];
  }
  c[2 + n + n] = c1fn (L);
  c[3 + n + n] = x1fn_24 (L);
  return p;
}

int main (int argc, char **argv)
{
  int    nc24[37] = {
     4,  4,  5,  5,  5,  5,  5,  5,  5,  5,  6,  6,  6,  6,  6,  6,
     6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,  6,
     6,  6,  6,  6,  6
  };
  int    nc53[37] = {
    10, 10, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 13,
    13, 13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
    14, 14, 14, 14, 14
  };
  real   f[37], g[37], e[37];
  real   c[44];
  real   x, r;
  long double f3[37];
  long double c3[44];
  long double x3;
  double f2[37];
  double c2[44];
  double x2;
  float  f1[37];
  float  c1[44];
  float  x1;
  int    nnz[3];
  int    *nz;
  int    nt, nf, kz, ko, nc, L, k;
  int    mp, np, mb, nb, lb, kb, kp, kx, i;
  L  = 0;
  nf = 0;
  kz = 0;
  nc = 0;
  nt = 2;
  mp = 0;
  np = 6;
  lb = 5;
  kx = 0;
  ko = 1;
  for (i = 1; i < argc; i++) {
    if (sscanf (argv[i], "L:%d", &L) == 1) {
      continue;
    }
    if (sscanf (argv[i], "z:%d", &kz) == 1) {
      continue;
    }
    if (sscanf (argv[i], "f:%d", &nf) == 1) {
      continue;
    }
    if (sscanf (argv[i], "c:%d", &nc) == 1) {
      continue;
    }
    if (sscanf (argv[i], "t:%d", &nt) == 1) {
      continue;
    }
    if (sscanf (argv[i], "p:%d,%d", &mp, &np) > 1) {
      continue;
    }
    if (sscanf (argv[i], "b:%d", &lb) == 1) {
      continue;
    }
    if (!strcmp (argv[i], "x:")) {
      kx = 1;
      continue;
    }
    if (sscanf (argv[i], "o:%d", &ko) == 1) {
      continue;
    }
    if (strstr (argv[i], "r:") == argv[i]) {
      switch (argv[i][2]) {
        case 'n': fesetround (FE_TONEAREST);  break;
        case 'u': fesetround (FE_UPWARD);     break;
        case 'd': fesetround (FE_DOWNWARD);   break;
        case 'z': fesetround (FE_TOWARDZERO); break;
      }
      fprintf (stderr, "# r=0x%08x\n", fegetround ());
      continue;
    }
  }
  if ((nt <= 0) || (nt > 4)) {
    nt = 4;
  }
  if ((L < 0) || (L > 36)) {
    L = 36;
  }
  nnz[2] = kz - 1;
  nz = kz ? nnz : NULL;
  if (nc < 0) {
    if        ((nc == -1) || ((nc <= -3) && (nt == 1))) {
      nc = nc24[L];
    } else if ((nc == -2) || ((nc <= -3) && (nt == 2))) {
      nc = nc53[L];
    } else {
      nf = 64;
    }
  }
  if (nc > 0) {
    nf = cpqfn (NULL, L, nc);
    nf = (nf > 0) ? nf : -1;
  } else if (nf > 0) {
    nc = ncpq (nf, L);
  } else {
    nc = 0;
  }
  fprintf (stderr, "# L = %2d  nf = %2d  nc = %2d\n", L, nf, nc);
  if ((nf < 0) || (nc < 0)) {
    return -1;
  }
  if        (nt == 1) {
    cpqn1 (c1, nz, L, nc);
  } else if (nt == 2) {
    cpqn2 (c2, nz, L, nc);
  } else if (nt == 3) {
    cpqn3 (c3, nz, L, nc);
  } else {
    cpqn  (c , nz, L, nc);
  }
  r = x1fn_113 (L);
  mb = 1 << lb;
  nb = mb + mb - 1;
  if (nz != NULL) {
    fprintf (stderr, "# nz = %2d, %2d\n", nz[0], nz[1]);
  }
  for (k = 0; k <= L; k++) {
    e[k] = 0;
  }
  for (kp = mp; kp <= np; kp++) {
    for (kb = (kp == mp) ? 0 : mb; kb <= nb; kb++) {
      if        (nt == 1) {
        x1 = ldexpf (kb, kp - lb);
        if (kx) {
          x1 *= nc ? c1[3 + nc + nc] : c1[0];
        }
        x = x1;
      } else if (nt == 2) {
        x2 = ldexp  (kb, kp - lb);
        if (kx) {
          x2 *= nc ? c2[3 + nc + nc] : c2[0];
        }
        x = x2;
      } else if (nt == 3) {
        x3 = ldexpl (kb, kp - lb);
        if (kx) {
          x3 *= nc ? c3[3 + nc + nc] : c3[0];
        }
        x = x3;
      } else {
        x  = ldexpq (kb, kp - lb);
        if (kx) {
          x  *= nc ? c [3 + nc + nc] : c [0];
        }
      }
      if (x < r) {
        fnsum (f, x, L);
      } else {
        fnlim (f, x, L);
      }
      if (nc > 0) {
        if        (nt == 1) {
          fpqen1 (f1, c1, nz, x1, L, nc);
        } else if (nt == 2) {
          fpqen2 (f2, c2, nz, x2, L, nc);
        } else if (nt == 3) {
          fpqen3 (f3, c3, nz, x3, L, nc);
        } else {
          fpqen  (g , c , nz, x , L, nc);
        }
      } else {
        if        (nt == 1) {
          if (x1 < c1[0]) {
            fnsum1 (f1, x1, L);
          } else {
            fnlim1 (f1, x1, L);
          }
        } else if (nt == 2) {
          if (x2 < c2[0]) {
            fnsum2 (f2, x2, L);
          } else {
            fnlim2 (f2, x2, L);
          }
        } else if (nt == 3) {
          if (x3 < c3[0]) {
            fnsum3 (f3, x3, L);
          } else {
            fnlim3 (f3, x3, L);
          }
        } else {
          return -1;
        }
      }
      for (k = 0; k <= L; k++) {
        if        (nt == 1) {
          g[k] = f1[k];
        } else if (nt == 2) {
          g[k] = f2[k];
        } else if (nt == 3) {
          g[k] = f3[k];
        }
        g[k] = (g[k] - f[k])/f[k];
        if (fabsq (g[k]) > fabsq (e[k])) {
          e[k] = g[k];
        }
      }
      if (ko) {
        printf ("%Qa", x);
        for (k = 0; k <= L; k++) {
          printf (" %Qa", g[k]);
        }
        printf ("\n");
      }
    }
  }
  g[0] = 0;
  for (k = 0; k <= L; k++) {
    if (fabsq (e[k]) > fabs (g[0])) {
      g[0] = e[k];
    }
  }
  for (k = 0; k <= L; k++) {
    fprintf (stderr, "# %2d: e = %13.4Qa  log2(e) = %7.2Qf\n", k, e[k], log2q (fabsq (e[k])));
  }
    fprintf (stderr, "#     e = %13.4Qa  log2(e) = %7.2Qf\n", g[0], log2q (fabsq (g[0])));
  return 0;
}

