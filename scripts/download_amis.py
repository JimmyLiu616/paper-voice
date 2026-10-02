"""Download pinned public Amis translation/TTS files; never upload model weights."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MODELS = [
    ('ILRDF/nllb-600m-formosan-all-finetune-v2', '317a939dd0a77688422a81d36b5fdab81b8ab456',
     'nllb-formosan', '9b9b858f6afebaecfc8fb81d3459820b23459ee315e5b3aaffb081d68e0e9dcb'),
    ('facebook/mms-tts-ami', 'd61903189d7641fc6482ec4d949898bca321ef38',
     'mms-tts-ami', 'f37d58ecd80663ed4e47d3108209e0836761cafaa5aa1d471d9339de32441453'),
]


def main():
    os.environ['HF_HUB_OFFLINE'] = '0'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HOME'] = str(ROOT/'.runtime/hf-cache')
    from huggingface_hub import snapshot_download
    remaining = sum(size for name,size in [('nllb-formosan',2_500_000_000),('mms-tts-ami',150_000_000)]
                    if not (ROOT/'.runtime'/name/'model.safetensors').is_file())
    if shutil.disk_usage(ROOT).free < remaining + 1_000_000_000:
        raise SystemExit('Insufficient free disk space for models plus 1 GB reserve.')
    report=[]
    for repo,revision,folder,expected in MODELS:
        target=ROOT/'.runtime'/folder
        snapshot_download(repo,revision=revision,token=False,local_dir=target,max_workers=2,
            allow_patterns=['*.json','*.safetensors','*.model','README.md','LICENSE*'])
        files=[]
        for path in sorted(target.iterdir()):
            if not path.is_file():continue
            with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
            if path.name=='model.safetensors' and digest!=expected:
                raise RuntimeError('Model checksum mismatch: '+repo)
            files.append({'name':path.name,'bytes':path.stat().st_size,'sha256':digest})
        report.append({'repo':repo,'revision':revision,'license':'CC BY-NC 4.0','files':files})
        print('Verified '+repo,flush=True)
    out=ROOT/'evaluation/amis-v1';out.mkdir(exist_ok=True)
    (out/'downloads.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
