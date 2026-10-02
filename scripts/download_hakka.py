import hashlib
import json
import os
from pathlib import Path
try:
    from scripts.model_policy import approved
except ModuleNotFoundError:
    from model_policy import approved
os.environ['HF_HUB_OFFLINE'] = '0'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
REPO = 'formospeech/yourtts-htia-240704'
REV = 'e61e1026d1fe5edb29f35ad025c090526a7e4fe7'
approved(REPO, revision=REV)
FILES = ['README.md', 'config.json', 'language_ids.json', 'model.pth', 'speaker_embs.pth', 'speakers.pth']
info = HfApi(token=False).model_info(REPO, revision=REV, files_metadata=True)
selected = [f for f in info.siblings if f.rfilename in FILES]
assert len(selected) == len(FILES)
assert sum(f.size or 0 for f in selected) < 2_000_000_000
target = ROOT / '.runtime/voxhakka'
snapshot_download(REPO, revision=REV, token=False, local_dir=target, allow_patterns=FILES)
rows = []
for item in selected:
    h = hashlib.sha256()
    path = target / item.rfilename
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    assert path.stat().st_size == item.size
    expected = item.lfs.sha256 if item.lfs else None
    if expected:
        assert expected == h.hexdigest()
    rows.append({'file':item.rfilename, 'bytes':path.stat().st_size, 'sha256':h.hexdigest(), 'lfs_sha256_verified':bool(expected)})
report = {'repo':REPO,'revision':REV,'files':rows,'license':'CC-BY-NC-4.0','purpose':'Optional local Hakka TTS; fixed released speaker XF'}
(target/'download-manifest.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
