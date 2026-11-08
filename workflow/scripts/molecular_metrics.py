"""Streaming elementwise molecular-matrix differences (all n*n entries)."""

import numpy as np


class MatrixMetrics:
    def __init__(self):
        self.count = 0
        self.max_absolute = 0.0
        self.absolute_sum = np.longdouble(0)

    def add(self, delta):
        absolute = np.abs(delta).astype(np.longdouble)
        if not np.isfinite(absolute).all():
            raise ValueError('Nonfinite matrix or difference')
        self.count += absolute.size
        self.max_absolute = max(self.max_absolute, float(np.max(absolute)))
        self.absolute_sum += np.sum(absolute, dtype=np.longdouble)

    def finish(self):
        if not self.count:
            raise ValueError('Empty matrix')
        return dict(max_absolute=self.max_absolute,
                    mean_absolute=float(self.absolute_sum / self.count),
                    elements=self.count)


DEFINITION = dict(averaging='equal weight to every n*n entry, including both symmetric halves',
                  accumulation='NumPy longdouble for absolute-error sums; binary64 exported statistics')
