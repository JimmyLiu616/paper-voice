"""Action source selection retains routes and who must perform a conditional step."""
import pytest
from app import source_action, validate_extraction


def action(raw, fact=None):
    return next(f for f in validate_extraction({'action': fact or {}}, raw)['fields'] if f['key'] == 'action')


def test_numbered_method_section_retains_both_routes_without_next_section():
    raw = ('提出申請補助時仍未就業。\n'
           '三、申請方式：\n'
           '（一）線上申請：請至網站填寫表單。\n'
           '（二）紙本申請：備妥文件，\n'
           '以掛號寄到服務中心。\n'
           '四、費用：免收費。')
    field = action(raw)
    assert field['value'] == '\n'.join(raw.splitlines()[2:5])
    assert field['evidence'] == '\n'.join(raw.splitlines()[1:5])
    assert '未就業' not in field['value'] and '免收費' not in field['value']


@pytest.mark.parametrize('raw', ['提出申請補助時仍未就業。', '申請填寫資料不完整。', '申請繳交文件期限另訂。'])
def test_application_noun_does_not_create_an_imperative(raw):
    assert source_action(raw) is None
    assert action(raw)['value'] == ''


def test_real_instruction_after_application_eligibility_is_selected():
    raw = '提出申請補助時仍未就業。\n請到服務櫃台填寫申請表。'
    assert action(raw)['value'] == raw.splitlines()[1]


def test_wrapped_proxy_instruction_keeps_the_condition():
    raw = ('姓名：\n本人如不克親自辦理，委託他人代辦\n'
           '者，請填委託書，並請代理人出示證件\n英文說明另列。')
    value = '\n'.join(raw.splitlines()[1:3])
    assert action(raw)['value'] == value
    assert action(raw)['evidence'] == value


@pytest.mark.parametrize('prefix', ['', '無關表格欄位\n', '本人如不克親自辦理。\n'])
def test_orphaned_continuation_is_not_presented_as_a_full_instruction(prefix):
    raw = prefix + '者，請填委託書。'
    assert source_action(raw) is None
    assert action(raw)['value'] == ''


def test_multiple_method_sections_do_not_arbitrarily_override_model():
    raw = '報名方式：請在線上登記。\n繳交方式：請到櫃台繳交。'
    fact = {'value': '請到櫃台繳交。', 'evidence': raw.splitlines()[1]}
    assert action(raw, fact)['value'] == fact['value']


def test_method_stops_before_standalone_note():
    raw = '辦理方式：\n（一）填表。\n（二）交到櫃台。\n※備註\n下月暫停開放。'
    assert action(raw)['value'] == '\n'.join(raw.splitlines()[1:3])


def test_completed_work_exemption_does_not_replace_main_instruction():
    raw = '請於期限前補交文件。\n如已完成補件請忽略通知。'
    assert action(raw)['value'] == raw.splitlines()[0]


def test_urls_are_not_section_headings_and_broken_source_urls_are_not_rewritten():
    raw = ('三、申請方式：\n（一）線上：請到下列網站下載表單。\n'
           'https://example.org/form，並至預約平台：h\n'
           'ttps://example.org/book完成登記。\n'
           '（二）紙本：請將表單寄到服務臺。\n'
           '四、費用：免收費。')
    assert action(raw)['value'] == '\n'.join(raw.splitlines()[1:5])
    assert '平台：h\nttps://' in action(raw)['value']
