"""Extend verified CPU reference comparisons from saved matrices; no NWChem run."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

if __package__:
    from .molecular_metrics import MatrixMetrics, DEFINITION
    from .record_manifest import write_manifest
else:
    from molecular_metrics import MatrixMetrics, DEFINITION
    from record_manifest import write_manifest


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_matrix(folder, name):
    complete = json.loads((folder / 'complete.json').read_text())
    path = folder / (name + '.bin')
    expected = complete[name + '.bin']
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Matrix checksum mismatch')
    return np.frombuffer(data, dtype='<f8'), expected


def run(root, output):
    original = root / 'reference-summary.json'
    summary = json.loads(original.read_text())
    rows = []
    for row in summary['results']:
        if not row['bitwise_reproducible']:
            raise ValueError('Original repeatability check failed')
        if row['backend'] == 'reference':
            continue
        base = root / 'measurements' / row['case']['id']
        result = dict(case=row['case'], backend=row['backend'],
                      energy_difference=row['energy_difference'], bitwise_reproducible=True,
                      matrix_sha256={})
        for name, key in (('fock', 'fock'), ('density-out', 'density')):
            reference, rhash = read_matrix(base / '0-reference', name)
            values, vhash = read_matrix(base / ('0-' + row['backend']), name)
            if reference.shape != values.shape:
                raise ValueError('Matrix size mismatch')
            metrics = MatrixMetrics()
            metrics.add(values - reference)
            result[key] = metrics.finish()
            if result[key]['max_absolute'] != row[name]['max_absolute']:
                raise ValueError('Maximum differs from completed reference summary')
            result['matrix_sha256'][name] = dict(reference=rhash, backend=vhash)
        rows.append(result)
        print('Completed', row['case']['id'], row['backend'], flush=True)
    report = dict(schema=2, reference_summary_sha256=sha(original),
                  generator_sha256=sha(Path(__file__)),
                  metrics_source_sha256=sha(Path(__file__).with_name('molecular_metrics.py')),
                  metric_definition=DEFINITION, numpy_version=np.__version__,
                  longdouble_bits=np.finfo(np.longdouble).nmant + 1, results=rows)
    with output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    write_manifest(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.run, args.output)
