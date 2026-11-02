// LibintX coefficient construction, unchanged; not part of the timed path.
#include "libintx/boys/chebyshev.h"
#include <cstdio>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    auto table = libintx::boys::chebyshev_interpolation_table<double>(7, 13, 117, 819);
    constexpr size_t count = 8 * 13 * 819;
    FILE* file = std::fopen(argv[1], "wb");
    if (!file) return 2;
    bool ok = std::fwrite(table.get(), sizeof(double), count, file) == count;
    return std::fclose(file) == 0 && ok ? 0 : 2;
}
