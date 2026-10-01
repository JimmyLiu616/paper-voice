"""Replay the saved formatting failure against old/new validators without inference."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app


def main():
    old_path=ROOT/'.runtime/public-documents/runs/public-v10/app.py'
    source=ROOT/'.runtime/format-control-v1/result.json'
    tree=ast.parse(old_path.read_text(encoding='utf-8'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_extraction')
    context=vars(app).copy()
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(old_path),'exec'),context)
    saved=json.loads(source.read_text(encoding='utf-8'))
    raw=saved['after']['raw_text']
    before=context['validate_extraction'](saved['data'],raw)
    after=app.validate_extraction(saved['data'],raw)
    old_fields={f['key']:f for f in before['fields']}
    differences=[f['key'] for f in after['fields'] if f!=old_fields[f['key']]]
    fee=next(f for f in after['fields'] if f['key']=='amount')
    assert differences==['amount']
    assert old_fields['amount']['state']=='needs_review' and fee['state']=='source_matched'
    assert all(token in fee['value'] for token in ('18,800','43,200','實際繳納','公立','私立'))
    assert app.normalized(fee['evidence']) in app.normalized(raw)
    report={'app_sha256':app.APP_REVISION,'baseline_app_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),
            'saved_output_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'changed_fields':differences,'before_state':old_fields['amount']['state'],'after_state':fee['state'],
            'full_source_quote_preserved':True,'two_amounts_roles_and_cap_preserved':True,
            'scope':'One saved real extraction shared by both validators; no new generation, fine-tuning or general accuracy claim.'}
    out=ROOT/'evaluation/fee-lines-v1';out.mkdir(exist_ok=False)
    (out/'replay.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
