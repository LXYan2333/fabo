"""Copy only owned metadata files, atomically, without compute-node utilities."""
from pathlib import Path
import shutil
import sys


def copy_metadata(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ('identity.json', 'records.jsonl', 'summary.json'):
        path = source/name
        if not path.is_file():
            continue
        temporary = destination/(name+'.publishing')
        shutil.copyfile(path, temporary)
        temporary.replace(destination/name)


if __name__ == '__main__':
    copy_metadata(*sys.argv[1:])
