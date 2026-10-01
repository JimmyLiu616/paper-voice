"""Real local integration/decoding experiment on synthetic (not human) speech."""
import json
from pathlib import Path
import subprocess
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from corpus import correction_metric

runtime = ROOT / '.runtime'
headers = {'X-PaperVoice':'local-ui'}
results=[]
with httpx.Client(base_url='http://127.0.0.1:8765', headers=headers, timeout=240) as client:
    for i, text in enumerate(['最晚什麼時候要完成？', '我需要準備什麼文件？']):
        response=client.post('/api/speech',json={'text':text,'language':'zh-TW','rate':-1})
        response.raise_for_status()
        audio=runtime / f'asr-test-{i}.wav'
        audio.write_bytes(response.content)
        for beam in [5,1]:
            output=runtime / f'asr-test-{i}-beam{beam}.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/asr_worker.py'),str(audio),str(output),'--beam',str(beam)],check=True,timeout=180)
            data=json.loads(output.read_text(encoding='utf-8'))
            if 'error' in data:
                raise RuntimeError(data['error'])
            data.update(reference=text, metrics=correction_metric(data['text'],text))
            results.append(data)
            print(json.dumps(data,ensure_ascii=False),flush=True)
    # Actual HTTP audio -> confirmed question -> grounded answer -> Mandarin audio.
    with (ROOT/'samples/event.png').open('rb') as file:
        r=client.post('/api/analyze',files={'file':('event.png',file,'image/png')})
    r.raise_for_status(); job=r.json()['id']
    deadline=time.monotonic()+240
    while time.monotonic()<deadline:
        data=client.get('/api/jobs/'+job).json()
        if data['status'] in ('done','error'):break
        time.sleep(1)
    assert data['status']=='done',data
    r=client.post('/api/transcribe?language=zh',files={'file':('q.wav',(runtime/'asr-test-1.wav').read_bytes(),'audio/wav')})
    r.raise_for_status(); asr=r.json()
    r=client.post('/api/ask',json={'job_id':job,'question':asr['text']})
    r.raise_for_status(); answer=r.json()
    assert answer['found'] and answer['evidence'] in data['result']['raw_text'],answer
    r=client.post('/api/speech',json={'text':answer['answer'],'language':'zh-TW'})
    r.raise_for_status(); assert r.content[:4]==b'RIFF'
    integration={'question':asr,'answer':answer,'speech_bytes':len(r.content),'image':'self-authored event.png'}
    client.delete('/api/jobs/'+job)
report={'scope':'Two synthetic Microsoft Hanhan Mandarin questions; not human speech or Taiwanese/Hakka validation',
    'optimization':'CPU int8, 4 threads, VAD, beam 1 vs beam 5; each run includes cold model load; no fine-tuning',
    'runs':results,'integration':integration}
(ROOT/'asr-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Real ASR and multimodal chain passed',flush=True)
