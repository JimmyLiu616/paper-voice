"""Frozen-app, page-scoped evaluation of downloaded official PDFs via real local API."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_documents import norm


def groups_match(text,groups):
    return all(any(norm(token) in norm(text) for token in group) for group in groups)


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='public-v1');args=p.parse_args()
    if not args.name.replace('-','').replace('_','').isalnum():p.error('Invalid run name')
    base=ROOT/'evaluation/public-documents'
    cases=json.loads((base/'cases.json').read_text(encoding='utf-8'))['cases']
    manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    sources={s['id']:s for s in manifest['sources']}
    out=ROOT/'.runtime/public-documents/runs'/args.name;out.mkdir(parents=True,exist_ok=False)
    meta={'name':args.name,'app_sha256':hashlib.sha256((ROOT/'app.py').read_bytes()).hexdigest(),
          'cases_sha256':hashlib.sha256((base/'cases.json').read_bytes()).hexdigest(),
          'manifest_sha256':hashlib.sha256((base/'manifest.json').read_bytes()).hexdigest(),
          'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope':'5 selected PDF pages / 4 public sources. No fine-tuning; no complete CER ground truth.',
          'note':'Required-span / abstention checks, not full semantic correctness. No automatic publication of raw sources.'}
    (out/'app.py').write_bytes((ROOT/'app.py').read_bytes())
    (out/'cases.json').write_bytes((base/'cases.json').read_bytes())
    (out/'manifest.json').write_bytes((base/'manifest.json').read_bytes())
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    rows=[]
    with httpx.Client(base_url='http://127.0.0.1:8765',headers={'X-PaperVoice':'local-ui'},timeout=260) as client:
        meta['health']=client.get('/api/health').json()
        if meta['health'].get('app_sha256') != meta['app_sha256']:
            raise ValueError('Running service differs from app.py; restart service before evaluating')
        (out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        for case in cases:
            started=time.monotonic();job_id=None;record={'id':case['id'],'source_id':case['source_id'],'page':case['page']}
            try:
                image=next(i for i in sources[case['source_id']]['images'] if i['page']==case['page'])
                path=ROOT/image['path'];content=path.read_bytes()
                assert hashlib.sha256(content).hexdigest()==image['sha256'],'Image changed'
                r=client.post('/api/analyze',files={'file':(path.name,content,'image/png')});r.raise_for_status();job_id=r.json()['id']
                deadline=time.monotonic()+480
                while time.monotonic()<deadline:
                    r=client.get('/api/jobs/'+job_id);r.raise_for_status();job=r.json()
                    if job['status'] in ('done','error'):break
                    time.sleep(.8)
                if job['status']!='done':raise RuntimeError(job.get('error','Timed out'))
                record['result']=job['result'];fields={f['key']:f['value'] for f in job['result']['fields']}
                record['checks']=[]
                for check in case['checks']:
                    value=fields.get(check['field'],'')
                    passed=not value if check.get('empty') else groups_match(value,check['groups'])
                    record['checks'].append(dict(check,actual=value,passed=passed))
                record['questions']=[]
                for question in case['questions']:
                    r=client.post('/api/ask',json={'job_id':job_id,'question':question['text']});r.raise_for_status();answer=r.json()
                    record['questions'].append({'question':question,'answer':answer,
                        'passed':answer['found']==question['found'] and groups_match(answer['answer'],question['groups'])})
                record['status']='done'
            except Exception as exc:record.update(status='error',error=str(exc))
            finally:
                if job_id:
                    try:client.delete('/api/jobs/'+job_id)
                    except httpx.HTTPError:pass
            record['wall_seconds']=round(time.monotonic()-started,2);rows.append(record)
            with (out/'results.jsonl').open('a',encoding='utf-8') as file:file.write(json.dumps(record,ensure_ascii=False)+'\n')
            print(json.dumps({'id':case['id'],'status':record['status'],
                'fields':sum(c['passed'] for c in record.get('checks',[])),
                'qa':sum(q['passed'] for q in record.get('questions',[])),
                'seconds':record['wall_seconds'],'error':record.get('error')},ensure_ascii=False),flush=True)
    summary={'run':args.name,'documents':len({r['source_id'] for r in rows}),'pages_attempted':len(rows),
        'errors':sum(r['status']!='done' for r in rows),'fields_passed':sum(c['passed'] for r in rows for c in r.get('checks',[])),
        'fields_planned':sum(len(c['checks']) for c in cases),'qa_passed':sum(q['passed'] for r in rows for q in r.get('questions',[])),
        'qa_planned':sum(len(c['questions']) for c in cases),'app_sha256':meta['app_sha256'],'note':meta['note']}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/(args.name+'-summary.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
