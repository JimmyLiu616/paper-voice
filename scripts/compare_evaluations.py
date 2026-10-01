"""Summarize recorded runs, preserving split and variant distinctions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCUS = {'deadline', 'required_documents', 'amount', 'conditions'}


def main():
    output = []
    for directory in sorted((ROOT/'evaluation/runs').iterdir()):
        if (directory/'INVALID.md').exists():continue
        if not (directory/'summary.json').exists(): continue
        summary=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
        metadata=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
        rows=[json.loads(line) for line in (directory/'results.jsonl').read_text(encoding='utf-8').splitlines()]
        checks=[c for r in rows for c in r.get('checks',[]) if c['field'] in FOCUS]
        output.append({'run':directory.name,'split':metadata['split'],'variants':metadata['variants'],
                       'purpose':metadata.get('purpose','reserved-evaluation' if metadata['split']=='test' else 'development'),
                       'document_families':len({r['id'] for r in rows}),'inputs':len(rows),
                       'all_fields':[summary['field_checks_passed'],summary['field_checks_total']],
                       'focus_fields':[sum(c['passed'] for c in checks),len(checks)],
                       'qa':[summary['qa_checks_passed'],summary['qa_checks_total']],
                       'errors':summary['errors'],'app_sha256':metadata['app_sha256']})
    result={'runs':output,'note':'Read split and variants separately: development, reserved images, and reference-text diagnostics are different comparisons. Multiple images per family are not independent. Test results opened for diagnosis are not fresh tests for future tuning. No fine-tuning performed.'}
    (ROOT/'evaluation/comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
