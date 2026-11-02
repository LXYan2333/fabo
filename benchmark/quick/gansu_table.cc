// Serialize the original release's decimal literals with the host C++ compiler.
// No refitting, truncation, table regeneration, or change to the upstream layout.
#include <cstdio>
#include <cmath>
using real_t = double;
#include "src/boys/boys_30720.h"
int main(int argc, char** argv) {
    if (argc != 2) return 2;
    static_assert(sizeof(gansu::h_boys_grid) == 30720 * sizeof(double));
    for (double x : gansu::h_boys_grid) if (!std::isfinite(x) || x <= 0) return 3;
    FILE* f = std::fopen(argv[1], "wb");
    if (!f) return 4;
    const bool ok = std::fwrite(gansu::h_boys_grid, sizeof(double), 30720, f) == 30720;
    return std::fclose(f) == 0 && ok ? 0 : 5;
}
