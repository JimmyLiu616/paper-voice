import io
import time
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import app


@pytest.fixture
def client():
    with TestClient(app.app) as c:
        yield c


HEADERS = {'X-PaperVoice': 'local-ui'}


def test_guessed_deadline_is_not_presented_as_source_fact():
    raw = '收到通知後十日內補交。發文日期：115年10月1日。'
    result = app.validate_extraction({'deadline': {'value': '115年10月11日', 'evidence': '收到通知後十日內補交。'}}, raw)
    deadline = next(x for x in result['fields'] if x['key'] == 'deadline')
    assert deadline['state'] == 'needs_review'
    assert deadline['value'] == ''
    assert any('相對期限' in w for w in result['warnings'])


def test_changed_amount_cannot_pass_with_real_quote():
    result = app.validate_extraction({'amount': {'value': '1000元', 'evidence': '報名費用：100元'}}, '報名費用：100元')
    assert next(x for x in result['fields'] if x['key'] == 'amount')['state'] == 'needs_review'


def test_exact_original_wording_remains_available():
    quote = '應備文件：身分證影本、填妥的報名表'
    result = app.validate_extraction({'required_documents': {'value': '身分證影本、填妥的報名表', 'evidence': quote}}, quote)
    field = next(x for x in result['fields'] if x['key'] == 'required_documents')
    assert field['value'] == '身分證影本、填妥的報名表'
    assert field['evidence'] == quote


def test_registration_action_is_not_replaced_by_capacity_exception():
    raw = '報名方式：請到活動中心服務櫃台登記\n名額有限，額滿即停止受理。'
    result = app.validate_extraction({'action': {'value': '額滿即停止受理。', 'evidence': '名額有限，額滿即停止受理。'}}, raw)
    action = next(f for f in result['fields'] if f['key']=='action')
    assert action['value'] == '請到活動中心服務櫃台登記'
    assert '名額有限，額滿即停止受理。' in result['conditions_raw']


def test_imperative_action_preserves_source_and_exemption():
    raw = '您的報名資料尚缺文件,請於期限前補交。\n如已完成補件請忽略本通知。'
    result = app.validate_extraction({},raw)
    assert next(f for f in result['fields'] if f['key']=='action')['value'] == raw.splitlines()[0]
    assert next(f for f in result['fields'] if f['key']=='conditions')['value'] == raw.splitlines()[1]


def test_dash_confused_with_floor_number_requires_confirmation():
    raw='地點：服務站-樓櫃台'
    result=app.validate_extraction({'location':{'value':'服務站-樓櫃台','evidence':raw}},raw)
    assert next(f for f in result['fields'] if f['key']=='location')['state']=='needs_review'


def test_cross_site_form_is_rejected(client):
    response = client.post('/api/analyze-text', json={'text': '請於星期一前完成申請'})
    assert response.status_code == 403


def test_invalid_upload_is_rejected(client):
    response = client.post('/api/analyze', files={'file': ('image.png', b'<script>bad</script>', 'image/png')}, headers=HEADERS)
    assert response.status_code == 415


def test_oversized_upload_is_rejected(client):
    response = client.post('/api/analyze', files={'file': ('large.png', b'x'*(app.MAX_BYTES+1), 'image/png')}, headers=HEADERS)
    assert response.status_code == 413


def test_taigi_does_not_silently_read_mandarin(client):
    response = client.post('/api/speech', json={'language': 'nan', 'text': '請於十月二十日前補交'}, headers=HEADERS)
    assert response.status_code == 422
    assert '白話字' in response.json()['detail']


def test_expired_result_is_not_accessible(client):
    app.jobs['expired'] = {'created': time.time()-app.TTL-1, 'status':'done', 'raw_text':'private'}
    assert client.get('/api/jobs/expired').status_code == 404
    assert 'expired' not in app.jobs


def test_delete_removes_result(client):
    app.jobs['delete-me'] = {'created':time.time(), 'status':'done', 'raw_text':'private'}
    assert client.delete('/api/jobs/delete-me', headers=HEADERS).status_code == 200
    assert client.get('/api/jobs/delete-me').status_code == 404


def test_security_headers_and_home(client):
    response=client.get('/')
    assert response.status_code==200
    assert '紙聲通' in response.text
    assert response.headers['cache-control']=='no-store'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
