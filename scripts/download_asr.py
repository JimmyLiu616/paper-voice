"""Download the pinned official Taiwan Tongues ASR CE inference model."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HOME'] = str(ROOT / '.runtime' / 'hf-cache')
os.environ['HF_HUB_OFFLINE'] = '0'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
from huggingface_hub import snapshot_download

REPO = 'adi-gov-tw/Taiwan-Tongues-ASR-CE-v1.0'
REVISION = '46b5eb7ee167ac2fd06cfe02f40e8fac416e5086'
if __name__ == '__main__':
    path = snapshot_download(REPO, revision=REVISION,
        local_dir=ROOT / '.runtime' / 'taiwan-tongues-asr',
        allow_patterns=['*.json', 'model.bin', 'README.md', 'LICENSE'])
    (ROOT / '.runtime' / 'asr-revision.json').write_text(
        json.dumps({'repo': REPO, 'revision': REVISION}, indent=2), encoding='utf-8')
    print(path)
