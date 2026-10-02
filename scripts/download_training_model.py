"""Download the pinned public native checkpoint; no account token or remote code."""
import hashlib
import json
import os
from pathlib import Path
import shutil
try:
    from scripts.model_policy import approved
except ModuleNotFoundError:
    from model_policy import approved

ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HOME']=str(ROOT/'.runtime/hf-train-cache')
os.environ['HF_HUB_OFFLINE']='0'
os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT']='120'


def main():
    from huggingface_hub import hf_hub_download
    manifest=json.loads((ROOT/'training/native-model-manifest.json').read_text(encoding='utf-8'))
    approved(manifest['model'], revision=manifest['revision'], serving=False)
    if manifest['gated'] or manifest['license']!='apache-2.0':
        raise ValueError('Expected the ungated Apache-2.0 checkpoint recorded in the manifest')
    names={'README.md','config.json','generation_config.json','model.safetensors.index.json',
           'model-00001-of-00002.safetensors','model-00002-of-00002.safetensors',
           'tokenizer.json','tokenizer_config.json','special_tokens_map.json','tekken.json',
           'chat_template.jinja','processor_config.json','params.json'}
    selected=[f for f in manifest['files'] if f['name'] in names]
    target=ROOT/'.runtime/training-models/ministral-3-3b-bf16'
    target.mkdir(parents=True,exist_ok=True)
    missing=sum(f['size'] for f in selected if not (target/f['name']).exists())
    if shutil.disk_usage(ROOT).free < missing+3*1024**3:
        raise RuntimeError('Not enough free disk space for the selected checkpoint plus 3 GiB reserve')
    records=[]
    for item in selected:
        print(json.dumps({'stage':'download','file':item['name'],'bytes':item['size']}),flush=True)
        path=Path(hf_hub_download(manifest['model'],item['name'],revision=manifest['revision'],
                                 local_dir=str(target),token=False))
        digest=hashlib.sha256()
        with path.open('rb') as file:
            for chunk in iter(lambda:file.read(1024*1024),b''):digest.update(chunk)
        sha=digest.hexdigest()
        if path.stat().st_size!=item['size']:raise ValueError('Size mismatch: '+item['name'])
        if item.get('lfs') and item['lfs']['sha256']!=sha:raise ValueError('SHA256 mismatch: '+item['name'])
        records.append({'file':item['name'],'size':item['size'],'sha256':sha})
        print(json.dumps({'stage':'verified','file':item['name']}),flush=True)
    record={'model':manifest['model'],'revision':manifest['revision'],'directory':str(target.relative_to(ROOT)),
            'files':records,'remote_code_executed':False,'consolidated_duplicate_downloaded':False}
    (ROOT/'training/native-model-download.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'status':'complete','files':len(records)}),flush=True)


if __name__=='__main__':main()
