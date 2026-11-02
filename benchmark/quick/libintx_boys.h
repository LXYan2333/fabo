// Adapted from LibintX boys/gpu/chebyshev.h and boys/asymptotic.h.
// Copyright (C) 2020-2023 Andrey Asadchev and Edward F. Valeev.
// LGPL-3.0; see third_party/libintx/LICENSE and COPYING.
// Runtime-order sequence adapter: write directly to QUICK's strided destination.
// No temporary sequence or per-order evaluator calls; omit the initial +0.
// Contract: output storage must not overlap the read-only coefficient table.
#ifndef FABO_LIBINTX_BOYS_H
#define FABO_LIBINTX_BOYS_H

__device__ static __forceinline__ void FaboLibintxBoys(
    int maximum, double x, double* __restrict__ output, size_t stride,
    const double* __restrict__ table) {
    constexpr int Order = 7;
    constexpr int M = 13;
    // QUICK's supported s/p/d/f families request orders 0..12. Keep the
    // runtime order loop shared; do not specialize the surrounding integrals.
    constexpr int Segments = 117 * 7;
    constexpr double Delta = double(117) / Segments;
    const double x_over_delta = x * (1.0 / Delta);
    const int k = int(x_over_delta);
    if (k >= Segments) {
        // LibintX's sequence overload uses sqrt(1/x), unlike its scalar
        // overload, which explicitly calls rsqrt(x). Preserve that choice.
        const double one_over_x = 1 / x;
        double Fm = 0.88622692545275801365 * sqrt(one_over_x);
        output[0] = Fm;
        for (int i = 1; i <= maximum; ++i) {
            Fm = Fm * (i - 0.5) * one_over_x;
            output[i * stride] = Fm;
        }
        return;
    }
    const double xd = x_over_delta - (double)k - 0.5;
    const double* p = table + k * M * (Order + 1);
    for (int j = 0; j <= maximum; ++j) {
        // The generated constant coefficients are positive normal doubles;
        // loading p[0] directly is bitwise equivalent to 0 + 1*p[0].
        double fj = p[0];
        double xi = xd;
        for (int i = 1; i <= Order; ++i) {
            fj += xi * p[i];
            xi *= xd;
        }
        output[j * stride] = fj;
        p += Order + 1;
    }
}
#endif
