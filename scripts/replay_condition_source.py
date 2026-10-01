"""Compare validators on saved real generations; publish only hashes and counts."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='public-v11')
    args = parser.parse_args()
    if not args.run.replace('-', '').replace('_', '').isalnum():
        parser.error('Invalid run')
    source = ROOT / '.runtime/public-documents/runs' / args.run
    baseline = ROOT / '.runtime/condition-source-v1/baseline-app.py'
    context = vars(app).copy()
    node = next(n for n in ast.parse(baseline.read_text(encoding='utf-8')).body
                if isinstance(n, ast.FunctionDef) and n.name == 'validate_extraction')
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(baseline), 'exec'), context)
    results = [json.loads(line) for line in (source / 'results.jsonl').read_text(encoding='utf-8').splitlines()]
    generations = [json.loads(line) for line in (source / 'generations.jsonl').read_text(encoding='utf-8').splitlines()]
    by_id = {r['id']: r for r in results}
    rows = []
    for generation in generations:
        if generation['operation'] != 'extraction':
            continue
        record = by_id[generation['case_id']]
        raw = record['result']['raw_text']
        data = app.Extraction.model_validate_json(generation['output']).model_dump()
        before, after = context['validate_extraction'](data, raw), app.validate_extraction(data, raw)
        a, b = ({f['key']: f for f in output['fields']} for output in (before, after))
        changed = [key for key in a if a[key] != b[key]]
        assert set(changed) <= {'conditions'}
        assert all(app.normalized(f['evidence']) in app.normalized(raw)
                   for f in after['fields'] if f['state'] == 'source_matched')
        checks = []
        for check in record['checks']:
            def passed(fields):
                value = fields[check['field']]['value']
                return not value if check.get('empty') else all(
                    any(app.normalized(token) in app.normalized(value) for token in group)
                    for group in check['groups'])
            checks.append({'field': check['field'], 'before': passed(a), 'after': passed(b)})
        old_condition = a['conditions']['value']
        retained = not old_condition or app.normalized(old_condition) in app.normalized('\n'.join(after['summary']))
        assert retained
        rows.append({'id': record['id'], 'changed_fields': changed, 'checks': checks,
                     'previous_condition_retained_in_summary': retained,
                     'recorded_fields_match_baseline': record['result']['fields'] == before['fields'],
                     'recorded_fields_match_candidate': record['result']['fields'] == after['fields']})
    assert len(rows) == len(results) == 5
    report = {'run': args.run, 'baseline_app_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
              'candidate_app_sha256': app.APP_REVISION,
              'generation_log_sha256': hashlib.sha256((source / 'generations.jsonl').read_bytes()).hexdigest(),
              'results_sha256': hashlib.sha256((source / 'results.jsonl').read_bytes()).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'rows': rows,
              'before_passed': sum(c['before'] for r in rows for c in r['checks']),
              'after_passed': sum(c['after'] for r in rows for c in r['checks']),
              'planned': sum(len(r['checks']) for r in rows),
              'new_inference': False, 'training': False,
              'scope': 'Paired replay of the same saved outputs on existing development pages; no semantic accuracy or fine-tuning claim.'}
    out = ROOT / 'evaluation/condition-source-v1'
    out.mkdir(exist_ok=True)
    destination = out / (args.run + '-replay.json')
    with destination.open('x', encoding='utf-8', newline='\n') as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
