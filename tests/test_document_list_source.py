"""A reformatted document list cannot bypass source and obligation checks."""
import pytest

from app import document_list_source, validate_extraction


def documents(data, raw):
    return next(f for f in validate_extraction({'required_documents': data}, raw)['fields']
                if f['key'] == 'required_documents')


def test_reformatted_list_restores_source_instruction_with_qualifiers():
    raw = ('一、活動說明：歡迎申請借用。\n'
           '（一）委託辦理：申請人應填寫借用申請書並備妥代理人證件，\n'
           '於開館時間交到服務臺；本人辦理者不需代理人證件。\n'
           '二、費用：免收費。')
    quote = '申請人應填寫借用申請書並備妥代理人證件，於開館時間交到服務臺'
    field = documents({'value': '借用申請書、代理人證件', 'evidence': quote}, raw)
    expected = '\n'.join(raw.splitlines()[1:3])
    assert field['state'] == 'source_matched'
    assert field['value'] == field['evidence'] == expected
    assert '本人辦理者不需代理人證件' in field['value']
    assert '免收費' not in field['value']


@pytest.mark.parametrize('value', [
    '借用申請書、護照正本',
    '代理人證件、借用申請書',
    '借用申請書、借用申請書',
    '借用申請書、代理人證件、繳費收據',
    '借用申請書、100元',
])
def test_changed_added_reordered_or_non_document_items_are_not_recovered(value):
    quote = '申請人應填寫借用申請書並備妥代理人證件。'
    field = documents({'value': value, 'evidence': quote}, quote)
    assert field['state'] == 'needs_review' and field['value'] == ''


@pytest.mark.parametrize('quote', [
    '附件：申請書及交通資料。',
    '網站提供申請書及交通資料，請參閱說明。',
    '無須填寫申請書，也無須準備交通資料。',
    '不需填寫申請書，也不需準備交通資料。',
])
def test_enclosures_reference_material_or_exemptions_do_not_become_requirements(quote):
    field = documents({'value': '申請書、交通資料', 'evidence': quote}, quote)
    assert field['value'] == ''


def test_evidence_must_be_verbatim_and_unique():
    quote = '申請人應填寫借用申請書並備妥代理人證件。'
    value = '借用申請書、代理人證件'
    assert document_list_source(quote.replace('應填寫', '無须填寫'), value, quote) == ''
    assert document_list_source(quote + '\n\n' + quote, value, quote) == ''


def test_source_line_breaks_and_original_characters_survive():
    raw = '請填寫申請書１份，\n另須檢附收據２份。'
    value = '申請書1份\n收據2份'
    assert document_list_source(raw, value, raw) == raw


def test_existing_valid_document_quote_is_unchanged():
    quote = '請攜帶借用證及領取單。'
    field = documents({'value': '借用證及領取單', 'evidence': quote}, quote)
    assert field['value'] == '借用證及領取單' and field['evidence'] == quote
