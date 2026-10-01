"""Read-only readiness report. Does not download weights or alter the serving environment."""
import argparse
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',choices=['serving','training'],default='serving')
    args=parser.parse_args()
    import torch
    report={'environment':args.environment,'python':sys.version,'torch':torch.__version__,'torch_cuda_available':torch.cuda.is_available(),
        'disk_free_gib':round(shutil.disk_usage(ROOT).free/1024**3,2),
        'packages':{},'native_checkpoints':[],'eligible_training_rows':0,'issues':[],
        'note':'Read-only environment check. Smoke training is reported separately and is not evidence of task improvement.'}
    for name in ['transformers','peft','bitsandbytes','accelerate','datasets']:
        try:report['packages'][name]=metadata.version(name)
        except metadata.PackageNotFoundError:report['packages'][name]=None
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used','--format=csv,noheader'],capture_output=True,text=True,timeout=10)
        report['nvidia_smi']=result.stdout.strip()
    except (OSError,subprocess.TimeoutExpired):report['nvidia_smi']='unavailable'
    # Only explicitly staged native training checkpoints count; never use a TTS or CT2 file by mistake.
    native=ROOT/'.runtime/training-models'
    if native.exists():report['native_checkpoints']=[str(p.relative_to(ROOT)) for p in native.rglob('*.safetensors')]
    download_file=ROOT/'training/native-model-download.json'
    report['native_checkpoint_download_complete']=False
    if download_file.exists():
        download=json.loads(download_file.read_text(encoding='utf-8'))
        report['native_checkpoint_download_complete']=all(
            (ROOT/download['directory']/f['file']).is_file() and
            (ROOT/download['directory']/f['file']).stat().st_size==f['size'] for f in download['files'])
        report['checkpoint_verification']='Download digest record and current sizes checked here; the smoke runner verifies all SHA256 hashes again.'
    report['smoke_runs']=[]
    for path in sorted((ROOT/'.runtime/training-runs').glob('*/report.json')):
        run=json.loads(path.read_text(encoding='utf-8'))
        report['smoke_runs'].append({k:run.get(k) for k in ['name','status','optimizer_steps','quality_improvement_evaluated']})
    manifest=ROOT/'training/data/train.jsonl'
    if manifest.exists():
        rows=[json.loads(line) for line in manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
        from validate_training_data import validate,reserved_evaluation_sources
        errors=validate(rows,*reserved_evaluation_sources())
        report['data_errors']=errors
        report['eligible_training_rows']=sum(r.get('split')=='train' for r in rows) if not errors else 0
    if not report['torch_cuda_available']:report['issues'].append('No CUDA training runtime; set up a separate GPU environment before trying LoRA.')
    for name in ['peft','bitsandbytes','accelerate']:
        if report['packages'][name] is None:report['issues'].append(f'Missing training dependency: {name}')
    if not report['native_checkpoint_download_complete']:report['issues'].append('Native checkpoint download is absent or incomplete. Ollama GGUF / ASR CTranslate2 weights are inference artifacts.')
    report['gpu_environment_ready']=not report['issues']
    if not report['eligible_training_rows']:report['issues'].append('No reviewed, rights-confirmed training split. Dev/test fixtures must not be silently reused for training.')
    report['ready']=not report['issues']
    output=ROOT/'training';output.mkdir(exist_ok=True)
    name='preflight.json' if args.environment=='serving' else 'preflight-training.json'
    (output/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
