import json
from copy import deepcopy

import pytest

from scripts.validate_document_trainer_cuda import ROOT, fixture_inputs
from scripts.verify_document_lora import same_outputs


def test_pinned_fixture_is_explicitly_unreviewed_and_not_independent():
    fixture = json.loads((ROOT/'training/smoke-fixture.json').read_text(encoding='utf-8'))
    output, manifest = fixture_inputs(fixture)
    assert manifest['human_reviewed'] is False
    assert manifest['same_fixture_train_and_dev'] is True
    assert manifest['quality_improvement_evaluated'] is False
    assert output['train'][0]['messages'] == output['dev'][0]['messages']
    assert output['train'][0]['human_reviewed'] is False
    assert 'review' not in output['train'][0]


@pytest.mark.parametrize('key,value', [('human_reviewed',True), ('document','另一份文件'),
                                     ('answer','不同標籤'), ('source_id','new-source')])
def test_runner_cannot_accept_other_data_or_fabricated_review(key, value):
    fixture = json.loads((ROOT/'training/smoke-fixture.json').read_text(encoding='utf-8'))
    changed = deepcopy(fixture); changed[key] = value
    with pytest.raises(ValueError, match='exact original'):
        fixture_inputs(changed)


def test_reproduction_allows_timing_change_but_rejects_content_or_identity_change():
    expected = [{'source_id':'one', 'output':'免交回', 'ended_with_eos':True, 'elapsed_seconds':1}]
    actual = [dict(expected[0], elapsed_seconds=2)]
    assert same_outputs(expected, actual)
    assert not same_outputs(expected, [dict(actual[0], output='須交回')])
    assert not same_outputs(expected, [dict(actual[0], source_id='two')])
    assert not same_outputs(expected, [dict(actual[0], ended_with_eos=False)])
    assert not same_outputs(expected, [])
