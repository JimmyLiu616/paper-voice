"""Exercise Hanji draft -> real local MMS WAV using original synthetic short sentences."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    import numpy as np
    import soundfile as sf
    from fastapi.testclient import TestClient
    import app
    rows = []
    headers = {'X-PaperVoice':'local-ui'}
    with TestClient(app.app) as client:
        for index, text in enumerate(['你好', '食飽未？', '請共身分證影本攑來。', '若是已經辦好，就免閣來。']):
            started = time.monotonic()
            draft = client.post('/api/taigi-pronunciation', headers=headers, json={'text':text})
            assert draft.status_code == 200, draft.text
            result = draft.json()
            response = client.post('/api/speech', headers=headers, json={'language':'nan','text':result['poj']})
            assert response.status_code == 200, response.text
            wave, rate = sf.read(io.BytesIO(response.content))
            assert wave.ndim == 1 and len(wave) > rate / 5 and np.isfinite(wave).all()
            assert np.max(np.abs(wave)) > .001
            row = {**result, 'seconds':round(time.monotonic()-started,3), 'audio_seconds':round(len(wave)/rate,3),
                   'sample_rate':rate,'wav_sha256':hashlib.sha256(response.content).hexdigest()}
            (args.output/f'{index+1}.wav').write_bytes(response.content)
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
        failures = []
        for text in ['龘', '2026年10月20日', '１０月', '你好abc', '你好🙂']:
            response = client.post('/api/taigi-pronunciation',headers=headers,json={'text':text})
            assert response.status_code == 422
            failures.append({'text':text,'status':response.status_code,'detail':response.json()['detail']})
    report = {'scope':'Real CPU synthesis and complete vocabulary coverage only; no native-speaker pronunciation or Mandarin translation score.',
              'app_sha256':app.APP_REVISION,'helper_sha256':hashlib.sha256((ROOT/'scripts/taigi_text.py').read_bytes()).hexdigest(),
              'model':'facebook/mms-tts-nan','taibun_version':'1.1.8','runs':rows,'rejections':failures}
    (args.output/'report.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())


if __name__ == '__main__':
    main()
