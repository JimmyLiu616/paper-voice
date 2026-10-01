import time
from fastapi.testclient import TestClient
import app


def field(result,key):return next(f for f in result['fields'] if f['key']==key)


def test_cited_event_date_cannot_become_deadline():
    raw='原活動日期：2027年2月14日\n本次活動已取消，請勿到場。'
    result=app.validate_extraction({'deadline':{'value':'2027年2月14日','evidence':raw.splitlines()[0]}},raw)
    assert field(result,'deadline')['value']==''
    assert field(result,'deadline')['state']=='needs_review'


def test_single_label_keeps_postmark_condition_and_all_documents():
    raw='申請截止：2027年3月6日，以郵戳為憑\n應附文件：履歷表、同意書、證照影本'
    result=app.validate_extraction({'deadline':{'value':'2027年3月6日','evidence':raw.splitlines()[0]},
        'required_documents':{'value':'履歷表','evidence':raw.splitlines()[1]}},raw)
    assert '郵戳為憑' in field(result,'deadline')['value']
    assert field(result,'required_documents')['value']=='履歷表、同意書、證照影本'


def test_two_deadlines_are_not_arbitrarily_replaced_by_first_label():
    raw='報名截止：2027年3月6日\n繳交期限：2027年3月9日'
    result=app.validate_extraction({'deadline':{'value':'2027年3月9日','evidence':raw.splitlines()[1]}},raw)
    assert field(result,'deadline')['value']=='2027年3月9日'


def test_waiver_condition_stays_in_readable_summary():
    raw='一般費用：新臺幣90元\n持有效志工證者免收費用。'
    result=app.validate_extraction({},raw)
    assert '持有效志工證者免收費用。' in result['conditions_raw']
    assert any('志工證' in text for text in result['summary'])


def test_main_action_does_not_skip_instruction_to_change_route():
    raw='電梯暫停使用，請改走樓梯。\n行動不便住戶請事先洽管理員。'
    result=app.validate_extraction({},raw)
    assert field(result,'action')['value']==raw.splitlines()[0]


def test_relative_deadline_refuses_exact_calendar_date_without_model(monkeypatch):
    async def must_not_generate(*args,**kwargs):raise AssertionError('Unnecessary model call')
    monkeypatch.setattr(app,'generate',must_not_generate)
    with TestClient(app.app) as client:
        app.jobs['relative-policy']={'created':time.time(),'status':'done','result':{'raw_text':'申請期限：收到通知次日起五日內','fields':[]}}
        r=client.post('/api/ask',headers={'X-PaperVoice':'local-ui'},json={'job_id':'relative-policy','question':'確切日期是幾月幾日？'})
        assert r.status_code==200 and not r.json()['found']
        assert '起算日期' in r.json()['answer']


def test_qa_requires_a_real_verbatim_source_quote(monkeypatch):
    async def response(*args,**kwargs):return '{"answer":"不可以現場交件。","evidence":"不接受現場繳件。","found":true}'
    monkeypatch.setattr(app,'generate',response)
    with TestClient(app.app) as client:
        app.jobs['indexed']={'created':time.time(),'status':'done','result':{'raw_text':'請郵寄資料。\n不接受現場繳件。','fields':[]}}
        r=client.post('/api/ask',headers={'X-PaperVoice':'local-ui'},json={'job_id':'indexed','question':'可以現場交嗎？'})
        assert r.json()['evidence']=='不接受現場繳件。'
        async def invalid(*args,**kwargs):return '{"answer":"可以。","evidence":"接受現場繳件，週日也可以。","found":true}'
        monkeypatch.setattr(app,'generate',invalid)
        r=client.post('/api/ask',headers={'X-PaperVoice':'local-ui'},json={'job_id':'indexed','question':'可以嗎？'})
        assert not r.json()['found']


def test_dispatch_enclosures_are_not_required_materials():
    raw='附件：宣傳單、交通路線圖\n主旨：歡迎參加成果展。'
    data={'required_documents':{'value':'宣傳單、交通路線圖','evidence':raw.splitlines()[0]}}
    assert field(app.validate_extraction(data,raw),'required_documents')['value']==''


def test_explicit_request_to_complete_an_attachment_is_preserved():
    raw='附件：請填妥同意書並於當日繳交。'
    data={'required_documents':{'value':'同意書','evidence':raw}}
    assert field(app.validate_extraction(data,raw),'required_documents')['value']=='同意書'


def test_requested_attachment_does_not_authorize_invented_documents():
    raw='附件：請填妥同意書並於當日繳交。'
    data={'required_documents':{'value':'護照正本','evidence':raw}}
    assert field(app.validate_extraction(data,raw),'required_documents')['value']==''


def test_numbered_multiline_document_section_stops_at_next_heading():
    raw='二、申請應備文件如下：\n（一）申請表。\n（二）履歷表。\n（三）作品說明書一式3份。\n三、申請期限：2028年6月9日'
    result=app.validate_extraction({},raw)
    documents=field(result,'required_documents')
    assert '履歷表' in documents['value'] and '3份' in documents['value']
    assert '2028' not in documents['value']
    assert app.normalized(documents['evidence']) in app.normalized(raw)


def test_wrapped_postmark_deadline_is_not_hidden():
    raw='二、受理申請期間：自116年5月2日起至116年6月11日止（郵\n寄以郵戳為憑），逾期不受理。\n三、申請方式：線上申請。'
    deadline=field(app.validate_extraction({},raw),'deadline')
    assert '116年6月11日' in deadline['value'] and '郵戳為憑' in deadline['value']
    assert deadline['state']=='source_matched'
    assert '線上申請' not in deadline['value']


def test_partial_fee_expands_to_identity_and_exemption():
    raw='二、報名費用：具有效志工服務證者免費；其他參加者\n每人450元。\n三、活動時間：116年5月4日。'
    data={'amount':{'value':'450元','evidence':'每人450元。'}}
    amount=field(app.validate_extraction(data,raw),'amount')
    assert '志工服務證' in amount['value'] and '免費' in amount['value'] and '450元' in amount['value']
    assert '活動時間' not in amount['value']


def test_empty_section_does_not_borrow_the_next_section():
    raw='應備文件：\n申請期限：116年5月4日'
    assert field(app.validate_extraction({},raw),'required_documents')['value']==''


def test_fee_section_stops_at_numbered_prose_without_a_colon():
    raw='二、報名費用：一般民眾每人480元，持有效識別證者免費\n三、全程出席者可取得證明。'
    value=field(app.validate_extraction({},raw),'amount')['value']
    assert '免費' in value and '出席' not in value


def test_wrapped_conditional_deadline_keeps_eligibility():
    raw='若申請人在116年5月1日至5月7日間失業且不及備妥文件，\n得先送申請書，並於116年5月14日前完成補件。\n二、其他事項：另行通知。'
    result=app.validate_extraction({'deadline':{'value':'116年5月14日','evidence':raw.splitlines()[1]}},raw)
    value=field(result,'deadline')['value']
    assert '5月7日' in value and '不及備妥' in value and '5月14日' in value
    assert '其他事項' not in value


def test_cost_word_without_a_price_is_not_a_fee():
    raw='申請人未領取其他就學費用補助。'
    result=app.validate_extraction({'amount':{'value':raw,'evidence':raw}},raw)
    assert field(result,'amount')['value']==''


def test_deadline_expansion_does_not_prepend_a_separate_reservation_date():
    raw='新預約日期：2028年8月19日\n如無法配合，請於2028年8月3日前提出取消。\n應備文件：預約單'
    result=app.validate_extraction({'deadline':{'value':'2028年8月3日','evidence':raw.splitlines()[1]}},raw)
    assert field(result,'deadline')['value']==raw.splitlines()[1]
    assert '8月19日' not in field(result,'deadline')['value']


def test_deadline_keeps_conditional_eligibility_dates_in_wrapped_prose():
    raw='原活動日期：2028年8月19日\n若申請人於8月1日至8月5日間符合資格，\n得於8月12日前提出申請。'
    result=app.validate_extraction({'deadline':{'value':'8月12日','evidence':raw.splitlines()[2]}},raw)
    value=field(result,'deadline')['value']
    assert '8月1日' in value and '8月5日' in value and '8月12日' in value
    assert '8月19日' not in value
