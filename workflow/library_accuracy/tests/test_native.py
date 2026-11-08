"""Opt-in native tests: FABO_ACCURACY_SCANNER and FABO_ACCURACY_REFERENCE."""
import json
import os
from pathlib import Path
import subprocess
import pytest

@pytest.fixture
def native():
    scanner=os.environ.get('FABO_ACCURACY_SCANNER')
    table=os.environ.get('FABO_ACCURACY_REFERENCE')
    if not scanner or not table:pytest.skip('set paths to the strict collector and reference table')
    return scanner,table

def test_reference_enclosures(native):
    scanner,table=native
    subprocess.run([scanner,'--check-reference',table],check=True)

@pytest.mark.parametrize('value,invalid,ulp',[('1.0',0,0),('0x1.0000000000001p0',0,1),('std::nan("")',1,None)])
def test_true_value_metrics(native,tmp_path,value,invalid,ulp):
    scanner,table=native
    src=tmp_path/'test.cc';lib=tmp_path/'test.so'
    src.write_text('#include <cstddef>\n#include <cmath>\nextern "C" void boys_accuracy(size_t n,const double*,double* out){for(size_t i=0;i<n;++i)out[i]='+value+';}\n')
    subprocess.run(['g++','-std=c++17','-fPIC','-shared',str(src),'-o',str(lib)],check=True)
    manifest=tmp_path/'adapters.txt';manifest.write_text(f'"test" "{lib}" 0\n')
    out=tmp_path/'out.json'
    subprocess.run([scanner,'scan',table,str(manifest),'0','1','1000000','7',str(out)],check=True)
    rows=json.loads(out.read_text())['rows'];assert all(r['invalid']==invalid for r in rows)
    if ulp is not None:
        r=next(r for r in rows if r['metric']=='ulp')
        assert float(r['max_lo'])<=ulp<=float(r['max_hi'])
        assert float(r['max_hi'])-float(r['max_lo'])<1e-12
