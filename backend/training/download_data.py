"""Download original LIAR distribution; no redistribution of the raw data."""
import argparse
import hashlib
import io
from pathlib import Path
import urllib.request
import zipfile

SOURCE = 'https://www.cs.ucsb.edu/~william/data/liar_dataset.zip'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', help='Use a previously downloaded official archive')
    args = parser.parse_args()
    raw = Path(__file__).resolve().parents[2] / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    if args.archive:
        data = Path(args.archive).read_bytes()
    else:
        with urllib.request.urlopen(SOURCE, timeout=40) as response:
            data = response.read(10 * 1024 * 1024)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in ['train.tsv', 'valid.tsv', 'test.tsv']:
            (raw / name).write_bytes(archive.read(name))
        if 'README' in archive.namelist():
            (raw / 'LIAR_README').write_bytes(archive.read('README'))
    (raw / 'archive.sha256').write_text(hashlib.sha256(data).hexdigest() + '\n')
    print(f'Original LIAR splits extracted to {raw}. Review dataset terms before any redistribution.')

if __name__ == '__main__':
    main()
