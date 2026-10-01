"""Verify the documented release cannot silently download a new MMS revision."""
import importlib.util
import json
import sys
from types import SimpleNamespace

from scripts import download_taigi


def test_import_does_not_download_or_lookup_latest(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('Import must not contact Hugging Face')
    monkeypatch.setitem(sys.modules, 'huggingface_hub', SimpleNamespace(snapshot_download=unexpected, HfApi=unexpected))
    spec=importlib.util.spec_from_file_location('isolated_download_taigi',download_taigi.__file__)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))


def test_download_uses_recorded_revision_without_credentials(monkeypatch,tmp_path):
    model=next(m for m in json.loads((download_taigi.ROOT/'MODEL_SOURCES.json').read_text(encoding='utf-8'))['models']
               if m['model']==download_taigi.REPO)
    calls=[]
    def fake_download(repo, **kwargs):
        calls.append((repo,kwargs))
        kwargs['local_dir'].mkdir(parents=True)
        return str(kwargs['local_dir'])
    monkeypatch.setitem(sys.modules,'huggingface_hub',SimpleNamespace(snapshot_download=fake_download))
    monkeypatch.setattr(download_taigi,'ROOT',tmp_path)
    # Restore environment automatically after invoking the script's main function.
    for key in ['HF_HOME','HF_HUB_OFFLINE','HF_HUB_DISABLE_SYMLINKS_WARNING']:
        monkeypatch.setenv(key,'test-before-call')
    download_taigi.main()
    assert len(calls)==1
    repo,args=calls[0]
    assert repo==model['model'] and args['revision']==model['revision']
    assert args['token'] is False and '*.safetensors' in args['allow_patterns']
    recorded=json.loads((tmp_path/'.runtime/mms-revision.json').read_text(encoding='utf-8'))
    assert recorded=={'repo':model['model'],'revision':model['revision']}
