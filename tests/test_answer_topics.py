import time
import json
import pytest
from fastapi.testclient import TestClient
import app


@pytest.mark.parametrize('question,answer,evidence,conflict',[
    ('會停電嗎？','甲棟會停電。','停水範圍：甲棟。',True),
    ('會停電嗎？','是的，上午九時開始。','上午九時停止供水。',True),
    ('網路會中斷嗎？','網路中斷一小時。','天然氣供應暫停一小時。',True),
    ('會停電嗎？','不會停電。','供電照常。',False),
    ('會停電嗎？','會停電一小時。','The power supply will be interrupted for one hour.',False),
    ('丙棟會停水嗎？','丙棟不會停水。','丙棟不受影響。',False),
    ('是停水還是停電？','停水。','本區供水暫停。',False),
])
def test_explicit_service_identity_without_blanket_refusal(question,answer,evidence,conflict):
    assert app.conflicting_service_topic(question,answer,evidence)==conflict


def test_real_quote_cannot_support_a_different_service_answer(monkeypatch):
    async def generate(*args,**kwargs):
        return json.dumps({'answer':'甲棟會停電。','evidence':'停水範圍：甲棟。','found':True},ensure_ascii=False)
    monkeypatch.setattr(app,'generate',generate)
    with TestClient(app.app) as client:
        app.jobs['service-topic']={'created':time.time(),'status':'done','result':{'raw_text':'停水範圍：甲棟。','fields':[]}}
        response=client.post('/api/ask',headers={'X-PaperVoice':'local-ui'},json={'job_id':'service-topic','question':'會停電嗎？'})
        assert response.status_code==200
        assert response.json()['found'] is False and response.json()['evidence']==''
