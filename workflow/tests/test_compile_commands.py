import json

import pytest

from workflow.scripts import generate_compile_commands as module


@pytest.fixture
def layout(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    for name in ('tools/clangd/simd.cc', 'tools/clangd/cuda.cu',
                 'include/fast_boys/simd.h', 'include/fast_boys/cuda.cuh'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('// test\n')
    highway = tmp_path / 'highway'
    (highway / 'hwy').mkdir(parents=True)
    (highway / 'hwy/highway.h').touch()
    cuda = tmp_path / 'cuda'
    headers = cuda / 'targets/x86_64-linux/include'
    headers.mkdir(parents=True)
    (headers / 'cuda_runtime.h').touch()
    (headers / 'curand_mtgp32_kernel.h').touch()
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module.shutil, 'which', lambda _: '/usr/bin/clang++-22')
    return root, highway, cuda


def test_command_languages_and_paths(layout):
    root, highway, cuda = layout
    path, count = module.generate(highway, cuda, cpu_arch='haswell')
    assert path == root / 'build/compile_commands.json'
    rows = json.loads(path.read_text())
    assert count == len(rows) == 4
    for row in rows:
        args = row['arguments']
        assert row['directory'] == str(root)
        assert '-I' + str(root / 'include') in args
        assert args[-1] == row['file']
        gpu = row['file'].endswith(('.cu', '.cuh'))
        assert args[args.index('-x') + 1] == ('cuda' if gpu else 'c++')
        assert ('--cuda-device-only' in args) == gpu
        if gpu:
            assert '-I' + str(cuda / 'targets/x86_64-linux/include') in args
        else:
            assert '-DHWY_COMPILE_ONLY_STATIC' in args
            assert '-march=haswell' in args


def test_missing_curand_fails_before_database_replacement(layout):
    root, highway, cuda = layout
    path, _ = module.generate(highway, cuda)
    previous = path.read_bytes()
    (cuda / 'targets/x86_64-linux/include/curand_mtgp32_kernel.h').unlink()
    with pytest.raises(ValueError, match='cuRAND'):
        module.generate(highway, cuda)
    assert path.read_bytes() == previous
