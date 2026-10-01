"""Paired core-model development comparison; isolated ASGI app, real Ollama/OCR.

Does not change the running service. Original public-document transcripts stay
under .runtime. Scores are required-span checks, not semantic accuracy.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app as backend
from scripts.evaluate_public_documents import groups_match

MODELS = {
    'gemma': ('gemma3:4b', 'a2af6cc3eb7fa8be8504abaf9b04e88f17a119ec3f04a3addf55f92841195f5a'),
    'ministral': ('ministral-3:3b-instruct-2512-q4_K_M', 'f04aa1c738f64e13c625b82ae92504fc0260fa6723b509ed1ece0fa188179b1d'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Unique lowercase run name required')
    out = ROOT/'.runtime/core-model-comparison'/args.name
    out.mkdir(parents=True, exist_ok=False)
    base = ROOT/'evaluation/public-documents'
    cases = json.loads((base/'cases.json').read_text(encoding='utf-8'))['cases']
    manifest = json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    sources = {r['id']: r for r in manifest['sources']}
    meta = {'name': args.name, 'app_sha256': sha(ROOT/'app.py'), 'cases_sha256': sha(base/'cases.json'),
            'manifest_sha256': sha(base/'manifest.json'), 'runner_sha256': sha(Path(__file__)),
            'transport': 'isolated in-process ASGI API; real external Ollama and Windows OCR',
            'scope': 'Same 5 existing development pages and 10 questions, alternating model order by page.',
            'deployed': False, 'models': {}, 'quality_accuracy_claimed': False}
    for src, name in [(ROOT/'app.py','app.py'), (Path(__file__),'runner.py'),
                      (base/'cases.json','cases.json'), (base/'manifest.json','manifest.json')]:
        (out/name).write_bytes(src.read_bytes())
    async with httpx.AsyncClient(timeout=15) as remote:
        tags = (await remote.get(backend.OLLAMA+'/api/tags')).json()['models']
        actual = {r['name']:r['digest'] for r in tags}
        for label, (tag, digest) in MODELS.items():
            if actual.get(tag) != digest:
                raise ValueError('Model digest changed: '+tag)
            show = (await remote.post(backend.OLLAMA+'/api/show', json={'model':tag})).json()
            if 'vision' not in show['capabilities']:
                raise ValueError('Model lacks vision: '+tag)
            meta['models'][label] = {'tag':tag, 'digest':digest, 'capabilities':show['capabilities'], 'details':show['details']}
        meta['live_service_before'] = (await remote.get('http://127.0.0.1:8765/api/health')).json()
    (out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    rows = []
    transport = httpx.ASGITransport(app=backend.app)
    async with httpx.AsyncClient(transport=transport,base_url='http://127.0.0.1:8765',
                                headers={'X-PaperVoice':'local-ui'},timeout=260) as client:
        for i, case in enumerate(cases):
            image = next(r for r in sources[case['source_id']]['images'] if r['page']==case['page'])
            path = ROOT/image['path']
            if sha(path) != image['sha256']:
                raise ValueError('Source image changed: '+case['id'])
            content = path.read_bytes()
            for label in (['gemma','ministral'] if i%2==0 else ['ministral','gemma']):
                backend.MODEL = MODELS[label][0]  # only this process; no changes to app.py or live service
                record = {'id':case['id'], 'model':label, 'checks':[], 'questions':[]}
                began = time.perf_counter(); job_id = None
                try:
                    response = await client.post('/api/analyze',files={'file':(path.name,content,'image/png')})
                    response.raise_for_status(); job_id = response.json()['id']
                    async with asyncio.timeout(600):
                        while True:
                            response = await client.get('/api/jobs/'+job_id); response.raise_for_status()
                            job = response.json()
                            if job['status'] in ('done','error'):
                                break
                            await asyncio.sleep(.5)
                    if job['status'] != 'done':
                        raise RuntimeError(job.get('error','Unknown analysis error'))
                    record['result'] = job['result']
                    fields = {f['key']: f['value'] for f in job['result']['fields']}
                    for check in case['checks']:
                        value = fields.get(check['field'],'')
                        record['checks'].append(dict(check,actual=value,passed=not value if check.get('empty') else groups_match(value,check['groups'])))
                    for question in case['questions']:
                        response = await client.post('/api/ask',json={'job_id':job_id,'question':question['text']})
                        response.raise_for_status(); answer=response.json()
                        record['questions'].append({'question':question,'answer':answer,
                            'passed':answer['found']==question['found'] and groups_match(answer['answer'],question['groups'])})
                    record['status'] = 'done'
                except Exception as error:
                    record.update(status='error', error=type(error).__name__+': '+str(error))
                finally:
                    if job_id:
                        await client.delete('/api/jobs/'+job_id)
                record['seconds'] = round(time.perf_counter()-began,2)
                rows.append(record)
                with (out/'results.jsonl').open('a',encoding='utf-8') as stream:
                    stream.write(json.dumps(record,ensure_ascii=False)+'\n')
                print(json.dumps({k:record[k] for k in ('id','model','status','seconds')} | {
                    'fields':sum(r['passed'] for r in record['checks']),
                    'qa':sum(r['passed'] for r in record['questions']), 'error':record.get('error')},ensure_ascii=False),flush=True)
    summaries = {}
    for label in MODELS:
        selected = [r for r in rows if r['model']==label]
        summaries[label] = {'pages':len(selected), 'errors':sum(r['status']=='error' for r in selected),
            'fields_passed':sum(c['passed'] for r in selected for c in r['checks']),
            'fields_planned':sum(len(c['checks']) for c in cases),
            'qa_passed':sum(q['passed'] for r in selected for q in r['questions']),
            'qa_planned':sum(len(c['questions']) for c in cases)}
    async with httpx.AsyncClient(timeout=30) as remote:
        live_after = (await remote.get('http://127.0.0.1:8765/api/health')).json()
        # Release the experimental model's cache, without touching the serving model.
        await remote.post(backend.OLLAMA+'/api/generate',json={'model':MODELS['ministral'][0],'keep_alive':0})
    summary = {'run':args.name, 'app_sha256':meta['app_sha256'], 'models':summaries,
               'live_model_unchanged':live_after['model']==meta['live_service_before']['model']==MODELS['gemma'][0],
               'deployed':False, 'note':'Paired existing-development regression, not unseen accuracy. Requires semantic review.'}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    asyncio.run(main())
