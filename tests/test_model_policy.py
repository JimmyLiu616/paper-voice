import asyncio
import hashlib
import json
import httpx
import pytest
from fastapi.testclient import TestClient
import app
from scripts import model_policy as mp


@pytest.mark.parametrize('model', ['qwen3:8b', 'qwen3-embedding:0.6b', 'deepseek-r1:8b',
    'paper-voice-omnitranslate-test:latest', 'foreign/renamed-model', 'qavit/mt5-small-hak',
    'ministral-3:3b-instruct-2512-q4_K_M'])
def test_unknown_chinese_and_experimental_models_cannot_serve(model):
    with pytest.raises(mp.ModelPolicyError):
        mp.approved(model)


def test_approved_download_cannot_use_latest_or_a_different_revision():
    entry=mp.approved('facebook/mms-tts-ami')
    assert mp.approved(entry['id'],revision=entry['revision'])==entry
    with pytest.raises(mp.ModelPolicyError):mp.approved(entry['id'],revision='main')


def test_same_size_model_replacement_invalidates_hash_cache(monkeypatch,tmp_path):
    path=tmp_path/'model.bin';path.write_bytes(b'approved')
    data={'approved_models':[{'id':'fixture','serving':True,'files':{'model.bin':{
        'bytes':8,'sha256':hashlib.sha256(b'approved').hexdigest()}}}]}
    monkeypatch.setattr(mp,'policy',lambda:data)
    mp.verify_files('fixture',tmp_path)
    path.write_bytes(b'replaced')
    with pytest.raises(mp.ModelPolicyError,match='SHA256'):mp.verify_files('fixture',tmp_path)


def test_missing_model_is_rejected_without_download(monkeypatch,tmp_path):
    data={'approved_models':[{'id':'fixture','serving':True,'files':{'model.bin':{'bytes':8,'sha256':'abc'}}}]}
    monkeypatch.setattr(mp,'policy',lambda:data)
    with pytest.raises(mp.ModelPolicyError,match='尚未就緒'):mp.verify_files('fixture',tmp_path)


@pytest.mark.parametrize('entrypoint', ['warmup','generate'])
@pytest.mark.parametrize('mode', ['blocked_tag','replaced_digest','absent'])
def test_no_inference_when_name_or_underlying_model_is_rejected(monkeypatch,entrypoint,mode):
    calls=[];client_type=httpx.AsyncClient
    def handler(request):
        calls.append((request.method,request.url.path))
        assert request.method=='GET', 'Rejected model must not get even a warmup POST'
        models=[] if mode=='absent' else [{'name':app.MODEL,'digest':'not-the-approved-weights'}]
        return httpx.Response(200,json={'models':models})
    monkeypatch.setattr(app.httpx,'AsyncClient',lambda **kw:client_type(transport=httpx.MockTransport(handler),**kw))
    if mode=='blocked_tag':monkeypatch.setattr(app,'MODEL','qwen3:8b')
    async def run():
        with pytest.raises(mp.ModelPolicyError):
            if entrypoint=='warmup':await app.warmup()
            else:await app.generate('document content')
    asyncio.run(run())
    assert all(method=='GET' for method,_ in calls)


def test_policy_rejection_returns_readable_api_error(monkeypatch):
    monkeypatch.setattr(app,'MODEL','qwen3:8b')
    with TestClient(app.app) as client:
        response=client.post('/api/warmup',headers={'X-PaperVoice':'local-ui'})
        assert response.status_code==503 and '模型來源規則拒絕' in response.json()['detail']


def test_hakka_does_not_swallow_policy_failure_as_model_fallback(monkeypatch):
    async def fail(*a,**kw):raise mp.ModelPolicyError('blocked by policy')
    monkeypatch.setattr(app,'generate',fail)
    with pytest.raises(mp.ModelPolicyError):
        asyncio.run(app.explain_hakka_notice('只有65歲以上才免費，其他人須繳500元。'))


def test_health_does_not_enable_taigi_when_only_speech_is_installed(monkeypatch):
    client_type=httpx.AsyncClient
    def handler(request):
        return httpx.Response(200,json={'models':[{'name':app.MODEL,'digest':app.approved(app.MODEL)['ollama_digest']}]})
    monkeypatch.setattr(app.httpx,'AsyncClient',lambda **kw:client_type(transport=httpx.MockTransport(handler),**kw))
    monkeypatch.setattr(app,'files_available',lambda *a:True)
    result=asyncio.run(app.health())
    assert result['taigi_ready'] and not result['narration_ready']['nan']
    assert result['model_ready'] and result['model_policy']['enforced']
