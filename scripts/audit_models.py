"""Read-only audit of project model pins and globally installed Ollama names."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
try:
    from scripts.model_policy import policy, verify_files, classify_installed, ModelPolicyError
except ModuleNotFoundError:
    from model_policy import policy, verify_files, classify_installed, ModelPolicyError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-files',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    data=policy();errors=[];installed=[];loaded=[]
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as response:
            tags=json.load(response)['models']
        installed=[{'name':m['name'],'digest':m['digest'],'classification':classify_installed(m['name'])} for m in tags]
        with urllib.request.urlopen('http://127.0.0.1:11434/api/ps',timeout=5) as response:
            loaded=[m['name'] for m in json.load(response)['models']]
    except (OSError,ValueError,KeyError) as exc:
        errors.append('Ollama inventory unavailable: '+type(exc).__name__)
    actual={m['name']:m['digest'] for m in installed}
    checked=[]
    for entry in data['approved_models']:
        if not entry['serving']:continue
        row={'model':entry['id'],'status':'not_checked'}
        if entry.get('runtime_tag'):
            row['status']='verified' if actual.get(entry['runtime_tag'])==entry['ollama_digest'] else 'missing_or_mismatched'
        elif args.check_files:
            try:verify_files(entry['id']);row['status']='verified'
            except ModelPolicyError as exc:row.update(status='missing_or_mismatched',error=str(exc))
        if row['status']=='missing_or_mismatched':errors.append('Not ready: '+entry['id'])
        checked.append(row)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'policy_version':data['version'],
        'scope':'Paper Voice serving model pins plus Ollama inventory; not a whole-computer compliance certificate',
        'checked':checked,'installed_ollama':installed,'loaded_ollama':loaded,'errors':errors,
        'passed':not errors,'files_checked':args.check_files,'deleted_or_unloaded':False}
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n',encoding='utf8')
    print(text)
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
