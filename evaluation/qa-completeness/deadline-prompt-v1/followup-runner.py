import asyncio, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import experiment_complete_deadlines as exp
app=exp.app

async def main():
    base=ROOT/'.runtime/complete-deadlines/deadline-prompt-v1'
    out=base/'followup.json'
    if out.exists():raise FileExistsError(out)
    extractions=json.loads((base/'extractions.json').read_text(encoding='utf-8'))
    questions=[
        {'source_id':'dev-postal','question':'申請最晚哪天寄出？以什麼為憑？','groups':[['2026'],['11月3日'],['郵戳']]},
        {'source_id':'dev-registration','question':'活動是哪天舉行？','groups':[['2026'],['11月8日']]},
        {'source_id':'dev-relative','question':'補正的七日從什麼時候開始算？','groups':[['次日']]},
    ]
    original=app.generate;rows=[]
    try:
        for q in questions:
            row=dict(q,variants={})
            for variant in ['baseline','candidate']:
                calls=[]
                async def generate(prompt,**kwargs):
                    if variant=='candidate':prompt=prompt.replace('answer 用短句；','answer 用短句；'+exp.INSTRUCTION,1)
                    response=await original(prompt,**kwargs);calls.append({'prompt':prompt,'response':response});return response
                app.generate=generate
                app.jobs['deadline-followup']={'created':time.time(),'status':'done','result':extractions[q['source_id']]}
                answer=await app.ask(app.Question(job_id='deadline-followup',question=q['question']))
                passed=answer['found'] and all(any(exp.norm(t) in exp.norm(answer['answer']) for t in g) for g in q['groups'])
                row['variants'][variant]={'answer':answer,'passed':passed,'calls':calls}
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='variants'}|{'answers':{k:v['answer'] for k,v in row['variants'].items()}},ensure_ascii=False),flush=True)
    finally:app.generate=original;app.jobs.pop('deadline-followup',None)
    out.write_text(json.dumps({'scope':'3 targeted follow-up development questions; same frozen extraction as first run','rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')

asyncio.run(main())
