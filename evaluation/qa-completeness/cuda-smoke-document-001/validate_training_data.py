"""Validate explicitly reviewed document-understanding JSONL; never train or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'deadline', 'required_documents', 'amount', 'conditions'}


def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text))


def validate(rows, reserved_ids=(), reserved_texts=()):
    errors = []
    groups = {}
    seen = set()
    reserved_hashes = {hashlib.sha256(normalize(t).encode()).hexdigest() for t in reserved_texts}
    for index, row in enumerate(rows, 1):
        def fail(reason): errors.append(f'row {index}: {reason}')
        if not isinstance(row, dict):
            fail('expected an object'); continue
        if row.get('schema') != 'paper-voice-understanding-v1': fail('unsupported schema')
        if row.get('rights_confirmed') is not True or row.get('human_reviewed') is not True:
            fail('rights and human review must be explicitly confirmed')
        for key in ['source_id', 'family', 'license', 'document']:
            if not isinstance(row.get(key), str) or not row[key].strip(): fail(f'missing {key}')
        split = row.get('split')
        if split not in ['train', 'dev', 'test']: fail('invalid split'); continue
        document = row.get('document', '')
        if not isinstance(document, str): continue
        digest = hashlib.sha256(normalize(document).encode()).hexdigest()
        if row.get('source_id') in reserved_ids or row.get('family') in reserved_ids or digest in reserved_hashes:
            fail('existing evaluation document cannot enter this new training experiment')
        for kind, value in [('source_id', row.get('source_id')), ('family', row.get('family')), ('text', digest)]:
            if not isinstance(value, str): continue
            key = (kind, value)
            if key in groups and groups[key] != split: fail(f'{kind} appears in more than one split')
            groups[key] = split
        if digest in seen: fail('duplicate document; keep augmentation within one source record')
        seen.add(digest)
        fields = row.get('fields')
        if not isinstance(fields, dict) or set(fields) != FIELDS: fail('require exactly the four focus fields')
        else:
            for key, value in fields.items():
                if not isinstance(value, str) or (value and (not normalize(value) or normalize(value) not in normalize(document))):
                    fail(f'{key} must be empty or a verbatim document span')
        questions = row.get('questions')
        if not isinstance(questions, list) or not questions: fail('missing questions'); continue
        for question in questions:
            if not isinstance(question, dict): fail('invalid question'); continue
            if not all(isinstance(question.get(k), str) and question[k].strip() for k in ['question', 'answer']):
                fail('question and answer must be nonempty strings')
            quotes = question.get('evidence')
            found = question.get('found')
            if not isinstance(found, bool) or not isinstance(quotes, list): fail('invalid found/evidence'); continue
            if bool(quotes) != found: fail('found must agree with evidence availability')
            if any(not isinstance(q, str) or not q.strip() or normalize(q) not in normalize(document) for q in quotes):
                fail('question evidence not present verbatim in document')
    return errors


def reserved_evaluation_sources():
    manifest=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))['documents']
    ids=[value for r in manifest for value in (r['id'],r['family'])]
    texts=[r['reference'] for r in manifest]
    public=ROOT/'evaluation/public-documents/sources.json'
    if public.exists():
        ids.extend(s['id'] for s in json.loads(public.read_text(encoding='utf-8'))['sources'])
    verifier=ROOT/'evaluation/answer-verification/cases.json'
    if verifier.exists():
        for case in json.loads(verifier.read_text(encoding='utf-8'))['cases']:
            ids.extend([case['id'],'answer-verification:'+case['family']])
            texts.append(case['document'])
    return ids,texts


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    rows = []
    for path in args.files:
        rows.extend(json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip())
    reserved_ids,reserved_texts=reserved_evaluation_sources()
    errors = validate(rows,reserved_ids,reserved_texts)
    if not rows: errors.append('no records')
    report = {'rows': len(rows), 'splits': sorted({r['split'] for r in rows if isinstance(r, dict) and isinstance(r.get('split'), str)}),
              'valid': not errors, 'errors': errors, 'note': 'Structural checks only; no training, semantic approval or upload.'}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == '__main__': main()
