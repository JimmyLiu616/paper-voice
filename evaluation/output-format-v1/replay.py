"""Replay three saved model failures without regenerating or publishing transcripts."""
import hashlib
import json
from pathlib import Path
import sys
import time

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


def main():
    source = ROOT / '.runtime/core-model-comparison/ministral-core-v1/results.jsonl'
    rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    changes = []
    for model, key in [('gemma', 'location'), ('ministral', 'contact')]:
        row = next(r for r in rows if r['id'] == 'moi-police-form-109-p4' and r['model'] == model)
        result = row['result']
        before = next(f for f in result['fields'] if f['key'] == key)
        assert before['state'] == 'source_matched'
        replay = app.validate_extraction({key: before}, result['raw_text'])
        after = next(f for f in replay['fields'] if f['key'] == key)
        assert after['state'] == 'needs_review' and after['value'] == ''
        changes.append({'id': row['id'], 'model': model, 'field': key,
                        'before': before, 'after': after})

    row = next(r for r in rows if r['id'] == 'taipei-tuition-115-p3' and r['model'] == 'ministral')
    qa = next(q for q in row['questions'] if q['answer']['answer'] == 'found=true')
    original_generate = app.generate
    async def saved_generate(*args, **kwargs):
        return json.dumps(qa['answer'], ensure_ascii=False)
    try:
        app.generate = saved_generate
        with TestClient(app.app) as client:
            app.jobs['saved-format'] = {'created': time.time(), 'status': 'done', 'result': row['result']}
            response = client.post('/api/ask', headers={'X-PaperVoice': 'local-ui'},
                                   json={'job_id': 'saved-format', 'question': qa['question']['text']})
            assert response.status_code == 502
            changes.append({'id': row['id'], 'model': 'ministral', 'field': 'answer',
                            'before': qa['answer']['answer'], 'status': response.status_code,
                            'after': response.json()})
    finally:
        app.generate = original_generate
    report = {'app_sha256': app.APP_REVISION,
              'source_results_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Three observed failures replayed from saved output; no model generation or accuracy estimate.',
              'passed': len(changes), 'changes': changes}
    output = ROOT / 'evaluation/output-format-v1'
    output.mkdir(exist_ok=False)
    (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': len(changes), 'app_sha256': app.APP_REVISION}))


if __name__ == '__main__':
    main()
