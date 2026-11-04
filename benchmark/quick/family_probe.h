// Diagnostic-only family statistics. Never include in a timing evaluator.
#ifndef FABO_FAMILY_PROBE_H
#define FABO_FAMILY_PROBE_H
#include <cstdio>
#include <cstdlib>
#include "fabo_warp_config.h"
#ifndef FABO_FAMILY_SPD_REQUEST_LIMIT
#define FABO_FAMILY_SPD_REQUEST_LIMIT 8
#endif
static_assert(FABO_FAMILY_SPD_REQUEST_LIMIT == 8 || FABO_FAMILY_SPD_REQUEST_LIMIT == 12,
              "invalid SPD diagnostic request capacity");

struct FaboFamilyCounters {
  unsigned long long requests[3][3][13][33];
  unsigned long long minimum[3][3][13][13];
  unsigned long long distinct[3][3][13][14];
  unsigned long long lanes[3][3][13][13];
  unsigned long long histogram[3][FABO_HIST_EDGES + 3];
  unsigned long long invalid[3][13][2];
  unsigned long long ranks[3][13][2][4][FABO_THRESHOLDS + 1];
  // Valid whole cohorts: [active][bounded], tail = active - bounded.
  unsigned long long split[3][33][33];
  unsigned long long invalid_order;
};
static __device__ FaboFamilyCounters fabo_family_counters;
static __constant__ int fabo_family_enabled;

// Operations: minimum, maximum, bitwise OR. Sparse masks are supported.
template<int Op>
__device__ __forceinline__ unsigned FaboFamilyReduce(unsigned mask, unsigned v) {
#if __CUDA_ARCH__ >= 800
  if (Op == 0) return __reduce_min_sync(mask, v);
  if (Op == 1) return __reduce_max_sync(mask, v);
  return __reduce_or_sync(mask, v);
#else
  unsigned result = v;
  for (unsigned pending = mask; pending; pending &= pending - 1) {
    const unsigned other = __shfl_sync(mask, v, __ffs(pending) - 1);
    if (Op == 0) result = result < other ? result : other;
    if (Op == 1) result = result > other ? result : other;
    if (Op == 2) result |= other;
  }
  return result;
#endif
}

__device__ __forceinline__ unsigned FaboFamilyBound(const double* table, unsigned size,
                                                    double x, bool upper) {
  unsigned lo = 0, hi = size;
  while (lo < hi) {
    const unsigned mid = (lo + hi) / 2;
    if (table[mid] < x || (upper && table[mid] == x)) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

// The mask is captured by the caller before argument-dependent branches.
template<int Family>
__device__ __forceinline__ void FaboFamilyObserveMask(unsigned whole, int order, double x) {
  static_assert(Family == 4 || Family == 8 || Family == 12, "unsupported QUICK family");
  constexpr int family = Family / 4 - 1;
  constexpr int limit = Family == 8 ? FABO_FAMILY_SPD_REQUEST_LIMIT : Family;
  const unsigned lane = (threadIdx.x + blockDim.x * (threadIdx.y + blockDim.y * threadIdx.z)) & 31;
  const unsigned leader = __ffs(whole) - 1;
  const unsigned bad_order = __ballot_sync(whole, order < 0 || order > limit);
  if (bad_order) {
    if (lane == unsigned(__ffs(bad_order) - 1) &&
        atomicAdd(&fabo_family_counters.invalid_order, 1ULL) == 0)
      printf("out-of-family Boys request: kernel=%d order=%d limit=%d\n", Family, order, limit);
    return;
  }
  const unsigned long long bits = __double_as_longlong(x);
  const bool zero = (bits & 0x7fffffffffffffffULL) == 0;
  const bool valid = zero || ((bits >> 63) == 0 && (bits & 0x7ff0000000000000ULL) != 0x7ff0000000000000ULL);
  const unsigned bad = __ballot_sync(whole, !valid);
  const unsigned bounded = __ballot_sync(whole, valid && x <= FABO_FAMILY_DOMAIN_END);
  const unsigned tail = whole & ~(bounded | bad);
  const unsigned bin = !valid ? FABO_HIST_EDGES + 2 : zero ? 0 :
      1 + FaboFamilyBound(fabo_hist_edges, FABO_HIST_EDGES, x, true);
  const unsigned same_bin = __match_any_sync(whole, bin);
  if (lane == unsigned(__ffs(same_bin) - 1))
    atomicAdd(&fabo_family_counters.histogram[family][bin], static_cast<unsigned long long>(__popc(same_bin)));
  if (lane == leader && !bad)
    atomicAdd(&fabo_family_counters.split[family][__popc(whole)][__popc(bounded)], 1ULL);

  for (int scope = 0; scope < 3; ++scope) {
    const unsigned mask = scope == 0 ? whole : scope == 1 ? bounded : tail;
    if (!(mask & (1U << lane))) continue;
    const unsigned maximum = FaboFamilyReduce<1>(mask, order);
    const unsigned minimum = FaboFamilyReduce<0>(mask, order);
    const unsigned distinct = __popc(FaboFamilyReduce<2>(mask, 1U << order));
    const unsigned same_order = __match_any_sync(mask, order);
    if (lane == unsigned(__ffs(same_order) - 1))
      atomicAdd(&fabo_family_counters.lanes[family][scope][maximum][order],
                static_cast<unsigned long long>(__popc(same_order)));
    if (lane == unsigned(__ffs(mask) - 1)) {
      atomicAdd(&fabo_family_counters.requests[family][scope][maximum][__popc(mask)], 1ULL);
      atomicAdd(&fabo_family_counters.minimum[family][scope][maximum][minimum], 1ULL);
      atomicAdd(&fabo_family_counters.distinct[family][scope][maximum][distinct], 1ULL);
    }
    if (scope != 0) continue;
    const unsigned full = __popc(whole) == 32;
    if (bad) {
      if (lane == leader) atomicAdd(&fabo_family_counters.invalid[family][maximum][full], 1ULL);
      continue;
    }
    const unsigned lower = FaboFamilyBound(fabo_thresholds, FABO_THRESHOLDS, x, false);
    const unsigned upper = FaboFamilyBound(fabo_thresholds, FABO_THRESHOLDS, x, true);
    const unsigned min_lower = FaboFamilyReduce<0>(whole, lower);
    const unsigned max_lower = FaboFamilyReduce<1>(whole, lower);
    const unsigned min_upper = FaboFamilyReduce<0>(whole, upper);
    const unsigned max_upper = FaboFamilyReduce<1>(whole, upper);
    if (lane == leader) {
      atomicAdd(&fabo_family_counters.ranks[family][maximum][full][0][min_lower], 1ULL);
      atomicAdd(&fabo_family_counters.ranks[family][maximum][full][1][max_lower], 1ULL);
      atomicAdd(&fabo_family_counters.ranks[family][maximum][full][2][min_upper], 1ULL);
      atomicAdd(&fabo_family_counters.ranks[family][maximum][full][3][max_upper], 1ULL);
    }
  }
}

template<int Family>
__device__ __forceinline__ void FaboObserveFamily(int order, double x) {
  if (!fabo_family_enabled) return;
  const unsigned mask = __activemask();
  FaboFamilyObserveMask<Family>(mask, order, x);
}

static void FaboFamilyCheck(cudaError_t status) {
  if (status != cudaSuccess) {
    std::fprintf(stderr, "family diagnostic: %s\n", cudaGetErrorString(status));
    std::exit(2);
  }
}
static void FaboFamilyBegin(bool enabled) {
  void* address;
  FaboFamilyCheck(cudaGetSymbolAddress(&address, fabo_family_counters));
  FaboFamilyCheck(cudaMemset(address, 0, sizeof(FaboFamilyCounters)));
  const int flag = enabled;
  FaboFamilyCheck(cudaMemcpyToSymbol(fabo_family_enabled, &flag, sizeof(flag)));
}
static void FaboFamilyWrite(FILE* f, unsigned long long& rows, const char* kind, int family,
                            const char* scope, int maximum, int index, int aux, unsigned long long count) {
  if (!count) return;
  std::fprintf(f, "%s,%d,%s,%d,%d,%d,%llu\n", kind, family, scope, maximum, index, aux, count);
  ++rows;
}
static void FaboFamilyEnd() {
  FaboFamilyCheck(cudaDeviceSynchronize());
  const int flag = 0;
  FaboFamilyCheck(cudaMemcpyToSymbol(fabo_family_enabled, &flag, sizeof(flag)));
  FaboFamilyCounters* h = new FaboFamilyCounters;
  FaboFamilyCheck(cudaMemcpyFromSymbol(h, fabo_family_counters, sizeof(*h)));
  if (h->invalid_order) { std::fprintf(stderr, "out-of-family Boys request\n"); std::exit(2); }
  FILE* f = std::fopen("family-counters.csv", "w");
  FILE* r = std::fopen("requests.csv", "w");
  if (!f || !r) std::exit(2);
  std::fprintf(f, "kind,family,scope,maximum,index,aux,count\nschema,0,whole,-1,0,0,2\n");
  std::fprintf(r, "family,scope,maximum,active,cohorts\n");
  unsigned long long rows = 0;
  const char* scopes[] = {"whole", "bounded", "tail"};
  const char* ranks[] = {"min_lower", "max_lower", "min_upper", "max_upper"};
  for (int a = 0; a < 3; ++a) {
    const int family = 4 * (a + 1);
    const int limit = family == 8 ? FABO_FAMILY_SPD_REQUEST_LIMIT : family;
    for (int bin = 0; bin < FABO_HIST_EDGES + 3; ++bin)
      FaboFamilyWrite(f, rows, "histogram", family, "whole", -1, bin, 0, h->histogram[a][bin]);
    for (int active = 1; active <= 32; ++active) for (int bounded = 0; bounded <= active; ++bounded)
      FaboFamilyWrite(f, rows, "split", family, "whole", -1, active, bounded, h->split[a][active][bounded]);
    for (int n = 0; n <= limit; ++n) {
      for (int s = 0; s < 3; ++s) {
        for (int active = 1; active <= 32; ++active) {
          const auto count = h->requests[a][s][n][active];
          FaboFamilyWrite(f, rows, "requests", family, scopes[s], n, active, 0, count);
          if (count) std::fprintf(r, "%d,%s,%d,%d,%llu\n", family, scopes[s], n, active, count);
        }
        for (int k = 0; k <= limit; ++k) {
          FaboFamilyWrite(f, rows, "minimum", family, scopes[s], n, k, 0, h->minimum[a][s][n][k]);
          FaboFamilyWrite(f, rows, "lanes", family, scopes[s], n, k, 0, h->lanes[a][s][n][k]);
        }
        for (int k = 1; k <= limit + 1; ++k)
          FaboFamilyWrite(f, rows, "distinct", family, scopes[s], n, k, 0, h->distinct[a][s][n][k]);
      }
      for (int full = 0; full < 2; ++full) {
        FaboFamilyWrite(f, rows, "invalid", family, "whole", n, 0, full, h->invalid[a][n][full]);
        for (int k = 0; k < 4; ++k) for (int rank = 0; rank <= FABO_THRESHOLDS; ++rank)
          FaboFamilyWrite(f, rows, ranks[k], family, "whole", n, rank, full, h->ranks[a][n][full][k][rank]);
      }
    }
  }
  std::fprintf(f, "complete,0,whole,-1,0,0,%llu\n", rows);
  const int failed_f = std::fclose(f), failed_r = std::fclose(r);
  delete h;
  if (failed_f || failed_r) std::exit(2);
}

#ifdef FABO_REQUEST_PROBE
extern "C" void fabo_request_begin_() {
  const char* mode = std::getenv("FABO_REQUEST_PROBE");
  FaboFamilyBegin(mode && mode[0] == '1' && mode[1] == '\0');
}
extern "C" void fabo_request_end_() {
  const char* mode = std::getenv("FABO_REQUEST_PROBE");
  if (mode && mode[0] == '1' && mode[1] == '\0') FaboFamilyEnd();
}
#endif
#ifdef FABO_WARP_PROBE
extern "C" void fabo_warp_begin_() { FaboFamilyBegin(true); }
extern "C" void fabo_warp_end_() { FaboFamilyEnd(); }
#endif
#endif
