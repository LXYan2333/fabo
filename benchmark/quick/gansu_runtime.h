// QUICK-only setup; the GANSU table lives in global memory, as upstream.
static __constant__ const double* fabo_gansu_table;

static void fabo_gansu_init() {
    constexpr size_t count = 30720;
    const char* path = std::getenv("FABO_GANSU_TABLE");
    FILE* file = path ? std::fopen(path, "rb") : nullptr;
    if (!file) { std::fprintf(stderr, "FABO_GANSU_TABLE is required\n"); std::exit(2); }
    double* host = new double[count];
    const bool valid = std::fread(host, sizeof(double), count, file) == count && std::fgetc(file) == EOF;
    if (std::fclose(file) != 0 || !valid) { std::fprintf(stderr, "Invalid GANSU table\n"); std::exit(2); }
    double* device;
    fabo_check(cudaMalloc(&device, count * sizeof(double)));
    fabo_check(cudaMemcpy(device, host, count * sizeof(double), cudaMemcpyHostToDevice));
    fabo_check(cudaMemcpyToSymbol(fabo_gansu_table, &device, sizeof(device)));
    delete[] host;
    // One process-lifetime allocation before any timed SCF work, no per-call transfer.
}
