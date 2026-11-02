#ifndef FAST_BOYS_BOYS_TYPES_H_
#define FAST_BOYS_BOYS_TYPES_H_
#include "fast_boys/detail/config.h"
#include <cstddef>
#include <cstdint>
namespace fast_boys {
enum class ErrorMetric { Absolute, Relative, Ulp };
// The owner must keep this matching allocation alive throughout evaluation.
// On CUDA the pointer must be a device-accessible allocation, aligned to 8
// bytes.
template <class Model> class TableView {
public:
  FAST_BOYS_HD static constexpr TableView from_pointer(const std::uint64_t *p) {
    return TableView(p);
  }
  FAST_BOYS_HD constexpr const std::uint64_t *data() const { return data_; }

private:
  FAST_BOYS_HD explicit constexpr TableView(const std::uint64_t *p)
      : data_(p) {}
  const std::uint64_t *data_;
};
// Specializations with literal initializers live in generated data.h files.
template <class Model> struct BoysTable;
} // namespace fast_boys
#endif
