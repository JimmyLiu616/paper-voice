"""Recover list formatting only when every generated line agrees with the source."""
import pytest
import app


SOURCE = ('補助額度：以實際繳納數額為上限。\n'
          '(一)甲類學生每名18,800元。\n'
          '(二)乙類學生每名43,200元。\n'
          '※說明：不得重複申請。')


@pytest.mark.parametrize('value', [
    '甲類學生每名18,800元。\n乙類學生每名43,200元。',
    '甲類學生每名１８，８００元。\n\n乙類學生每名４３，２００元。',
])
def test_fee_list_restores_source_numbering_and_cap(value):
    result = app.validate_extraction({'amount': {'value': value, 'evidence': SOURCE}}, SOURCE)
    fee = next(f for f in result['fields'] if f['key'] == 'amount')
    assert fee['state'] == 'source_matched'
    assert fee['value'] == '以實際繳納數額為上限。\n(一)甲類學生每名18,800元。\n(二)乙類學生每名43,200元。'
    assert '不得重複申請' not in fee['evidence']


@pytest.mark.parametrize('value', [
    '甲類學生每名18,000元。\n乙類學生每名43,200元。',
    '甲類學生每名18,800元。\n丙類學生每名43,200元。',
    '乙類學生每名43,200元。\n甲類學生每名18,800元。',
    '甲類學生每名18,800元。\n甲類學生每名18,800元。',
    '8,800\n43,200',
    '18,800\n3,200',
    '甲類學生每名18,800元。、乙類學生每名43,200元。',
])
def test_changed_or_unverifiable_fee_list_stays_hidden(value):
    result = app.validate_extraction({'amount': {'value': value, 'evidence': SOURCE}}, SOURCE)
    fee = next(f for f in result['fields'] if f['key'] == 'amount')
    assert fee['state'] == 'needs_review'
    assert fee['value'] == fee['evidence'] == ''
