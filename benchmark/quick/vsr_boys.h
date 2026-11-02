// CUDA port of the supplied VSR Algorithm 1 / minimax.c, not an upstream CUDA implementation.
// See third_party/vsr/README.md for provenance, source correction and port choices.
#ifndef FABO_VSR_BOYS_H
#define FABO_VSR_BOYS_H
#include "vsr_coefficients.h"

// QUICK supplies finite nonnegative x and 0 <= maximum <= 12. Output is strided
// by the integral kernel's lane count. No temporary sequence or packing pass.
__device__ static __forceinline__ void FaboVsrBoys(
    int maximum, double x, double* __restrict__ output, size_t stride) {
    if (x < fabo_vsr_x_0) {
        double value = FaboVsrSeed(maximum, x);
        output[maximum * stride] = value;
        if (maximum == 0) return;  // No exp is needed to return just F0.
        const double half_exp = 0.5 * exp(-x);
        // A fallthrough sequence exposes each constant divisor, while storing
        // only requested orders. It does not clone the surrounding ERI kernel.
#define FABO_VSR_DOWN(N) case N: value = (x * value + half_exp) / (N - 0.5); output[(N - 1) * stride] = value;
        switch (maximum) {
            FABO_VSR_DOWN(12) // fall through
            FABO_VSR_DOWN(11) // fall through
            FABO_VSR_DOWN(10) // fall through
            FABO_VSR_DOWN(9)  // fall through
            FABO_VSR_DOWN(8)  // fall through
            FABO_VSR_DOWN(7)  // fall through
            FABO_VSR_DOWN(6)  // fall through
            FABO_VSR_DOWN(5)  // fall through
            FABO_VSR_DOWN(4)  // fall through
            FABO_VSR_DOWN(3)  // fall through
            FABO_VSR_DOWN(2)  // fall through
            FABO_VSR_DOWN(1)
            default: break;
        }
#undef FABO_VSR_DOWN
    } else if (x < fabo_vsr_x_1) {
        double value = FaboVsrMiddle(x);
        output[0] = value;
        if (maximum == 0) return;
        const double half_exp = 0.5 * exp(-x);
        for (int l=1; l<=maximum; ++l) {
            value = ((l - 0.5) * value - half_exp) / x;
            output[l * stride] = value;
        }
    } else {
        double value = fabo_vsr_halfsqrtpi / sqrt(x);
        output[0] = value;
        for (int l=1; l<=maximum; ++l) {
            value = (l - 0.5) * value / x;
            output[l * stride] = value;
        }
    }
}
#endif
