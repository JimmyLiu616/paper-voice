"""Offline paired dev diagnostics; never infer, train, read test labels or deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('deadline', 'required_documents', 'amount', 'conditions')


def norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Non-JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant)


def valid_schema(value, task):
    if not isinstance(value, dict):
        return False
    if task == 'fields':
        return set(value) == set(FIELDS) and all(isinstance(value[k], str) for k in FIELDS)
    if not re.fullmatch(r'qa-[1-9][0-9]*', task):
        return False
    return (set(value) == {'answer', 'found', 'evidence'}
            and isinstance(value['answer'], str) and bool(value['answer'].strip())
            and type(value['found']) is bool and isinstance(value['evidence'], list)
            and all(isinstance(q, str) and bool(q.strip()) for q in value['evidence'])
            and (bool(value['evidence']) if value['found'] else not value['evidence']))


def score(output, reference, document, task, ended_with_eos):
    if not valid_schema(reference, task):
        raise ValueError('Invalid reference schema')
    result = {'strict_json': True, 'structure_valid': False, 'ended_with_eos': ended_with_eos,
              'strict_reference_pass': False}
    try:
        prediction = strict_json(output)
    except (ValueError, TypeError):
        result['strict_json'] = False
        # A fenced object can be inspected, but never becomes a strict format pass.
        match = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', output, re.S)
        try:
            prediction = strict_json(match.group(1)) if match else None
        except (ValueError, TypeError):
            prediction = None
    result['structure_valid'] = valid_schema(prediction, task)
    if not result['structure_valid']:
        return result
    source = norm(document)
    if task == 'fields':
        result['field_exact'] = {k: norm(prediction[k]) == norm(reference[k]) for k in FIELDS}
        result['field_source_match'] = {k: not prediction[k] or norm(prediction[k]) in source for k in FIELDS}
        result['unexpected_nonempty_fields'] = [k for k in FIELDS if not reference[k] and prediction[k]]
        matches = all(result['field_exact'].values()) and all(result['field_source_match'].values())
    else:
        result.update(found_matches=prediction['found'] == reference['found'],
                      unexpected_positive=prediction['found'] and not reference['found'],
                      missing_answer=reference['found'] and not prediction['found'],
                      answer_exact=norm(prediction['answer']) == norm(reference['answer']),
                      evidence_exact=[norm(q) for q in prediction['evidence']] == [norm(q) for q in reference['evidence']],
                      evidence_source_match=all(norm(q) in source for q in prediction['evidence']))
        matches = all(result[k] for k in ('found_matches', 'answer_exact', 'evidence_exact', 'evidence_source_match'))
    result['strict_reference_pass'] = bool(result['strict_json'] and ended_with_eos and matches)
    return result


def index(rows):
    result = {}
    for row in rows:
        key = (row['source_id'], row['task'])
        if key in result:
            raise ValueError('Duplicate source/task pair')
        result[key] = row
    return result


def compare(inputs, baseline, adapter, *, document_hash_mode='normalized'):
    if document_hash_mode not in ('normalized', 'raw'):
        raise ValueError('Unknown document hash convention')
    inputs, baseline, adapter = map(index, (inputs, baseline, adapter))
    if not inputs or inputs.keys() != baseline.keys() or inputs.keys() != adapter.keys():
        raise ValueError('Missing or extra paired dev tasks')
    rows = []
    for key, item in inputs.items():
        if item['split'] != 'dev':
            raise ValueError('Only dev inputs can be scored')
        prompt = item['messages'][0]['content']
        document = strict_json(prompt.split('\n', 1)[1])['document']
        hash_text = norm(document) if document_hash_mode == 'normalized' else document
        if digest(hash_text.encode()) != item['document_sha256']:
            raise ValueError('Document hash mismatch')
        target = item['messages'][1]['content']
        reference = strict_json(target)
        row = {'source_id': key[0], 'task': key[1]}
        for label, outputs in (('baseline', baseline), ('adapter', adapter)):
            output = outputs[key]
            if (any(output[k] != item[k] for k in ('family', 'document_sha256'))
                    or output['prompt_sha256'] != digest(prompt.encode()) or output['reference'] != target):
                raise ValueError('Prompt, source or reference mismatch')
            if type(output['ended_with_eos']) is not bool or not isinstance(output['output'], str):
                raise ValueError('Invalid generation record')
            row[label] = score(output['output'], reference, document, key[1], output['ended_with_eos'])
        row['unchanged_output'] = baseline[key]['output'] == adapter[key]['output']
        rows.append(row)
    totals = {}
    for label in ('baseline', 'adapter'):
        totals[label] = {metric: sum(bool(r[label].get(metric, False)) for r in rows)
                         for metric in ('strict_json', 'structure_valid', 'ended_with_eos', 'strict_reference_pass',
                                        'unexpected_positive', 'missing_answer')}
        totals[label]['field_exact'] = sum(sum(r[label].get('field_exact', {}).values()) for r in rows)
        totals[label]['field_checks_planned'] = 4 * sum(r['task'] == 'fields' for r in rows)
        totals[label]['qa_planned'] = sum(r['task'].startswith('qa-') for r in rows)
    return {'tasks': len(rows), 'totals': totals, 'rows': rows,
            'new_strict_reference_passes': sum(not r['baseline']['strict_reference_pass'] and r['adapter']['strict_reference_pass'] for r in rows),
            'lost_strict_reference_passes': sum(r['baseline']['strict_reference_pass'] and not r['adapter']['strict_reference_pass'] for r in rows),
            'unchanged_outputs': sum(r['unchanged_output'] for r in rows),
            'task_quality_verified': False, 'deployed': False, 'human_review_required': True,
            'limitations': ['Strict reference matching may reject valid paraphrases.',
                           'Source-matched evidence may still be irrelevant or fail to support the answer.',
                           'A dev diagnostic is not held-out quality, training success or deployment approval.',
                           'Markdown fences are inspected diagnostically but never pass strict JSON.']}


def score_run(directory):
    report = strict_json((directory/'report.json').read_text(encoding='utf-8'))
    if report['status'] not in ('completed-synthetic-flow-only', 'completed-awaiting-quality-review'):
        raise ValueError('Training run is not complete')
    hashes = {}
    for name in ('baseline-dev.jsonl', 'adapter-dev.jsonl', 'inputs/manifest.json'):
        hashes[name] = digest((directory/name).read_bytes())
        if hashes[name] != report['artifacts_sha256'][name]:
            raise ValueError('Changed artifact: ' + name)
    manifest = strict_json((directory/'inputs/manifest.json').read_text(encoding='utf-8'))
    hashes['inputs/dev.jsonl'] = digest((directory/'inputs/dev.jsonl').read_bytes())
    if hashes['inputs/dev.jsonl'] != manifest['outputs']['dev.jsonl']['sha256']:
        raise ValueError('Changed dev input')
    def read(name):
        return [strict_json(line) for line in (directory/name).read_text(encoding='utf-8').splitlines() if line.strip()]
    purpose = report['purpose']
    if purpose not in ('synthetic-feasibility-only', 'reviewed-document-text-experiment'):
        raise ValueError('Unknown run purpose')
    expected_status = 'completed-synthetic-flow-only' if purpose == 'synthetic-feasibility-only' else 'completed-awaiting-quality-review'
    if report['status'] != expected_status or manifest.get('purpose', 'reviewed-document-text-experiment') != purpose:
        raise ValueError('Run purpose mismatch')
    # The existing fixed smoke runner hashes raw text; reviewed bundles use NFKC/no whitespace.
    mode = 'raw' if purpose == 'synthetic-feasibility-only' else 'normalized'
    result = compare(read('inputs/dev.jsonl'), read('baseline-dev.jsonl'), read('adapter-dev.jsonl'), document_hash_mode=mode)
    result.update(purpose=report['purpose'], same_fixture_train_and_dev=report['same_fixture_train_and_dev'],
                  artifacts_sha256=hashes, scorer_sha256=digest(Path(__file__).read_bytes()),
                  training_report_sha256=digest((directory/'report.json').read_bytes()), test_labels_read=False,
                  document_hash_mode=mode,
                  gpu_used=False, model_generation_performed=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Invalid run name')
    directory = ROOT/'.runtime/document-training'/args.name
    try:
        result = score_run(directory)
        with (directory/'paired-dev-metrics.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'scored': False, 'error': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({k:result[k] for k in ('tasks','totals','unchanged_outputs','task_quality_verified')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
