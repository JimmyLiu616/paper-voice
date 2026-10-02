import time
import pytest
from fastapi.testclient import TestClient
import app
from scripts.amis_worker import speech_text,validate_source
from scripts import amis_worker

VOCAB=set(" acdefghiklmnoprstuwxy'-")

def test_glottal_stop_is_preserved_for_mms():
    assert speech_text('ngaʼay ho.',VOCAB)=="nga'ay ho"
    assert speech_text('‘aca，’aca。',VOCAB)=="'aca 'aca"

@pytest.mark.parametrize('text',['費用 payso','payso 500','payso |','payso 0'])
def test_unreadable_characters_are_not_silently_dropped(text):
    with pytest.raises(ValueError):speech_text(text,VOCAB|{'0','|'})

@pytest.mark.parametrize('source,dialect',[('。','ami_Xiug'),('字'*81,'ami_Xiug'),('你好','invalid')])
def test_source_validation(source,dialect):
    with pytest.raises(ValueError):validate_source(source,dialect)

def test_automatic_endpoint_and_document_binding(monkeypatch):
    seen=[]
    def fake(source,dialect):
        seen.append(source)
        return {'source':source,'translation':'ngaʼay ho.','audio_base64':'wave'}
    monkeypatch.setattr(app,'amis_translate_speak_local',fake)
    h={'X-PaperVoice':'local-ui'}
    with TestClient(app.app) as c:
        body={'source':'你好。'}
        assert c.post('/api/amis-translate-speak',json=body).status_code==403
        assert c.post('/api/amis-translate-speak',headers=h,json=body).status_code==200
        assert 'confirmed' not in app.AmisRequest.model_fields
        app.jobs['amis-test']={'created':time.time(),'status':'done','result':{'raw_text':'你好。'}}
        body['job_id']='amis-test'
        assert c.post('/api/amis-translate-speak',headers=h,json=body).status_code==200
        body['source']='繳費500元'
        assert c.post('/api/amis-translate-speak',headers=h,json=body).status_code==422
        body['job_id']='missing'
        assert c.post('/api/amis-translate-speak',headers=h,json=body).status_code==404
        assert len(seen)==2

def test_synthesis_failure_keeps_translation_without_confirmation(monkeypatch,tmp_path):
    class Translator:
        def translate(self,*args):return 'ngaʼay ho. 中文'
    class Speaker:
        def speak(self,*args):raise ValueError('unsupported letters')
    monkeypatch.setattr(amis_worker,'Translator',Translator)
    monkeypatch.setattr(amis_worker,'Speaker',Speaker)
    audio=tmp_path/'speech.wav'
    result=amis_worker.run({'source':'你好。','dialect':'ami_Xiug'},audio)
    assert result['translation']=='ngaʼay ho. 中文'
    assert result['speech_error']=='unsupported letters'
    assert not audio.exists()

def test_synthesis_runs_immediately_after_translation(monkeypatch,tmp_path):
    calls=[]
    class Translator:
        def translate(self,*args):calls.append('translate');return 'ngaʼay ho.'
    class Speaker:
        def speak(self,text):calls.append('speak');return b'wave',"nga'ay ho"
    monkeypatch.setattr(amis_worker,'Translator',Translator)
    monkeypatch.setattr(amis_worker,'Speaker',Speaker)
    audio=tmp_path/'speech.wav'
    result=amis_worker.run({'source':'你好。','dialect':'ami_Xiug'},audio)
    assert calls==['translate','speak']
    assert result['speech_error']=='' and audio.read_bytes()==b'wave'
