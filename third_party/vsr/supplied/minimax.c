#include "constants.h"
#include <math.h>
#include <stddef.h>

void minimax(const size_t N,
             const double*__restrict x,
             const double*__restrict y,
             const double*__restrict c,
             double*__restrict z) {
  static const double
    a0 =  2.53544601714217041E+07,
    a1 = -8.48258198675025220E+06,
    a2 =  1.30979027926005474E+06,
    a3 = -1.21399979536359709E+05,
    a4 =  7.36540787890653295E+03,
    a5 = -2.98819753533120450E+02,
    a6 =  7.90065371972972126E+00,
    a7 = -1.24223182966353277E-01,
    a8 =  8.87602463343472957E-04;
  static const double
    b0 = 6.33861504285287492E+08,
    b1 = 3.74844250615203673E+08,
    b2 = 1.06606600921230004E+08,
    b3 = 1.93004584684968576E+07,
    b4 = 2.47784305031495735E+06,
    b5 = 2.37294882532379883E+05,
    b6 = 1.72900919399835697E+04,
    b7 = 9.53839898338405204E+02,
    b8 = 3.77540526654878690E+01;
  static const double
    c0 = 5.74537531702047552E+7,
    c1 = 2.73330925890901898E+6,
    c2 = 7.52922255805293133E+04,
    c3 = 2.33846894861346960E+05,
    c4 = 8.34841284469484906E+03,
    c5 = 3.90892739018191431E+01;
  static const double
    d0 =  4.79893571439451030E+07,
    d1 =  3.04808499107506708E+07,
    d2 = -1.66693114610725015E+06,
    d3 =  5.63505368535215625E+05,
    d4 =  6.39702496081641495E+04,
    d5 =  8.53693546919731980E+02;
    
  #pragma acc parallel loop copyin(x[0:N], c[0:k+1]) copyout(z[0:N])
  for (size_t i = 0; i < N; i++) {
    z[i] = 0;
    for (size_t j = 0; j < N; j++) {
      double xx = x[i]+x[j];
      double w;
      double expx = 0.5*exp(-xx);
      if (xx < x_0) {
        // Downwards recursion
        double F = ((((((((a8*xx+a7)*xx+a6)*xx+a5)*xx+a4)*xx+a3)*xx+a2)*xx+a1)*xx+a0)/
                   ((((((((((xx+b8))*xx+b7)*xx+b6)*xx+b5)*xx+b4)*xx+b3)*xx+b2)*xx+b1)*xx+b0);
        w = c[k]*F;
        for (int l = k-1; l >= 0; l--) {
          F = (xx*F+expx)/(l+0.5);
          w += c[l]*F;
        }
      } else {
        // Upwards recursion
        double F;
        if (xx < x_1) {
          F = (((((c5*xx+c4)*xx+c3)*xx+c2)*xx+c1)*xx+c0)/
              ((((((xx+d5)*xx+d4)*xx+d3)*xx+d2)*xx+d1)*xx+d0);
          w = c[0]*F;
          for (int l = 1; l <= k; l++) {
            F = ((l-0.5)*F-expx)/xx;
            w += c[l]*F;
          }
        }
        else {
          F = halfsqrtpi/sqrt(xx);
          w = c[0]*F;
          for (int l = 1; l <= k; l++) {
            F = (l-0.5)*F/xx;
            w += c[l]*F;
          }
        }
      }
      z[i] += y[j]*w;
    }
  }
}
