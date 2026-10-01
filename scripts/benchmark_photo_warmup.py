"""Actual photo API cold/preloaded comparison on original synthetic samples."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import httpx
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='photo-warmup-v1')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        parser.error('Invalid run name')
    out = ROOT / '.runtime' / args.name
    out.mkdir(exist_ok=False)
    (out / 'app.py').write_bytes((ROOT / 'app.py').read_bytes())
    (out / 'runner.py').write_bytes(Path(__file__).read_bytes())
    plan = [('notice', 'cold'), ('notice', 'preloaded'), ('event', 'preloaded'), ('event', 'cold')]
    (out / 'plan.json').write_bytes((json.dumps({'app_sha256': app.APP_REVISION, 'cases': plan,
        'scope': 'Two original synthetic images, one cold/preloaded pair each; model unloaded before every run, OS file cache not cleared. Preload elapsed time is reported separately, not erased. Same image and inference path.',
        'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2)+'\n').encode())
    rows = []
    with TestClient(app.app, headers={'X-PaperVoice':'local-ui'}) as client:
        for sample, mode in plan:
            unload = httpx.post(app.OLLAMA + '/api/generate', json={'model':app.MODEL, 'keep_alive':0}, timeout=120)
            unload.raise_for_status()
            resident = httpx.get(app.OLLAMA+'/api/ps', timeout=20).json()
            assert all(m['name'] != app.MODEL for m in resident['models'])
            prep = None
            if mode == 'preloaded':
                r = client.post('/api/warmup'); r.raise_for_status(); prep = r.json()
                assert prep['status'] == 'ready'
            path = ROOT / 'samples' / (sample+'.png')
            content = path.read_bytes()
            start = time.monotonic()
            r = client.post('/api/analyze', files={'file':(path.name, content, 'image/png')})
            r.raise_for_status(); job_id = r.json()['id']
            limit = time.monotonic()+300
            while time.monotonic() < limit:
                job = client.get('/api/jobs/'+job_id).json()
                if job['status'] in ('done','error'):
                    break
                time.sleep(.2)
            row = {'sample':sample, 'mode':mode, 'image_sha256':hashlib.sha256(content).hexdigest(),
                   'preparation':prep, 'upload_to_result_seconds':round(time.monotonic()-start,3),
                   'status':job['status'], 'result':job.get('result'), 'error':job.get('error')}
            rows.append(row)
            with (out/'results.jsonl').open('a',encoding='utf-8',newline='\n') as f:
                f.write(json.dumps(row,ensure_ascii=False)+'\n')
            client.delete('/api/jobs/'+job_id)
            print(json.dumps({k:v for k,v in row.items() if k!='result'},ensure_ascii=False),flush=True)
            if job['status'] != 'done':
                raise RuntimeError('Photo evaluation failed')
    comparisons = []
    for name in ('notice','event'):
        cold = next(r for r in rows if r['sample']==name and r['mode']=='cold')
        warm = next(r for r in rows if r['sample']==name and r['mode']=='preloaded')
        comparisons.append({'sample':name, 'cold_seconds':cold['upload_to_result_seconds'],
            'preloaded_seconds':warm['upload_to_result_seconds'], 'preparation_seconds':warm['preparation']['seconds'],
            'transcript_identical':cold['result']['raw_text']==warm['result']['raw_text'],
            'fields_identical':cold['result']['fields']==warm['result']['fields']})
    report = {'app_sha256':app.APP_REVISION,'comparisons':comparisons,
              'all_done':all(r['status']=='done' for r in rows),
              'scope':'Moves model load before upload when the page/file selection leaves enough preparation time. Does not speed up token generation, OCR, or every warm request. Single pair per sample, not population performance.'}
    (out/'summary.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(report),flush=True)


if __name__ == '__main__':
    main()
