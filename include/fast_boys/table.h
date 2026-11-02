#ifndef FAST_BOYS_TABLE_H_
#define FAST_BOYS_TABLE_H_
#include "fast_boys/boys_types.h"
// Include the selected model's data.h in the initialization translation unit.
// BoysTable<Model> owns immutable exact words and has a constexpr constructor.
// Do not create/copy this large owning object in a GPU thread or on a small
// stack.
#endif
