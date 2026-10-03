import asyncio
import json
import time
import httpx
import pytest
from fastapi.testclient import TestClient
import app
from scripts.taigi_translation import mask_numbers, restore_numbers, reading_draft, integer_hanji, WEIGHT_SHA256


def test_number_guard_preserves_dates_and_does_not_invent_year():
    source='請於115年10月20日下午5時前提出申請。'
    masked,numbers=mask_numbers(source)
    restored=restore_numbers(masked,numbers,masked.replace('請於','請佇'))
    assert restored=='請佇115年10月20日下午5時前提出申請。'
    assert reading_draft(restored)=='請佇一百一十五年十月二十日下午五時前提出申請。'


@pytest.mark.parametrize('candidate',[
    '請佇一千一百五年前申請。',
    '請佇[NUM_B]年[NUM_A]月申請。',
    '請佇[NUM_A]年[NUM_A]月申請。',
    '請佇[NUM_A]年[NUM_B]月申請，加收300元。',
    '請佇[NUM_A]月[NUM_B]年申請。',
    '請佇[NUM_A]年[NUM_B]月[NUM_Z]日申請。',
    '請佇[NUM_A]年[NUM_B]月[NUM_?]申請。',
])
def test_corrupt_numeric_drafts_are_never_restored(candidate):
    masked,numbers=mask_numbers('115年10月')
    with pytest.raises(ValueError):restore_numbers(masked,numbers,candidate)


@pytest.mark.parametrize('source',['[NUM_A]年','', '你'*81])
def test_input_cannot_inject_reserved_slots(source):
    with pytest.raises(ValueError):mask_numbers(source)


def test_fee_unit_synonyms_keep_exact_source_number():
    masked,numbers=mask_numbers('費用300元')
    assert restore_numbers(masked,numbers,'費用[NUM_A]箍')=='費用300箍'


def test_research_and_table_labels_have_explicit_readings():
    assert reading_draft('RQ2:資料分析。')=='研究問題二：資料分析。'
    assert reading_draft('表1系統模組與資料流')=='表一系統模組與資料流'
    assert reading_draft('圖12系統架構')=='圖十二系統架構'
    assert reading_draft('RQI:資料分析。')=='RQI:資料分析。'  # No OCR digit guessing.
    with pytest.raises(ValueError):reading_draft('ABC123')


def test_rq_number_never_enters_or_depends_on_model_translation(monkeypatch):
    from scripts import taigi_text
    calls=[]
    async def generate(text,**kw):calls.append(text);return '資料分析。'
    monkeypatch.setattr(app,'generate_taigi_draft',generate)
    monkeypatch.setattr(taigi_text,'pronunciation_draft',lambda t:{'poj':'chu liau'})
    r=asyncio.run(app.translate_taigi_text('RQ2:資料分析。',restore=False))
    assert calls==['資料分析。'] and r['translation']=='RQ2:資料分析。'
    assert r['reading']=='研究問題二：資料分析。'


def test_pronunciation_failure_keeps_specific_reason_and_translation(monkeypatch):
    from scripts import taigi_text
    async def generate(text,**kw):return '測試資料。'
    def fail(text):raise ValueError('字典未收錄：測')
    monkeypatch.setattr(app,'generate_taigi_draft',generate)
    monkeypatch.setattr(taigi_text,'pronunciation_draft',fail)
    r=asyncio.run(app.translate_taigi_text('測試資料。',restore=False))
    assert r['translation']=='測試資料。' and r['pronunciation_error']=='字典未收錄：測' and not r['poj']


def test_reading_substitutions_preserve_negative_and_payment_condition():
    assert reading_draft('逾期不受理。')=='過期不受理。'
    assert reading_draft('未滿65歲仍須繳費。')=='未滿六十五歲猶原愛繳費。'
    assert reading_draft('仍然免繳費。')=='仍然免繳費。'
    assert reading_draft('逾期仍可受理。')=='逾期仍可受理。'


@pytest.mark.parametrize(('value','expected'),[('0','零'),('10','十'),('20','二十'),('115','一百一十五'),('1005','一千零五'),('1010','一千零一十'),('9999','九千九百九十九')])
def test_written_numerals_do_not_change_quantity(value,expected):
    assert integer_hanji(value)==expected


@pytest.mark.parametrize('text',['0912345678','第001號','3.5元','3,000元','10000元','１０月','115/10/20'])
def test_unsupported_numeric_readings_require_manual_work(text):
    with pytest.raises(ValueError):reading_draft(text)


def test_source_bound_translation_never_confirms_or_plays(monkeypatch):
    calls=[]
    async def generate(masked):calls.append(masked);return masked.replace('請於','請佇')
    monkeypatch.setattr(app,'generate_taigi_draft',generate)
    with TestClient(app.app) as client:
        app.jobs['draft']={'created':time.time(),'status':'done','result':{'raw_text':'請於115年10月20日前申請。'}}
        payload={'job_id':'draft','source':'請於115年10月20日前申請。'}
        assert client.post('/api/taigi-translation',json=payload).status_code==403
        result=client.post('/api/taigi-translation',headers={'X-PaperVoice':'local-ui'},json=payload)
        assert result.status_code==200
        assert result.json()['translation']=='請佇115年10月20日前申請。'
        assert result.json()['reading']=='請佇一百一十五年十月二十日前申請。'
        assert result.json()['poj'] and 'confirmed' not in result.json()
        payload['source']='請繳交500元。'
        assert client.post('/api/taigi-translation',headers={'X-PaperVoice':'local-ui'},json=payload).status_code==422
        assert len(calls)==1


@pytest.mark.parametrize('outcome',['success','length','wrong_weight','http_error'])
def test_model_verification_and_document_model_restore(monkeypatch,outcome):
    calls=[];restored=[];original=httpx.AsyncClient
    def handler(request):
        if request.url.path=='/api/tags':
            from scripts.taigi_translation import MODEL
            return httpx.Response(200,json={'models':[{'name':MODEL,'digest':app.approved(MODEL)['ollama_digest']}]})
        body=json.loads(request.content);calls.append((request.url.path,body))
        if request.url.path=='/api/show':
            return httpx.Response(200,json={'modelfile':'FROM sha256-'+(WEIGHT_SHA256 if outcome!='wrong_weight' else 'wrong')})
        if request.url.path=='/api/generate':return httpx.Response(200,json={'done':True})
        if outcome=='http_error':return httpx.Response(500,json={'error':'failure'})
        return httpx.Response(200,json={'done_reason':'length' if outcome=='length' else 'stop','message':{'content':'{"translation":"請紮文件。"}'}})
    async def restore():restored.append(True)
    monkeypatch.setattr(app.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    monkeypatch.setattr(app,'restore_document_model',restore)
    async def run():
        if outcome=='success':assert await app.generate_taigi_draft('請攜帶文件。')=='請紮文件。'
        else:
            with pytest.raises(app.HTTPException):await app.generate_taigi_draft('請攜帶文件。')
        await asyncio.sleep(0)
    asyncio.run(run())
    assert bool(restored)==(outcome!='wrong_weight')
    if outcome=='wrong_weight':assert len(calls)==1
    else:assert calls[-1][1]['keep_alive']==0
