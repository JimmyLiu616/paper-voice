"""Evaluate raw-only QA context on saved public-v9 development transcripts."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app as backend
from scripts.evaluate_public_documents import groups_match


async def main():
    source = ROOT / '.runtime/public-documents/runs/public-v9/results.jsonl'
    out = ROOT / '.runtime/qa-raw-only-v1'
    out.mkdir(exist_ok=False)
    original_generate = backend.generate
    async def raw_only_generate(prompt, **kwargs):
        instructions, payload = prompt.split('\n', 1)
        data = json.loads(payload)
        data.pop('source_fields')
        return await original_generate(instructions + '\n' + json.dumps(data, ensure_ascii=False), **kwargs)
    backend.generate = raw_only_generate
    (out/'app.py').write_bytes((ROOT/'app.py').read_bytes())
    (out/'runner.py').write_bytes(Path(__file__).read_bytes())
    records = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend.app), base_url='http://testserver',
                                 headers={'X-PaperVoice':'local-ui'}, timeout=180) as client:
        for row in map(json.loads, source.read_text(encoding='utf-8').splitlines()):
            backend.jobs['context-test'] = {'created':time.time(),'status':'done','result':row['result']}
            for old in row['questions']:
                q = old['question']
                response = await client.post('/api/ask', json={'job_id':'context-test','question':q['text']})
                response.raise_for_status()
                answer = response.json()
                passed = answer['found'] == q['found'] and groups_match(answer['answer'], q['groups'])
                records.append({'id':row['id'],'question':q,'before':old['answer'],'before_passed':old['passed'],
                                'after':answer,'passed':passed})
                print(json.dumps({'id':row['id'],'before':old['passed'],'after':passed}), flush=True)
    (out/'results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    report = {'app_sha256':backend.APP_REVISION,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'planned':len(records),'before_passed':sum(r['before_passed'] for r in records),
              'after_passed':sum(r['passed'] for r in records),
              'scope':'Existing development transcripts. Candidate removes redundant source_fields from QA prompt; no training.'}
    (out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__ == '__main__':
    asyncio.run(main())
