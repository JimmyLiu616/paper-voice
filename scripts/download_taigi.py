"""Download only the pinned Meta MMS Min Nan checkpoint into this project."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'facebook/mms-tts-nan'
REVISION = 'f28526a6caaf9dc55e030da83008c933f6a1978b'


def main():
    os.environ['HF_HOME'] = str(ROOT / '.runtime' / 'hf-cache')
    os.environ['HF_HUB_OFFLINE'] = '0'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    from huggingface_hub import snapshot_download

    path = snapshot_download(REPO, revision=REVISION, token=False,
                             local_dir=ROOT / '.runtime' / 'mms-tts-nan',
                             allow_patterns=['*.json', '*.safetensors', 'README.md', 'LICENSE*'])
    (ROOT / '.runtime' / 'mms-revision.json').write_text(
        json.dumps({'repo': REPO, 'revision': REVISION}, indent=2), encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
