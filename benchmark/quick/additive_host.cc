// Only this host translation unit parses/owns the large coefficient arrays.
#include "fast_boys/models/data_0_4.h"
#ifdef ENABLEF
#include "fast_boys/models/data_0_12.h"
#else
#include "fast_boys/models/data_0_8.h"
#endif
#include "fast_boys/models/tail_data.h"
#include "fast_boys/selected.h"

template <class Model>
static const std::uint64_t *host_words(std::size_t *bytes) {
  static constexpr fast_boys::BoysTable<Model> table{};
  *bytes = Model::table_bytes;
  return table.data();
}

extern "C" const std::uint64_t *fabo_quick_host_table(int last,
                                                    std::size_t *bytes) {
  switch (last) {
  case 4:
    return host_words<fast_boys::selected::Model<4>>(bytes);
#ifdef ENABLEF
  case 12:
    return host_words<fast_boys::selected::Model<12>>(bytes);
#else
  case 8:
    return host_words<fast_boys::selected::Model<8>>(bytes);
#endif
  case -1:
    return host_words<fast_boys::selected::Tail>(bytes);
  default:
    *bytes = 0;
    return nullptr;
  }
}
