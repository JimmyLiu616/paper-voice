"""Exercise real local correction export and paired POJ synthesis with fictional data."""
import io
import json
from pathlib import Path
import time
import httpx
import soundfile as sf

root=Path(__file__).resolve().parents[1]
with httpx.Client(base_url='http://127.0.0.1:8765', headers={'X-PaperVoice':'local-ui'}, timeout=180) as client:
    response=client.post('/api/analyze-text',json={'text':'你好，歡迎參加活動。\n地點：服務站-樓\n姓名：王虛構\n電話：0912345678'})
    response.raise_for_status(); job=response.json()['id']
    try:
        for _ in range(180):
            data=client.get('/api/jobs/'+job).json()
            if data['status'] in ('done','error'):break
            time.sleep(1)
        assert data['status']=='done',data
        r=client.post('/api/corpus/preview',json={'job_id':job,'corrected':data['result']['raw_text'].replace('站-樓','站一樓')})
        r.raise_for_status(); preview=r.json()
        assert '王虛構' not in r.text and '0912345678' not in r.text
        r=client.post('/api/corpus/export',json={'original':preview['original'],'corrected':preview['corrected'],
            'provenance':'synthetic','reviewed':True,'rights_confirmed':True})
        r.raise_for_status(); record=r.json()
        assert record['metrics']['edit_distance']==1
        r=client.post('/api/document-taigi',json={'job_id':job,'source':'你好','poj':'lí hó','confirmed':True})
        r.raise_for_status(); waveform,sr=sf.read(io.BytesIO(r.content))
        assert sr==16000 and len(waveform)>0
        report={'corpus_preview_redactions':preview['redactions'],'export_record':record,
            'paired_taigi':{'source':'你好','poj':'lí hó','sample_rate':sr,'duration':len(waveform)/sr,
                'scope':'basic synthesis plumbing only; not independent Taiwanese linguistic validation'},
            'source':'Self-authored fictional text; no personal user data or external upload'}
        (root/'extension-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Real correction export and document-paired Min Nan synthesis passed.')
    finally:
        client.delete('/api/jobs/'+job)
