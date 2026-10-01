"""Real HTTP benchmark. Dev by default; test requires explicit final-evaluation flag."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from corpus import correction_metric


def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if not c.isspace() and not unicodedata.category(c).startswith('P'))


def score_fields(case,result):
    fields={f['key']:f['value'] for f in result['fields']}
    checks=[]
    for field,tokens in case['expected'].items():
        value=fields.get(field,'')
        checks.append({'field':field,'kind':'required_spans','passed':all(norm(t) in norm(value) for t in tokens),
            'expected':tokens,'actual':value})
    for field in case['absent']:
        checks.append({'field':field,'kind':'must_abstain','passed':not fields.get(field,''),'actual':fields.get(field,'')})
    for field,tokens in case['forbidden'].items():
        checks.append({'field':field,'kind':'forbidden_spans','passed':not any(norm(t) in norm(fields.get(field,'')) for t in tokens),
            'forbidden':tokens,'actual':fields.get(field,'')})
    return checks


def main():
    p=argparse.ArgumentParser(); p.add_argument('--name',required=True);p.add_argument('--split',choices=['dev','test'],default='dev')
    p.add_argument('--final-evaluation',action='store_true');p.add_argument('--variants',nargs='+',choices=['clean','tilt_blur'],default=['clean','tilt_blur'])
    p.add_argument('--freeze',type=Path,help='Pre-recorded candidate and evaluation file hashes, required for test split')
    p.add_argument('--text-only',action='store_true');p.add_argument('--resume',action='store_true');args=p.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.name):p.error('Use a simple run name')
    if args.split=='test' and not args.final_evaluation:p.error('Freeze candidate before opening test split; pass --final-evaluation deliberately')
    if args.split=='test' and not args.freeze:p.error('Test split requires --freeze pointing to a pre-recorded freeze manifest')
    freeze=None
    if args.freeze:
        freeze=json.loads(args.freeze.read_text(encoding='utf-8'))
        for file,expected in freeze['files'].items():
            if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=expected:
                raise ValueError('Frozen file changed: '+file)
    cases=json.loads((ROOT/'evaluation/cases.json').read_text(encoding='utf-8'))
    manifest=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))
    if manifest['source_sha256']!=hashlib.sha256((ROOT/'evaluation/cases.json').read_bytes()).hexdigest():raise ValueError('Rebuild fixtures after changing annotations')
    documents={d['id']:d for d in manifest['documents']}
    out=ROOT/'evaluation/runs'/args.name;out.mkdir(parents=True,exist_ok=True)
    resultfile=out/'results.jsonl'
    if resultfile.exists() and not args.resume:raise ValueError('Run already exists; choose a new name or --resume')
    finished=set()
    if resultfile.exists():
        finished={(r['id'],r['variant']) for r in map(json.loads,resultfile.read_text(encoding='utf-8').splitlines())}
    metadata={'name':args.name,'split':args.split,'variants':['text'] if args.text_only else args.variants,
        'dataset_sha256':manifest['source_sha256'],'app_sha256':hashlib.sha256((ROOT/'app.py').read_bytes()).hexdigest(),
        'metric':'Required-span/abstention checks, NOT exact semantic correctness. CER keeps punctuation.',
        'population':'Original synthetic notices; no claims about real users or real photos'}
    with httpx.Client(base_url='http://127.0.0.1:8765',headers={'X-PaperVoice':'local-ui'},timeout=260) as client:
        metadata['health']=client.get('/api/health').json()
        if metadata['health'].get('app_sha256') != metadata['app_sha256']:
            raise ValueError('Running service differs from app.py; restart service before evaluating')
        if freeze and metadata['health'].get('digest')!=freeze['model_digest']:
            raise ValueError('Model digest differs from frozen candidate')
        if freeze:
            metadata['freeze_sha256']=hashlib.sha256(args.freeze.read_bytes()).hexdigest()
        meta=out/'metadata.json'
        if meta.exists():
            prior=json.loads(meta.read_text(encoding='utf-8'))
            if any(prior[k]!=metadata[k] for k in ['app_sha256','dataset_sha256','split','variants']):raise ValueError('Cannot resume after code/data/config changes')
        else:
            metadata['runner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            metadata['metric_sha256']=hashlib.sha256((ROOT/'corpus.py').read_bytes()).hexdigest()
            meta.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
            # Preserve the measured implementation for new runs; never fabricate old snapshots.
            source=out/'source';source.mkdir(exist_ok=True)
            for path in [ROOT/'app.py',ROOT/'corpus.py',Path(__file__)]:
                (source/path.name).write_bytes(path.read_bytes())
            if freeze:
                (out/'freeze.json').write_bytes(args.freeze.read_bytes())
        for case in cases['cases']:
            if case['split']!=args.split:continue
            for variant in metadata['variants']:
                if (case['id'],variant) in finished:continue
                record={'id':case['id'],'variant':variant,'language':case['language'],'split':args.split};job_id=None
                started=time.monotonic()
                try:
                    doc=documents[case['id']]
                    if variant=='text':r=client.post('/api/analyze-text',json={'text':doc['reference']})
                    else:
                        image=ROOT/doc['images'][variant]['path']
                        if hashlib.sha256(image.read_bytes()).hexdigest()!=doc['images'][variant]['sha256']:raise ValueError('Fixture checksum mismatch')
                        r=client.post('/api/analyze',files={'file':(image.name,image.read_bytes(),'image/jpeg')})
                    r.raise_for_status();job_id=r.json()['id'];deadline=time.monotonic()+480
                    while time.monotonic()<deadline:
                        r=client.get('/api/jobs/'+job_id);r.raise_for_status();job=r.json()
                        if job['status'] in ('done','error'):break
                        time.sleep(.8)
                    if job['status']!='done':raise RuntimeError(job.get('error','Job timed out'))
                    result=job['result'];record.update(result=result,cer=correction_metric(result['raw_text'],doc['reference']),
                        checks=score_fields(case,result),questions=[])
                    for question in case['questions']:
                        r=client.post('/api/ask',json={'job_id':job_id,'question':question['text']});r.raise_for_status();answer=r.json()
                        passed=answer['found']==question['found'] and all(norm(t) in norm(answer['answer']) for t in question['contains'])
                        record['questions'].append({'question':question, 'answer':answer,'passed':passed})
                    record['status']='done'
                except Exception as exc:record.update(status='error',error=str(exc))
                finally:
                    if job_id:
                        try:client.delete('/api/jobs/'+job_id)
                        except httpx.HTTPError:pass
                record['wall_seconds']=round(time.monotonic()-started,2)
                with resultfile.open('a',encoding='utf-8') as file:file.write(json.dumps(record,ensure_ascii=False)+'\n')
                failed=[c['field']+':'+c['kind'] for c in record.get('checks',[]) if not c['passed']]
                print(json.dumps({'id':case['id'],'variant':variant,'status':record['status'],'failed_fields':failed,
                    'question_passes':sum(q['passed'] for q in record.get('questions',[])),'seconds':record['wall_seconds']},ensure_ascii=False),flush=True)
    rows=[json.loads(line) for line in resultfile.read_text(encoding='utf-8').splitlines()]
    checks=[c for row in rows for c in row.get('checks',[])];qa=[q for row in rows for q in row.get('questions',[])]
    summary={'cases':len(rows),'errors':sum(r['status']!='done' for r in rows),'field_checks_passed':sum(c['passed'] for c in checks),
        'field_checks_total':len(checks),'qa_checks_passed':sum(q['passed'] for q in qa),'qa_checks_total':len(qa),
        'note':metadata['metric'],'failures':[{'id':r['id'],'variant':r['variant'],'checks':[c for c in r.get('checks',[]) if not c['passed']],
        'questions':[q for q in r.get('questions',[]) if not q['passed']]} for r in rows]}
    selected=[c for c in cases['cases'] if c['split']==args.split]
    variants=len(metadata['variants'])
    summary.update(inputs_planned=len(selected)*variants,
        field_checks_planned=sum(len(c['expected'])+len(c['absent'])+len(c['forbidden']) for c in selected)*variants,
        qa_checks_planned=sum(len(c['questions']) for c in selected)*variants)
    summary['complete']=len(rows)==summary['inputs_planned'] and summary['errors']==0
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='failures'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
