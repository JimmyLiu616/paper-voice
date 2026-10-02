import asyncio
import subprocess
import pytest
from fastapi.testclient import TestClient
import app
from scripts.hakka_worker import validate_text, phoneme_tokens, speech_punctuation


def test_sentence_boundaries_become_supported_pauses_without_dropping_words():
    assert speech_punctuation('免費；毋使繳費。\n過期毋受理！')=='免費，毋使繳費，過期毋受理，'
    assert speech_punctuation('期限：十月五日、下晝五時。')=='期限，十月五日，下晝五時，'


@pytest.mark.parametrize('text', ['', '   ', '123', '天公2026', 'hello', '天公🙂', '天' * 81])
def test_hakka_rejects_unpronounceable_input(text):
    with pytest.raises(ValueError):
        validate_text(text)


def test_hakka_preserves_multicharacter_tone_tokens():
    assert validate_text(' 天公落水。 ') == '天公落水。'
    tokens = phoneme_tokens(['tʰ-ien_24 k-uŋ_24', 'l-ok_5 s-ui_31'])
    assert '24' in tokens and '31' in tokens and '_' not in tokens and '2' not in tokens


@pytest.mark.parametrize('payload', [{'text':'天公落水','dialect':'invalid'}, {'text':'天' * 81}, {'text':''}])
def test_hakka_api_validates_before_inference(monkeypatch, payload):
    monkeypatch.setattr(app, 'hakka_wav', lambda *a: pytest.fail('must not synthesize'))
    with TestClient(app.app) as client:
        assert client.post('/api/hakka-speech', headers={'X-PaperVoice':'local-ui'}, json=payload).status_code == 422


def test_hakka_requires_local_boundary():
    with TestClient(app.app) as client:
        assert client.post('/api/hakka-speech', json={'text':'天公落水'}).status_code == 403


def test_hakka_releases_lock_after_worker_error(monkeypatch):
    monkeypatch.setattr(app, 'hakka_ready', lambda: True)
    def timeout(*args, **kwargs):
        assert kwargs['timeout'] == 120
        raise subprocess.TimeoutExpired('worker', 120)
    monkeypatch.setattr(app.subprocess, 'run', timeout)
    with TestClient(app.app) as client:
        response = client.post('/api/hakka-speech', headers={'X-PaperVoice':'local-ui'}, json={'text':'天公落水'})
        assert response.status_code == 503
    assert not app.speech_lock.locked()


def test_hakka_does_not_queue_behind_speech(monkeypatch):
    lock = asyncio.Lock()
    monkeypatch.setattr(app, 'speech_lock', lock)
    async def check():
        await lock.acquire()
        try:
            with pytest.raises(app.HTTPException) as error:
                await app.hakka_speech(app.HakkaRequest(text='天公落水'))
            assert error.value.status_code == 409
        finally:
            lock.release()
    asyncio.run(check())
