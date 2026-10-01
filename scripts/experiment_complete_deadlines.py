"""Paired live-model development experiment; never changes the running app or trains."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app

INSTRUCTION = ('回答時間或期限時，完整保留來源明示的年、月、日、時刻，以及起算點、'
               '郵戳或資格條件；不可只答幾點而漏掉日期。依問題區分不同事件，'
               '不要混入發文日或其他活動日期；來源未寫的部分不可自行補出。')


def norm(text):
    return re.sub(r'\s+', '', text).casefold()


async def run(name):
    out = ROOT / '.runtime/complete-deadlines' / name
    out.mkdir(parents=True, exist_ok=False)
    cases = json.loads((ROOT/'evaluation/cases.json').read_text(encoding='utf-8'))['cases']
    docs = {d['id']:d['reference'] for d in json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))['documents']}
    cases = [c for c in cases if c['split']=='dev']
    questions=[]
    for case in cases:
        for i,q in enumerate(case['questions']):
            questions.append({'id':case['id']+f'-qa-{i}', 'source_id':case['id'],
                              'question':q['text'], 'found':q['found'],
                              'groups':[[s] for s in q['contains']], 'kind':'existing-regression'})
    docs['demo-notice']=(ROOT/'samples/notice.txt').read_text(encoding='utf-8')
    questions += [
        {'id':'demo-deadline','source_id':'demo-notice','question':'最晚什麼時候要完成',
         'found':True,'groups':[['115'],['10月20日'],['下午5時','下午5點','17時','17:00']], 'kind':'deadline-completeness'},
        {'id':'registration-deadline','source_id':'dev-registration','question':'最晚什麼時候報名？',
         'found':True,'groups':[['2026'],['10月23日'],['12時','12點','12:00']], 'kind':'deadline-completeness'},
        {'id':'english-deadline','source_id':'dev-english-renewal','question':'最晚什麼時候更新會員？',
         'found':True,'groups':[['2026'],['10月28日','October 28'],['下午4','16:00','16時','4 PM']], 'kind':'deadline-completeness'},
        {'id':'relative-deadline','source_id':'dev-relative','question':'補正期限是多久？',
         'found':True,'groups':[['次日'],['七日','7日','七天','7天']], 'kind':'deadline-completeness'},
        {'id':'no-deadline','source_id':'dev-waiver','question':'有沒有申請截止日？',
         'found':True,'groups':[['未設定','沒有','未訂','不設']], 'kind':'deadline-completeness'},
    ]
    metadata={'name':name,'app_sha256':app.APP_REVISION,'instruction':INSTRUCTION,
              'scope':'Paired model calls on existing fictional development documents; automated span checks, not independent human-reviewed evaluation.',
              'fields':'One shared actual extraction per document for both prompts',
              'question_count':len(questions),'health':await app.health()}
    for filename,value in [('metadata.json',metadata),('questions.json',questions),('documents.json',docs)]:
        (out/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'app.py').write_bytes((ROOT/'app.py').read_bytes())
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    extractions={}
    for source_id in sorted({q['source_id'] for q in questions}):
        extractions[source_id]=await app.extract(docs[source_id])
        print(json.dumps({'extracted':source_id}),flush=True)
    (out/'extractions.json').write_text(json.dumps(extractions,ensure_ascii=False,indent=2),encoding='utf-8')
    original=app.generate
    rows=[]
    try:
        for i,q in enumerate(questions):
            row=dict(q, variants={})
            # Alternate order to reduce systematic cold/cache timing bias.
            for variant in (['baseline','candidate'] if i%2==0 else ['candidate','baseline']):
                calls=[]
                async def generate(prompt,**kwargs):
                    if variant=='candidate':
                        marker='answer 用短句；'
                        if marker not in prompt:raise ValueError('Baseline prompt changed')
                        prompt=prompt.replace(marker,marker+INSTRUCTION,1)
                    reply=await original(prompt,**kwargs)
                    calls.append({'prompt':prompt,'response':reply})
                    return reply
                app.generate=generate
                job_id='deadline-experiment'
                app.jobs[job_id]={'created':time.time(),'status':'done','result':extractions[q['source_id']]}
                started=time.monotonic()
                try:
                    answer=await app.ask(app.Question(job_id=job_id,question=q['question']))
                    passed=(answer['found']==q['found'] and all(any(norm(s) in norm(answer['answer']) for s in g) for g in q['groups']))
                    row['variants'][variant]={'answer':answer,'passed':passed,'calls':calls,'seconds':round(time.monotonic()-started,3)}
                except Exception as exc:
                    row['variants'][variant]={'passed':False,'error':str(exc),'calls':calls}
                finally: app.jobs.pop(job_id,None)
            rows.append(row)
            with (out/'results.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            print(json.dumps({'id':q['id'],**{v:r['passed'] for v,r in row['variants'].items()}}),flush=True)
    finally:app.generate=original
    summary=dict(metadata, totals={v:sum(r['variants'][v]['passed'] for r in rows) for v in ['baseline','candidate']},
                 improvements=[r['id'] for r in rows if not r['variants']['baseline']['passed'] and r['variants']['candidate']['passed']],
                 regressions=[r['id'] for r in rows if r['variants']['baseline']['passed'] and not r['variants']['candidate']['passed']],
                 errors=sum('error' in v for r in rows for v in r['variants'].values()),deployed=False)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);args=parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]+',args.name):parser.error('Use a simple run name')
    asyncio.run(run(args.name))
