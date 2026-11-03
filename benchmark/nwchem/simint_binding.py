"""Generate direct compile-time Boys bindings and patch generated Simint C TUs."""
import json
from pathlib import Path
import re

CALL = re.compile(r'boys_F_split\(\s*(\w+)\s*,\s*F_x\s*,\s*(\d+)\s*\);')


def patch(tree, mode, maximum, binding_directory=None):
    if mode not in ('original', 'fabo', 'libintx', 'vsr', 'laikov'):
        raise ValueError('unknown Simint binding mode')
    tree = Path(tree)
    changes = {}
    seen = set()
    sources = []
    for path in sorted((tree/'simint/ostei').rglob('*.c')):
        text = path.read_text()
        matches = list(CALL.finditer(text))
        if not matches:
            continue
        orders = {int(m[2]) for m in matches}
        if max(orders) > maximum:
            raise ValueError('generated Simint requests an unsupported Boys order')
        seen.update(orders)
        if mode != 'original':
            names={n:json.loads((Path(binding_directory)/f'order-{n}/binding.json').read_text())['namespace'] for n in orders}
            text = CALL.sub(lambda m: f'::{names[int(m[2])]}::evaluate(F_x,{m[1]});', text)
            text = ''.join(f'#include "order-{n}/binding.h"\n' for n in sorted(orders)) + text
        changes[path] = text
        sources.append(str(path.relative_to(tree/'simint')))
    if seen != set(range(maximum+1)):
        raise ValueError(f'generated Boys-order coverage mismatch: {sorted(seen)}')
    cmake = tree/'simint/CMakeLists.txt'
    text = cmake.read_text()
    if 'add_library(simint ' not in text or 'FABO_CPU_BINDING' in text:
        raise ValueError('Simint CMake shape changed/already patched')
    # The properties are added in the target's own directory scope. Preserve
    # vectorization flags when changing generated kernel files from C to C++.
    text += '\n# FABO_CPU_BINDING\nset_source_files_properties(\n' + '\n'.join('  "'+s+'"' for s in sources) + '\n  PROPERTIES LANGUAGE CXX)\n'
    text += ('target_compile_features(simint PRIVATE cxx_std_17)\n'
             'target_include_directories(simint PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")\n'
             'set(FABO_CXX_FLAGS ${SIMINT_C_FLAGS})\n'
             'list(FILTER FABO_CXX_FLAGS EXCLUDE REGEX "^-std=")\n'
             'target_compile_options(simint PRIVATE $<$<COMPILE_LANGUAGE:CXX>:${FABO_CXX_FLAGS}>)\n'
             'target_sources(simint PRIVATE fabo_requests.cc)\n')
    if mode != 'original':
        text += 'target_include_directories(simint PRIVATE "' + Path(binding_directory).resolve().as_posix() + '")\n'
    changes[cmake] = text
    for path, text in changes.items():
        path.write_text(text)
    (tree/'simint/fabo_requests.cc').write_text(
        'extern "C" void fabo_request_begin_() {}\n'
        'extern "C" void fabo_request_end_() {}\n')
    return {'mode': mode, 'orders': sorted(seen), 'cxx_sources': sources}
