"""Compare old/new validators on one shared generated extraction, without re-OCR."""
import ast
import asyncio
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


async def main():
    source = ROOT / '.runtime/public-documents/runs/public-v8/app.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    current = ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
    old_functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_functions = {n.name: n for n in current.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name in ('normalized', 'labelled_facts', 'paragraph_context', 'deadline_paragraph', 'extract', 'generate'):
        assert ast.dump(old_functions[name]) == ast.dump(new_functions[name]), name
    context = vars(app).copy()
    exec(compile(ast.Module(body=[old_functions['validate_extraction']], type_ignores=[]), str(source), 'exec'), context)
    old_validate = context['validate_extraction']
    row = next(r for r in map(json.loads, (ROOT/'.runtime/public-documents/runs/public-v10/results.jsonl').read_text(encoding='utf-8').splitlines()) if r['id'] == 'taipei-tuition-115-p3')
    raw = row['result']['raw_text']
    original = app.validate_extraction
    captured = {}
    def paired(data, text):
        captured.update(data=data, before=old_validate(data, text), after=original(data, text))
        return captured['after']
    app.validate_extraction = paired
    try:
        await app.extract(raw)
    finally:
        app.validate_extraction = original
    out = ROOT/'.runtime/format-control-v1'
    out.mkdir(exist_ok=False)
    (out/'result.json').write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding='utf-8')
    changed = [a['key'] for a,b in zip(captured['before']['fields'], captured['after']['fields']) if a != b]
    report = {'id':row['id'], 'baseline_app_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'candidate_app_sha256':app.APP_REVISION, 'input_text_sha256':hashlib.sha256(raw.encode()).hexdigest(),
              'output_sha256':hashlib.sha256((out/'result.json').read_bytes()).hexdigest(),
              'same_generated_extraction_for_both_validators':True, 'changed_fields':changed,
              'scope':'Single diagnostic page with public-v10 transcript; fresh model extraction shared by old/new validators. Shared helpers and prompts checked structurally unchanged. Not a repeat end-to-end score.'}
    (ROOT/'evaluation/output-format-v2/paired-validation.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    asyncio.run(main())
