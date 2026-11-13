import json
from pathlib import Path
import shutil

import pytest

from workflow.scripts.format_public_headers import format_headers, format_source, formatter_identity


@pytest.fixture
def formatter():
    tool = 'clang-format-22'
    if not shutil.which(tool):
        pytest.skip('clang-format-22 unavailable')
    return tool


def test_format_excludes_payload_and_is_repeatable(tmp_path, formatter):
    root = tmp_path / 'fast_boys/models/example'
    root.mkdir(parents=True)
    payload = root / 'data.h'
    raw = b'// Preserve payload bytes exactly\nint  data[]={1,2,3};\n'
    payload.write_bytes(raw)
    source = '#include "z.h"\n#include "a.h"\nint  f( int x ){return x+1;}\n'
    header = root / 'model.h'
    cuda = root / 'helper.cuh'
    header.write_text(source)
    cuda.write_text(source)
    public = tmp_path / 'fast_boys/models/data_0_0.h'
    public.write_text(source)
    manifest = dict(files={str(header.relative_to(tmp_path)): 'old'}, sources={})
    manifest_path = tmp_path / 'simd-manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    paths = format_headers(tmp_path, formatter)
    assert set(paths) == {header, cuda, public}
    assert payload.read_bytes() == raw
    assert header.read_text() == cuda.read_text() == public.read_text() == format_source(source, formatter)
    assert header.read_text().startswith('#include "z.h"\n#include "a.h"')
    saved = manifest_path.read_bytes()
    assert json.loads(saved)['formatting'] == formatter_identity(formatter)
    format_headers(tmp_path, formatter)
    assert manifest_path.read_bytes() == saved
    assert payload.read_bytes() == raw


def test_refuse_header_symlink(tmp_path, formatter):
    root = tmp_path / 'fast_boys'
    root.mkdir()
    other = tmp_path / 'other.h'
    other.write_text('int  x;\n')
    (root / 'alias.h').symlink_to(other)
    with pytest.raises(ValueError, match='symlink'):
        format_headers(tmp_path, formatter)
    assert other.read_text() == 'int  x;\n'
