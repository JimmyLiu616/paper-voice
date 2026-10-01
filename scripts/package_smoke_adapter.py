"""Package the verified synthetic smoke adapter, without base weights or local paths."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = ROOT / '.runtime/training-runs/smoke-001'
    adapter = run / 'adapter/adapter_model.safetensors'
    report = json.loads((ROOT / 'training/lora-smoke-report.json').read_text(encoding='utf-8'))
    verification = json.loads((run / 'fresh-process-verification.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256(adapter.read_bytes()).hexdigest()
    if not verification['passed'] or digest != verification['adapter_sha256'] or digest != report['adapter_sha256']:
        raise ValueError('Adapter no longer matches verified experiment')
    config = json.loads((run / 'adapter/adapter_config.json').read_text(encoding='utf-8'))
    if config['base_model_name_or_path'] != report['model'] or config['revision'] != report['revision']:
        raise ValueError('Base model provenance mismatch')
    selected = {
        'adapter_model.safetensors': adapter,
        'adapter_config.json': run / 'adapter/adapter_config.json',
        'README.md': ROOT / 'training/ADAPTER_RELEASE.md',
        'LICENSE': ROOT / 'third_party/Ministral-3-LICENSE.txt',
        'lora-smoke-report.json': ROOT / 'training/lora-smoke-report.json',
        'fresh-process-verification.json': run / 'fresh-process-verification.json',
        'smoke-fixture.json': ROOT / 'training/smoke-fixture.json',
    }
    contents = {name: path.read_bytes() for name, path in selected.items()}
    contents['NOTICE'] = (
        'Paper Voice smoke-001 experimental LoRA adapter.\n'
        'Base model by Mistral AI: mistralai/Ministral-3-3B-Instruct-2512-BF16.\n'
        'Modified by the Paper Voice project: one synthetic QLoRA optimizer step.\n'
        'Apache-2.0; see LICENSE. Not deployed; no task-quality improvement claim.\n'
    ).encode()
    for name, data in contents.items():
        if name.endswith('.safetensors'):
            continue
        text = data.decode('utf-8')
        if re.search(r'[A-Z]:[\\/]Users[\\/]|/home[/]|gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{25,}', text):
            raise ValueError('Private path or credential pattern in ' + name)
    contents['SHA256SUMS'] = ''.join(
        hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
        for name, data in sorted(contents.items())).encode()
    output = ROOT / '.runtime/releases/paper-voice-smoke-001-adapter.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in contents.items():
            z.writestr('paper-voice-smoke-001-adapter/' + name, data)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
    print(json.dumps({'archive': str(output.relative_to(ROOT)), 'files': len(contents),
                      'bytes': output.stat().st_size,
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
