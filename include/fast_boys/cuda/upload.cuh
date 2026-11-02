#ifndef FAST_BOYS_CUDA_UPLOAD_CUH_
#define FAST_BOYS_CUDA_UPLOAD_CUH_
#include "fast_boys/table.h"
#include <cuda_runtime_api.h>
#include <stdexcept>
#include <utility>
namespace fast_boys::cuda {
// Optional host-only owner. Upload synchronously once, outside timed kernels.
// Destroy on the same current CUDA device, after all consumers have finished.
template <class Model> class DeviceTable {
public:
  explicit DeviceTable(const BoysTable<Model> &host) {
    void *allocation = nullptr;
    check(cudaMalloc(&allocation, Model::table_bytes));
    data_ = static_cast<std::uint64_t *>(allocation);
    const auto status = cudaMemcpy(data_, host.data(), Model::table_bytes,
                                   cudaMemcpyHostToDevice);
    if (status != cudaSuccess) {
      cudaFree(data_);
      data_ = nullptr;
      check(status);
    }
  }
  ~DeviceTable() {
    if (data_)
      cudaFree(data_);
  }
  DeviceTable(const DeviceTable &) = delete;
  DeviceTable &operator=(const DeviceTable &) = delete;
  DeviceTable(DeviceTable &&other) noexcept
      : data_(std::exchange(other.data_, nullptr)) {}
  DeviceTable &operator=(DeviceTable &&) = delete;
  TableView<Model> view() const {
    return TableView<Model>::from_pointer(data_);
  }

private:
  static void check(cudaError_t status) {
    if (status != cudaSuccess)
      throw std::runtime_error(cudaGetErrorString(status));
  }
  std::uint64_t *data_ = nullptr;
};
} // namespace fast_boys::cuda
#endif
