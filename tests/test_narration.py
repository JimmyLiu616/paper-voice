import base64
import io
import wave
import pytest
from fastapi.testclient import TestClient
import app
from scripts.narration import sentences,join_wav

def wav(rate=16000):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b'\1\0'*160)
    return out.getvalue()

def test_sentence_limits_keep_exceptions_and_reject_truncation():
    source='本活動免費，惟材料費另收。請攜帶身分證影本；不接受正本。'
    assert ''.join(sentences(source))==source
    assert len(sentences(source))==2
    for text in ['字'*81,'免費。'*7,'','!你好。']:
        with pytest.raises(ValueError):sentences(text)

def test_audio_join_preserves_all_frames_and_checks_format():
    with wave.open(io.BytesIO(join_wav([wav(),wav()])),'rb') as w:
        assert w.getnframes()==320+4000
    with pytest.raises(ValueError):join_wav([wav(),wav(22050)])

@pytest.mark.parametrize('language,dialect',[('zh-TW',''),('nan',''),('hakka','sixian'),('hakka','hailu'),('ami','ami_Xiug')])
def test_language_routing_automatically_translates_and_synthesizes(monkeypatch,language,dialect):
    calls=[]
    monkeypatch.setattr(app,'mandarin_wav',lambda text,rate:calls.append(('zh',text)) or wav())
    monkeypatch.setattr(app,'hakka_wav',lambda text,d:calls.append(('hakka',d,text)) or wav())
    monkeypatch.setattr(app,'taigi_wav',lambda text:calls.append(('nan',text)) or wav())
    async def translate(text,restore=True):
        calls.append(('translate_nan',text,restore));return {'translation':'免費','poj':'bian hui'}
    async def restore():pass
    monkeypatch.setattr(app,'translate_taigi_text',translate)
    monkeypatch.setattr(app,'restore_document_model',restore)
    monkeypatch.setattr(app,'amis_translate_speak_local',lambda text,d:calls.append(('ami',d,text)) or {'translation':'awaay ko payso.','audio_base64':base64.b64encode(wav()).decode()})
    with TestClient(app.app) as c:
        body={'text':'本活動免費，不必繳費。','language':language,'dialect':dialect}
        assert c.post('/api/narrate',json=body).status_code==403
        r=c.post('/api/narrate',headers={'X-PaperVoice':'local-ui'},json=body)
    assert r.status_code==200 and not r.json()['speech_error']
    assert r.json()['language']==language and r.json()['audio_base64']
    assert calls
    if language=='nan':assert calls[0][2] is False

def test_unsupported_hakka_preserves_chinese_and_never_plays_partial_audio(monkeypatch):
    monkeypatch.setattr(app,'hakka_wav',lambda *a:pytest.fail('No speech before whole-answer validation'))
    with TestClient(app.app) as c:
        result=c.post('/api/narrate',headers={'X-PaperVoice':'local-ui'},json={'text':'本活動免費。不過材料費另收。','language':'hakka'}).json()
    assert result['audio_base64'] is None
    assert result['source']=='本活動免費。不過材料費另收。'
    assert result['speech_error'] and not result['translation']

def test_language_dialect_mismatch_rejected():
    with TestClient(app.app) as c:
        assert c.post('/api/narrate',headers={'X-PaperVoice':'local-ui'},json={'text':'你好。','language':'hakka','dialect':'ami_Xiug'}).status_code==422
