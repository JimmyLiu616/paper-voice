"""Diagnostics must detect regressions without asserting semantic correctness."""
from copy import deepcopy
import json
import pytest
from scripts.score_document_lora import compare, digest, norm, score, score_run

RAW = '費用：100元。已繳費者免再繳。承辦人未載明。'
REF = {'answer': '已繳費者免再繳。', 'found': True, 'evidence': ['已繳費者免再繳。']}


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


def rows():
    prompt = '測試資料，不是訓練素材。\n' + encoded({'document': RAW, 'question': '已繳費者要再繳嗎？'})
    item = {'source_id': 'unit-only', 'family': 'unit-only', 'task': 'qa-1', 'split': 'dev',
            'document_sha256': digest(norm(RAW).encode()),
            'messages': [{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': encoded(REF)}]}
    output = {k: item[k] for k in ('source_id', 'family', 'task', 'document_sha256')}
    output.update(prompt_sha256=digest(prompt.encode()), reference=encoded(REF), output=encoded(REF), ended_with_eos=True)
    return [item], [output], [deepcopy(output)]


def test_exact_output_is_a_reference_match_not_semantic_approval():
    result = compare(*rows())
    assert result['totals']['baseline']['strict_reference_pass'] == 1
    assert result['unchanged_outputs'] == 1
    assert result['task_quality_verified'] is result['deployed'] is False


def test_fenced_json_is_only_diagnostic_and_truncation_blocks_acceptance():
    result = score('```json\n' + encoded(REF) + '\n```', REF, RAW, 'qa-1', True)
    assert result['structure_valid'] and result['answer_exact'] and not result['strict_json']
    assert not result['strict_reference_pass']
    assert not score(encoded(REF), REF, RAW, 'qa-1', False)['strict_reference_pass']


@pytest.mark.parametrize('changes', [
    {'answer': '已繳費者需要再繳。'},
    {'evidence': ['費用：100元。']},
    {'evidence': ['免繳1000元。']},
])
def test_changed_negation_irrelevant_quote_or_invented_quote_fails_reference(changes):
    result = score(encoded(REF | changes), REF, RAW, 'qa-1', True)
    assert not result['strict_reference_pass']
    if changes == {'evidence': ['費用：100元。']}:
        assert result['evidence_source_match']  # Source presence alone is insufficient.


@pytest.mark.parametrize('prediction', [REF | {'found': 'true'}, REF | {'evidence': []}, REF | {'extra': 1}])
def test_invalid_qa_schema_is_not_scored_as_valid(prediction):
    result = score(encoded(prediction), REF, RAW, 'qa-1', True)
    assert not result['structure_valid'] and not result['strict_reference_pass']


def test_duplicate_json_keys_are_rejected():
    text = '{"answer":"x","answer":"y","found":false,"evidence":[]}'
    assert not score(text, REF, RAW, 'qa-1', True)['strict_json']


def test_positive_and_refusal_regressions_are_distinct():
    absent = {'answer': '文件沒有提供。', 'found': False, 'evidence': []}
    assert score(encoded(REF), absent, RAW, 'qa-1', True)['unexpected_positive']
    assert score(encoded(absent), REF, RAW, 'qa-1', True)['missing_answer']


def test_changed_amount_and_missing_condition_count_individually():
    ref = {'deadline': '', 'required_documents': '', 'amount': '100元', 'conditions': '已繳費者免再繳。'}
    result = score(encoded(ref | {'amount': '1000元', 'conditions': ''}), ref, RAW, 'fields', True)
    assert sum(result['field_exact'].values()) == 2
    assert not result['field_source_match']['amount']
    assert not result['strict_reference_pass']


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'reference', 'prompt', 'document', 'test_split'])
def test_misaligned_pairs_cannot_report_improvement(change):
    items, baseline, adapter = rows()
    if change == 'missing': adapter.clear()
    elif change == 'duplicate': adapter.append(deepcopy(adapter[0]))
    elif change == 'reference': adapter[0]['reference'] = '{}'
    elif change == 'prompt': adapter[0]['prompt_sha256'] = '0' * 64
    elif change == 'document': items[0]['document_sha256'] = '0' * 64
    else: items[0]['split'] = 'test'
    with pytest.raises(ValueError):
        compare(items, baseline, adapter)


def test_changed_artifact_is_rejected_before_scoring(tmp_path):
    (tmp_path/'report.json').write_text(encoded({'status': 'completed-awaiting-quality-review',
        'artifacts_sha256': {'baseline-dev.jsonl': '0' * 64}}), encoding='utf-8')
    (tmp_path/'baseline-dev.jsonl').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='Changed artifact'):
        score_run(tmp_path)
