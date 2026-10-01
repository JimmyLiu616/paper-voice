import pytest
from fastapi.testclient import TestClient
import app
from scripts.taigi_text import mms_text, pronunciation_draft
from scripts import taigi_text

VOCAB = set(" abcdefghijklmnopqrstuvwxyz-'àáâèéêìíîòóôùúûāēīńōūǹ̂̄̍͘ḿ")


@pytest.fixture(autouse=True)
def no_model_download_required(monkeypatch):
    monkeypatch.setattr(taigi_text, 'load_vocab', lambda: VOCAB)


def test_mms_normalization_keeps_tones_and_nasal_letter():
    assert mms_text('Chhiáⁿ kā iáⁿ-pún gia̍h lâi。', VOCAB) == 'chhián kā ián-pún gia̍h lâi'
    assert mms_text('nā-sī í-keng pān-hó，tō bián koh-lâi。', VOCAB) == 'nā-sī í-keng pān-hó tō bián koh-lâi'


@pytest.mark.parametrize('text', ['10', '１０', '²', '日期', '𪜶', 'lí 🙂', '|', '???', ' '])
def test_mms_does_not_silently_drop_unsupported_information(text):
    with pytest.raises(ValueError):
        mms_text(text, VOCAB)


@pytest.mark.parametrize('text', ['2026年', '１０月', '你好abc', '你好🙂', '', '。', '龘', '你' * 81])
def test_hanji_draft_refuses_incomplete_or_invalid_text(text):
    with pytest.raises(ValueError):
        pronunciation_draft(text)


def test_draft_is_not_a_human_confirmation_or_translation():
    result = pronunciation_draft('你好')
    assert result['poj'] == 'lí hó'
    assert 'confirmed' not in result
    assert '不是華語翻譯' in result['warning']


def test_draft_api_header_and_length_are_enforced():
    with TestClient(app.app) as client:
        assert client.post('/api/taigi-pronunciation', json={'text':'你好'}).status_code == 403
        assert client.post('/api/taigi-pronunciation', headers={'X-PaperVoice':'local-ui'}, json={'text':'你'*81}).status_code == 422


def test_unknown_dictionary_entry_returns_actionable_failure():
    with TestClient(app.app) as client:
        response = client.post('/api/taigi-pronunciation', headers={'X-PaperVoice':'local-ui'}, json={'text':'龘'})
        assert response.status_code == 422
        assert '龘' in response.json()['detail']
