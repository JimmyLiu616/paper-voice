"""Package source and original fixtures only, excluding environments and weights."""
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
destination=root.parent/'paper-voice-submission.zip'
files=['app.py','corpus.py','AGENTS.md','.cursor/rules/model-origin.mdc','MODEL_POLICY.json','MODEL_POLICY.md','LANGUAGES.md','README.md','DEMO.md','SUBMISSION.md','VALIDATION.md','MODEL_SOURCES.json','LICENSE','CONTRIBUTING_DATA.md','ITERATION_LOG.md','asr-validation.json','extension-validation.json',
       'requirements.txt','requirements-lock.txt','pytest.ini','Start.ps1','Start.cmd','Stop.ps1','Stop.cmd',
       '.gitignore','validation-report.json','release-validation.json']
for folder in ['static','scripts','samples','tests','third_party','evaluation']:
    files += [str(path.relative_to(root)) for path in (root/folder).rglob('*') if path.is_file() and '__pycache__' not in path.parts]
files += [str(path.relative_to(root)) for path in (root/'training').glob('*.md')]
files += ['training/preflight.json','training/preflight-training.json',
          'training/requirements-cuda.txt','training/requirements-cuda-lock.txt',
          'training/native-model-manifest.json','training/native-model-download.json',
          'training/smoke-fixture.json','training/lora-smoke-report.json',
          'training/review-drafts-validation.json','training/review-ui-validation.json',
          'training/messages-validation.json','training/tokenization-validation.json',
          'training/contrast-drafts-validation.json','training/contrast-ui-validation.json']
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
    for file in files:
        if (root/file).is_file():archive.write(root/file,'paper-voice/'+file.replace('\\','/'))
print(destination)
print(f'{destination.stat().st_size:,} bytes')
