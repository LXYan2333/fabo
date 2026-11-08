import pytest
from .core import reduce_windows,GATES

def shards(bits,size):
    out=[]
    for start in range(0,len(bits),size):
        end=min(start+size,len(bits));bad=[i+1 for i in range(start,end) if not bits[i]]
        out.append(dict(protocol='upward-window-v1',begin=start+1,end=end+1,rows=[dict(N=n,gate=g,first_fail=min(bad) if bad else -1,last_fail=max(bad) if bad else -1) for n in range(1,13) for g in GATES]))
    return out

@pytest.mark.parametrize('pattern',[0,1,5,17,53,127,1023,4095])
@pytest.mark.parametrize('size',[1,2,3])
def test_oracle(pattern,size):
    bits=[bool(pattern&(1<<i)) for i in range(12)]
    expected=next((i+1 for i in range(9) if all(bits[i:i+4])),None)
    result=reduce_windows(shards(bits,size),final=12,window=4)
    assert all(r['start_index']==expected for r in result)

def test_invalid():
    ds=shards([True]*12,3)
    with pytest.raises(ValueError):reduce_windows(ds[1:],12,4)
    with pytest.raises(ValueError):reduce_windows(ds+ds,12,4)
    with pytest.raises(ValueError):reduce_windows(ds,12,3)
    ds[0]['rows'].pop()
    with pytest.raises(ValueError):reduce_windows(ds,12,4)

def test_output_gate_separation():
    ds=shards([True]*12,3)
    for d in ds:
        d['rows'][-1].update(first_fail=d['begin'],last_fail=d['end']-1)
    rows=reduce_windows(ds,12,4)
    assert rows[-1]['start_index'] is None
    assert all(r['start_index']==1 for r in rows[:-1])
