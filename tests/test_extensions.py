import io
import time
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
import app
from corpus import redact_pair, correction_metric
from scripts.asr_worker import decode_bounded

HEADERS = {'X-PaperVoice': 'local-ui'}


@pytest.fixture
def client():
    with TestClient(app.app) as client:
        yield client


def test_corpus_export_needs_both_consent_and_review(client):
    body = {'original': '服務站-樓', 'corrected': '服務站一樓', 'provenance': 'synthetic'}
    assert client.post('/api/corpus/export', json=body, headers=HEADERS).status_code == 422
    body.update(reviewed=True, rights_confirmed=True)
    response = client.post('/api/corpus/export', json=body, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()['status'] == 'local_export_pending_maintainer_review'
    assert response.json()['metrics']['edit_distance'] == 1
    assert 'job_id' not in response.json()


def test_screening_applies_to_original_and_correction():
    before, after, count = redact_pair('姓名：王測試\n電話：0912-345-678\na123456789\na@b.com', '0912345678\n姓名：王測試')
    for sensitive in ['王測試', '0912', 'a123456789', 'a@b.com']:
        assert sensitive not in before + after
    assert count >= 4


def test_export_cannot_bypass_sensitive_data_screening(client):
    body = {'original':'請聯絡0912345678', 'corrected':'請聯絡0912345678',
        'provenance':'authorized', 'reviewed':True, 'rights_confirmed':True}
    assert client.post('/api/corpus/export', json=body, headers=HEADERS).status_code == 422


def test_preview_keeps_existing_result_and_excludes_document_metadata(client):
    app.jobs['preview'] = {'created':time.time(), 'status':'done', 'result':{'raw_text':'姓名：王測試\n服务站-樓', 'title':'private'}}
    response = client.post('/api/corpus/preview', json={'job_id':'preview','corrected':'姓名：王測試\n服務站一樓'}, headers=HEADERS)
    assert response.status_code == 200
    assert '王測試' not in response.text
    assert 'private' not in response.text
    assert '王測試' in app.jobs['preview']['result']['raw_text']


def test_audio_decoder_rejects_long_and_invalid_audio():
    stream = io.BytesIO()
    sf.write(stream, np.zeros(16000*31), 16000, format='WAV')
    stream.seek(0)
    with pytest.raises(ValueError, match='30 秒'):
        decode_bounded(stream)
    with pytest.raises(Exception):
        decode_bounded(io.BytesIO(b'not audio'))


def test_audio_api_uses_real_worker_boundary(client, monkeypatch):
    called = []
    def fake_worker(data, language):
        called.append((data,language))
        return {'text':'何時截止？'}
    monkeypatch.setattr(app, 'transcribe_audio', fake_worker)
    # Fixture readiness is isolated from whether a developer downloaded weights.
    monkeypatch.setattr(app.Path, 'exists', lambda _: True)
    r = client.post('/api/transcribe?language=zh', files={'file':('q.wav',b'audio','audio/wav')}, headers=HEADERS)
    assert r.status_code == 200 and called == [(b'audio','zh')]
    assert client.post('/api/transcribe?language=bad',files={'file':('x',b'x')},headers=HEADERS).status_code == 422


def test_document_taigi_requires_review_and_current_source(client, monkeypatch):
    app.jobs['nan'] = {'created':time.time(),'status':'done','result':{'raw_text':'你好，歡迎參加活動。'}}
    monkeypatch.setattr(app, 'taigi_wav', lambda _: b'RIFFtest')
    body = {'job_id':'nan','source':'你好','poj':'lí hó','confirmed':False}
    assert client.post('/api/document-taigi',json=body,headers=HEADERS).status_code == 422
    body['confirmed'] = True
    assert client.post('/api/document-taigi',json=body,headers=HEADERS).status_code == 200
    body['source'] = '另一份文件'
    assert client.post('/api/document-taigi',json=body,headers=HEADERS).status_code == 422


def test_character_error_rate_is_reference_based():
    assert correction_metric('一樓', '二樓')['character_error_rate'] == .5
    assert correction_metric('Ａ B\n', 'AB')['edit_distance'] == 0
