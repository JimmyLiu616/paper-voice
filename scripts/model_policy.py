"""Reviewed model allowlist and pinned artifacts. No automatic model fallback.

This enforces project configuration, not a sandbox for other programs on the PC.
The policy and source code are trusted, version-controlled review inputs.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / 'MODEL_POLICY.json'


class ModelPolicyError(ValueError):
    pass


def policy():
    return json.loads(POLICY_FILE.read_text(encoding='utf-8'))


def approved(model, *, revision=None, serving=True):
    data = policy()
    entry = next((m for m in data['approved_models']
                  if model in (m['id'], m.get('runtime_tag'))), None)
    if entry is None or (serving and not entry.get('serving')):
        raise ModelPolicyError('模型來源規則拒絕：未核准的模型 ' + str(model))
    if revision is not None and revision != entry.get('revision'):
        raise ModelPolicyError('模型版本不符：' + str(model))
    return entry


@lru_cache(maxsize=256)
def _hash(path, size, mtime_ns, ctime_ns):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_files(model, folder=None):
    entry = approved(model)
    folder = Path(folder) if folder is not None else ROOT / entry['directory']
    if not entry.get('files'):
        raise ModelPolicyError('缺少固定模型檔案清單：' + model)
    for name, expected in entry['files'].items():
        path = folder / name
        try:
            before = path.stat()
            if before.st_size != expected['bytes']:
                raise ModelPolicyError('模型檔案大小不符：' + model + '/' + name)
            digest = _hash(str(path.resolve()), before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ModelPolicyError('模型檔案在檢查期間變更：' + model)
            if digest != expected['sha256']:
                raise ModelPolicyError('模型檔案 SHA256 不符：' + model + '/' + name)
        except OSError as exc:
            raise ModelPolicyError('核准模型檔案尚未就緒：' + model + '/' + name) from exc
    return entry


def files_available(model):
    """Cheap readiness probe; SHA256 is verified before actual loading."""
    try:
        entry = approved(model)
        return bool(entry.get('files')) and all(
            (ROOT / entry['directory'] / name).stat().st_size == item['bytes']
            for name, item in entry['files'].items())
    except (OSError, KeyError, ModelPolicyError):
        return False


async def verify_ollama(client, model):
    entry = approved(model)
    response = await client.get('http://127.0.0.1:11434/api/tags')
    response.raise_for_status()
    actual = next((m.get('digest') for m in response.json().get('models', [])
                   if m.get('name') == model), None)
    if not entry.get('ollama_digest') or actual != entry['ollama_digest']:
        raise ModelPolicyError('模型來源或版本不符，已停止執行：' + model)
    return entry


def classify_installed(name):
    data = policy()
    if any(name in (m['id'], m.get('runtime_tag')) for m in data['approved_models']):
        return 'approved'
    if re.search(r'qwen|deepseek|omnitranslate', name, re.I):
        return 'blocked_chinese_origin_or_base'
    return 'unreviewed_blocked'
