"""Exercise local draft + both TTS dialects without submitting human approval.

Audio is a technical test via the existing standalone TTS route. No checkbox
or mother-tongue review is claimed. Requires a running local Paper Voice app.
"""
import hashlib
import io
import json
from pathlib import Path
import time
import urllib.request
import wave

ROOT = Path(__file__).resolve().parents[1]


def post(path, body):
    request = urllib.request.Request('http://127.0.0.1:8765'+path,
        data=json.dumps(body).encode(), headers={'Content-Type':'application/json','X-PaperVoice':'local-ui'})
    with urllib.request.urlopen(request, timeout=150) as response:
        return response.read()


def main():
    folder = ROOT/'evaluation/hakka-translation-v1'
    output = ROOT/'.runtime/hakka-translation-demo';output.mkdir(exist_ok=True)
    cases = [('free','本活動免費，不必繳費。'),
             ('deadline','請於115年10月20日下午5時前提出申請。')]
    results=[]
    for case,source in cases:
        for dialect in ['sixian','hailu']:
            start=time.perf_counter()
            draft=json.loads(post('/api/hakka-translation',{'source':source,'dialect':dialect}))
            translation_seconds=time.perf_counter()-start
            start=time.perf_counter()
            audio=post('/api/hakka-speech',{'text':draft['reading'],'dialect':dialect})
            speech_seconds=time.perf_counter()-start
            with wave.open(io.BytesIO(audio)) as w:
                assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getnframes()>0
                rate=w.getframerate();duration=w.getnframes()/rate
            filename=f'{case}-{dialect}.wav';(output/filename).write_bytes(audio)
            row={'case':case,'dialect':dialect,'source':source,'translation':draft['translation'],
                 'reading':draft['reading'],'translation_seconds':round(translation_seconds,3),
                 'speech_seconds':round(speech_seconds,3),'rate':rate,'duration':round(duration,3),
                 'filename':filename,'sha256':hashlib.sha256(audio).hexdigest(),
                 'native_speaker_reviewed':False,'human_confirmation_submitted':False}
            results.append(row)
            (folder/'live-audio.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
