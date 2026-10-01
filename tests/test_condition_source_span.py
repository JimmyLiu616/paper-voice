"""Source repair must preserve restrictions and cannot invent or trim qualifiers."""
import pytest

from app import condition_source_span, validate_extraction


def test_wrong_evidence_recovers_full_original_restriction_and_keeps_other_exception():
    raw = ('一、處理需三個工作天；若需另行查詢，不在此限。\n'
           '二、申請人有下列情形者，不予借用：\n'
           '（一）尚有逾期器材未歸還者。\n'
           '（二）借用證已過有效期限者。\n'
           '三、其他資訊：請參閱網站。')
    value = '申請人有下列情形者，不予借用：\n（一）尚有逾期器材未歸還者。\n（二）借用證已過有效期限者。'
    result = validate_extraction({'conditions': {'value': value, 'evidence': '其他資訊：請參閱網站。'}}, raw)
    field = next(f for f in result['fields'] if f['key'] == 'conditions')
    assert field['value'] == '二、' + value
    assert field['evidence'] in raw
    assert field['state'] == 'source_matched'
    assert '文件提醒：一、處理需三個工作天；若需另行查詢，不在此限。' in result['summary']


@pytest.mark.parametrize('raw,value', [
    ('禁止攜帶未密封容器。', '禁止攜帶已密封容器。'),
    ('未滿18歲不得報名。', '未滿8歲不得報名。'),
    ('並非禁止攝影。', '禁止攝影。'),
    ('未經同意者\n不得借用器材。', '不得借用器材。'),
    ('僅限發生下列情形時：\n（一）禁止借用器材。', '禁止借用器材。'),
    ('未經同意者\n不得借用器材，但完成登記者除外。', '不得借用器材'),
    ('禁止攝影，但開幕活動除外。', '禁止攝影'),
    ('甲區：\n禁止攝影。\n乙區：\n禁止攝影。', '禁止攝影。'),
    ('不得借用' + '器材' * 610 + '。', '不得借用' + '器材' * 610 + '。'),
    ('請到櫃台領取號碼牌。', '請到櫃台領取號碼牌。'),
])
def test_recovery_refuses_changed_ambiguous_incomplete_or_nonconditional_text(raw, value):
    assert condition_source_span(raw, value) == ''


def test_line_markers_and_original_full_width_digits_survive_normalized_matching():
    raw = '（一）未滿１８歲不得報名。'
    assert condition_source_span(raw, '未滿18歲不得報名') == raw


def test_existing_valid_evidence_does_not_change():
    raw = '應備文件：申請表。\n禁止攜帶未密封容器。'
    value = '禁止攜帶未密封容器。'
    result = validate_extraction({'conditions': {'value': value, 'evidence': value}}, raw)
    field = next(f for f in result['fields'] if f['key'] == 'conditions')
    assert field['value'] == value and field['evidence'] == value
