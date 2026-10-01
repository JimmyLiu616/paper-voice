"""Observed model non-facts plus nearby legitimate inputs through the public API."""
import json
import time

import pytest
from fastapi.testclient import TestClient
import app


@pytest.mark.parametrize('key,value,raw,rejected', [
    ('contact', 'Phone No.: _______________________', 'Phone No.: _______________________', True),
    ('contact', '＿＿＿＿', '聯絡電話：＿＿＿＿', True),
    ('contact', '02-1234-5678', '聯絡電話：02-1234-5678', False),
    ('contact', 'Phone No.: 02-1234-5678', 'Phone No.: 02-1234-5678', False),
    ('contact', 'help_desk@example.org', '聯絡方式：help_desk@example.org', False),
])
def test_blank_contacts_hidden_without_banning_real_contacts(key, value, raw, rejected):
    result = app.validate_extraction({key: {'value': value, 'evidence': raw}}, raw)
    field = next(f for f in result['fields'] if f['key'] == key)
    assert field['state'] == ('needs_review' if rejected else 'source_matched')
    assert field['value'] == ('' if rejected else value)
    if rejected:
        assert field['evidence'] == ''
        assert not any(value in line for line in result['summary'])
        assert any('欄位檢查' in line for line in result['warnings'])


@pytest.mark.parametrize('answer,expected_status', [
    ('found=true', 502),
    ('found = false', 502),
    ('`found: true`', 502),
    ('  ', 502),
    ('僅能由其中一人提出申請。', 200),
    ('此欄位顯示 found=true，表示已找到資料。', 200),
])
def test_format_failure_is_retryable_not_a_claim_of_missing_information(monkeypatch, answer, expected_status):
    raw = '申請人與配偶均符合申請資格時，僅能由其中一人提出申請。'
    async def generate(*args, **kwargs):
        return json.dumps({'answer': answer, 'evidence': raw, 'found': True}, ensure_ascii=False)
    monkeypatch.setattr(app, 'generate', generate)
    with TestClient(app.app) as client:
        app.jobs['format-test'] = {'created': time.time(), 'status': 'done',
                                  'result': {'raw_text': raw, 'fields': []}}
        response = client.post('/api/ask', headers={'X-PaperVoice': 'local-ui'},
                               json={'job_id': 'format-test', 'question': '夫妻可以各自申請嗎？'})
        assert response.status_code == expected_status
        if expected_status == 502:
            assert response.json() == {'detail': '這次回答格式異常，請重新提問。'}
        else:
            assert response.json()['answer'] == answer
