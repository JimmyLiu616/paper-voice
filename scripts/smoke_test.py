"""Real local inference test. Saves only outputs from original fictional fixtures."""
import io
import json
from pathlib import Path
import time
import wave
import httpx

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime'/'validation'
OUT.mkdir(exist_ok=True)
client=httpx.Client(base_url='http://127.0.0.1:8765',timeout=240,headers={'X-PaperVoice':'local-ui'})
report={'health':client.get('/api/health').json()}
response=client.post('/api/analyze',files={'file':('event.png',(ROOT/'samples'/'event.png').read_bytes(),'image/png')})
response.raise_for_status()
job_id=response.json()['id']
for _ in range(180):
    job=client.get('/api/jobs/'+job_id).json()
    if job['status'] in ('done','error'):break
    time.sleep(2)
assert job['status']=='done',job
report['event_result']=job['result']
fields={f['key']:f for f in job['result']['fields']}
assert '10月12日' in fields['deadline']['value'],fields
assert '100' in fields['amount']['value'],fields
assert '手機' in fields['required_documents']['value'],fields
assert '登記' in fields['action']['value'],fields
for question,key in [('我需要帶什麼？','supported_question'),('可以搭哪一路公車到會場？','unknown_question')]:
    response=client.post('/api/ask',json={'job_id':job_id,'question':question})
    response.raise_for_status();report[key]=response.json()
assert report['supported_question']['found'],report
assert not report['unknown_question']['found'],report
for lang,text in [('zh-TW','這是紙聲通的本機語音測試。請記得核對日期與應備文件。'),('nan','lí hó')]:
    response=client.post('/api/speech',json={'language':lang,'text':text})
    response.raise_for_status()
    with wave.open(io.BytesIO(response.content),'rb') as audio:
        duration=audio.getnframes()/audio.getframerate()
        assert duration>0.1
        report[lang]={'seconds':duration,'sample_rate':audio.getframerate(),'bytes':len(response.content)}
    (OUT/f'{lang}.wav').write_bytes(response.content)
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
client.delete('/api/jobs/'+job_id)
print(json.dumps(report,ensure_ascii=False,indent=2))
