import asyncio
import base64
import io
import json
import time
import wave
import pytest
from fastapi.testclient import TestClient
import app
from scripts.document_summary import (SummaryReview, finalize, document_blocks,
    summarize, number_agreement, narration_units)
from scripts.model_policy import ModelPolicyError


def point(raw,text='每隊最高100點。'):
    return [{'id':'p1','heading':'可用額度','text':text,'evidence':raw.splitlines()[1],
             'source_start':2,'source_end':2,'state':'draft','note':''}]


def review(ok=True):
    return SummaryReview(items=[{'id':'p1','supported':ok,'preserves_conditions':ok}],covers_important_information=True)


def test_variable_topics_and_exact_line_citations():
    raw='通知\n每隊最高100點。\n\n不得轉售。'
    result=finalize(raw,point(raw),review())
    assert result['fields']==[]
    assert result['highlights'][0]['heading']=='可用額度'
    assert result['highlights'][0]['evidence']==raw.splitlines()[1]
    assert result['unselected_source_lines']==[{'id':1,'text':'通知'},{'id':4,'text':'不得轉售。'}]
    assert result['narration_text']==result['highlights'][0]['text']


@pytest.mark.parametrize('text',['每隊最高100元。','每隊最高1000點。','每隊最高10點。'])
def test_changed_amount_or_unit_cannot_be_authorized_by_model(text):
    raw='通知\n每隊最高100點。'
    result=finalize(raw,point(raw,text),review())
    assert result['highlights'][0]['state']=='source_excerpt'
    assert result['narration_text']=='每隊最高100點。'


def test_dropped_limit_or_negation_falls_back_to_source():
    raw='通知\n每隊最高100點，不保證核發。'
    result=finalize(raw,point(raw,'每隊可獲100點。'),review(False))
    assert result['narration_text']==raw.splitlines()[1]


def test_empty_draft_falls_back_without_losing_document():
    raw='通知\n限額50組。\n\n若額滿則停止受理。'
    result=finalize(raw,[])
    assert '限額50組。' in result['narration_text']
    assert '若額滿則停止受理。' in result['narration_text']
    assert not result['unselected_source_lines']


def test_missing_or_duplicate_verdict_does_not_approve_paraphrase():
    raw='通知\n每隊最高100點。'
    r=review();r.items*=2
    assert finalize(raw,point(raw),r)['highlights'][0]['state']=='source_excerpt'
    assert finalize(raw,point(raw),None)['highlights'][0]['state']=='source_excerpt'


def test_source_policy_error_never_turns_into_summary_success():
    async def generate(*a,**kw):raise ModelPolicyError('blocked')
    with pytest.raises(ModelPolicyError):asyncio.run(summarize('文件原文',generate))


def test_malformed_model_output_keeps_source_instead_of_empty_fields():
    async def generate(*a,**kw):return 'not json'
    r=asyncio.run(summarize('活動通知\n本活動免費。',generate))
    assert r['highlights'] and '免費' in r['narration_text']


def test_numeric_check_preserves_time_percent_and_unit():
    assert not number_agreement('10月1日15:00前，最高100點。','10月1日15:30前，最高100點。')
    assert number_agreement('1. 每隊最高100點。','每隊最高100點。')
    assert not number_agreement('最高50%。','最高50元。')


def test_long_document_mandarin_is_not_truncated():
    text='甲'*3000+'不得轉售。'
    assert ''.join(narration_units([text],'zh-TW'))==text
    with pytest.raises(ValueError):narration_units(['甲'*81+'。'],'ami')
    assert len(narration_units(['本活動免費。'*8],'nan'))==8


def wav():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*1600)
    return b.getvalue()


@pytest.mark.parametrize('fail_second',[False,True])
def test_document_audio_aligns_text_and_never_returns_partial_wav(monkeypatch,fail_second):
    calls=[]
    async def synth(body,**kw):
        calls.append(body.text)
        return {'translation':body.text,'audio_base64':None if fail_second and len(calls)==2 else base64.b64encode(wav()).decode(),
                'speech_error':'unsupported' if fail_second and len(calls)==2 else '', 'warning':''}
    monkeypatch.setattr(app,'synthesize_narration',synth)
    with TestClient(app.app) as client:
        app.jobs['dynamic']={'created':time.time(),'status':'done','result':{'raw_text':'原文',
          'highlights':[{'id':'p1','text':'第一項。'},{'id':'p2','text':'第二項。'}]}}
        r=client.post('/api/narrate-document',headers={'X-PaperVoice':'local-ui'},json={'job_id':'dynamic'}).json()
    assert calls==['第一項。','第二項。']
    assert r['source']=='第一項。\n\n第二項。'
    if fail_second:
        assert r['audio_base64'] is None and r['segments']==[]
        assert r['translation']=='第一項。\n\n第二項。'
        assert r['translation_complete'] is False and r['failed_segment']=={'index':2,'total':2,'source':'第二項。'}
    else:
        assert r['segments'][1]['start']==.35 and r['segments'][1]['end']==.45
        with wave.open(io.BytesIO(base64.b64decode(r['audio_base64'])),'rb') as w:assert w.getnframes()==7200


def test_document_audio_rejects_stale_id_or_changed_point():
    with TestClient(app.app) as client:
        h={'X-PaperVoice':'local-ui'}
        assert client.post('/api/narrate-document',json={'job_id':'gone'},headers=h).status_code==404
        app.jobs['dynamic']={'created':time.time(),'status':'done','result':{'raw_text':'通知','highlights':[]}}
        assert client.post('/api/narrate-document',json={'job_id':'dynamic','point_id':'bad'},headers=h).status_code==422


def test_blocks_preserve_all_source_lines_and_subordinate_list_items():
    raw='申請通知\n\n一、參加資格\n1. 學生團隊。\n2. 需有指導老師。\n二、使用限制\n不得轉售。'
    blocks=document_blocks(raw)
    assert len(blocks)==3
    assert blocks[1]['evidence']=='一、參加資格\n1. 學生團隊。\n2. 需有指導老師。'
    assert blocks[2]['evidence']=='二、使用限制\n不得轉售。'
    for b in blocks:assert b['evidence']=='\n'.join(raw.splitlines()[b['source_start']-1:b['source_end']])


def test_live_pipeline_assigns_citations_and_falls_back_when_rewrite_drops_exception():
    raw='社區通知\n\n甲棟停水。乙棟不受影響。\n\n本次不收費。'
    drafts=iter([json.dumps({'heading':'停水安排','text':'甲棟停水。'},ensure_ascii=False),
                 json.dumps({'heading':'費用','text':'本次不收費。'},ensure_ascii=False),
                 json.dumps({'items':[{'id':'p1','supported':True,'preserves_conditions':True},
                                      {'id':'p2','supported':True,'preserves_conditions':True}],
                             'covers_important_information':True})])
    async def generate(*a,**kw):return next(drafts)
    result=asyncio.run(summarize(raw,generate))
    assert len(result['highlights'])==2
    assert result['highlights'][0]['source_start']==3
    assert result['highlights'][0]['text']=='甲棟停水。乙棟不受影響。'
    assert result['highlights'][0]['state']=='source_excerpt'
    assert result['highlights'][1]['state']=='ai_reviewed'
