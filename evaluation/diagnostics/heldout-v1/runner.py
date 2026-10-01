"""Record real model extraction before/after validation for selected known fixtures.

Diagnostic only: does not train, change the server, or assign a performance score.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app


async def run(args):
    out=ROOT/'.runtime/extraction-diagnostics'/args.name
    out.mkdir(parents=True,exist_ok=False)
    references={d['id']:d['reference'] for d in json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))['documents']}
    metadata={'app_sha256':app.APP_REVISION,'health':await app.health(),
              'ids':args.id,'purpose':'Model extraction versus postprocessing; diagnostic, not a new held-out score.',
              'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'app.py').write_bytes((ROOT/'app.py').read_bytes())
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    original=app.generate
    try:
        for source_id in args.id:
            calls=[]
            async def capture(prompt,**kwargs):
                response=await original(prompt,**kwargs)
                calls.append({'prompt':prompt,'options':kwargs,'response':response})
                return response
            app.generate=capture
            result=await app.extract(references[source_id])
            record={'source_id':source_id,'reference':references[source_id],'model_calls':calls,'validated':result}
            (out/(source_id+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'id':source_id,'status':'done'},ensure_ascii=False),flush=True)
    finally:
        app.generate=original


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--id',nargs='+',required=True)
    args=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.name) or any(not re.fullmatch(r'[A-Za-z0-9_-]+',s) for s in args.id):
        p.error('Use simple run and fixture IDs')
    asyncio.run(run(args))
