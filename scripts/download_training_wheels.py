"""Fetch three pinned large wheels from official PyPI with bounded range requests.

Separate download directory; never modifies a Python environment. Full official
SHA256 is required before publishing a wheel to the local wheel directory.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / '.runtime/training-wheels'
PACKAGES = [('bitsandbytes', '0.50.2', 'py3-none-win_amd64.whl'),
            ('transformers', '5.18.0', 'py3-none-any.whl'),
            ('numpy', '2.3.5', 'cp311-cp311-win_amd64.whl')]


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    with httpx.Client(timeout=60, follow_redirects=True,
                      limits=httpx.Limits(max_connections=6)) as client:
        jobs = []
        for name, version, suffix in PACKAGES:
            response = client.get(f'https://pypi.org/pypi/{name}/{version}/json')
            response.raise_for_status()
            metadata = response.json()
            candidates = [f for f in metadata['urls'] if f['filename'].endswith(suffix)]
            if len(candidates) != 1:
                raise ValueError('Ambiguous wheel: ' + name)
            item = candidates[0]
            if urlsplit(item['url']).hostname != 'files.pythonhosted.org':
                raise ValueError('Unexpected artifact host')
            records.append(item)
            parts = DESTINATION / (item['filename'] + '.parts')
            parts.mkdir(exist_ok=True)
            for index, start in enumerate(range(0, item['size'], 1024 * 1024)):
                end = min(start + 1024 * 1024, item['size']) - 1
                jobs.append((item, parts / f'{index:04d}', start, end))

        def fetch(job):
            item, path, start, end = job
            expected = end - start + 1
            if path.exists() and path.stat().st_size == expected:
                return
            for attempt in range(3):
                try:
                    response = client.get(item['url'], headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
                    if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{item["size"]}':
                        raise ValueError('Server did not return the requested range')
                    if len(response.content) != expected:
                        raise ValueError('Incomplete range')
                    temporary = path.with_suffix('.partial')
                    temporary.write_bytes(response.content)
                    temporary.replace(path)
                    return
                except (httpx.HTTPError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(1)

        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(fetch, job) for job in jobs]
            for count, future in enumerate(as_completed(futures), 1):
                future.result()
                if count % 6 == 0 or count == len(jobs):
                    print(json.dumps({'completed_chunks': count, 'total_chunks': len(jobs)}), flush=True)

    for item in records:
        destination = DESTINATION / item['filename']
        parts = DESTINATION / (item['filename'] + '.parts')
        digest = hashlib.sha256()
        temporary = destination.with_suffix('.partial')
        with temporary.open('wb') as file:
            for path in sorted(parts.iterdir()):
                if not path.name.isdigit():
                    continue
                data = path.read_bytes()
                file.write(data)
                digest.update(data)
        if temporary.stat().st_size != item['size'] or digest.hexdigest() != item['digests']['sha256']:
            raise ValueError('Wheel SHA256 mismatch: ' + item['filename'])
        temporary.replace(destination)
        print(json.dumps({'verified': item['filename'], 'sha256': digest.hexdigest()}), flush=True)
    (DESTINATION / 'manifest.json').write_text(json.dumps(records, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
