"""Read-only offline inspection of shipped AI drafts; never writes token datasets."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import time

from prepare_training_messages import ROOT, digest, document_tasks, reserved_sources
from validate_training_data import validate
from training_tokens import tokenize_messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-tokens', type=int, default=1024)
    args = parser.parse_args()
    if args.max_tokens < 1:
        parser.error('--max-tokens must be positive')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HOME'] = str(ROOT / '.runtime/hf-train-cache')
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    started = time.perf_counter()
    source = ROOT / 'static/training-review-drafts.json'
    rows = json.loads(source.read_text(encoding='utf-8'))['rows']
    # Intentionally do not call prepare() or alter review flags for this inspection.
    if any(r.get('human_reviewed') is not False or r.get('rights_confirmed') is not False
           or r.get('split') not in ('train', 'dev') for r in rows):
        raise ValueError('Inspection is limited to the unreviewed, non-test shipped drafts')
    errors = validate(rows, *reserved_sources())
    if any(not e.endswith('rights and human review must be explicitly confirmed') for e in errors):
        raise ValueError('Draft structure or source validation failed')
    manifest_path = ROOT / 'training/native-model-download.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    model_path = ROOT / manifest['directory']
    verified = []
    for record in manifest['files']:
        if record['file'].endswith('.safetensors'):
            continue
        raw = (model_path / record['file']).read_bytes()
        if len(raw) != record['size'] or digest(raw) != record['sha256']:
            raise ValueError('Tokenizer/config checkpoint changed: ' + record['file'])
        verified.append(record['file'])
    from transformers import MistralCommonBackend
    inference = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='test')
    training = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='finetuning')
    report = {'purpose': 'read-only-draft-token-inspection', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'model': manifest['model'], 'revision': manifest['revision'], 'verified_metadata_files': verified,
              'packages': {p: importlib.metadata.version(p) for p in ['transformers', 'mistral-common']},
              'max_tokens': args.max_tokens, 'source_sha256': digest(source.read_bytes()),
              'code_sha256': {p: digest((ROOT / 'scripts' / p).read_bytes()) for p in
                             ['inspect_training_tokens.py', 'training_tokens.py', 'prepare_training_messages.py']},
              'human_reviewed': 0, 'eligible_for_training': False, 'weights_loaded': False,
              'optimizer_steps': 0, 'token_dataset_written': False, 'sequences': [], 'errors': []}
    for row in rows:
        for task, messages in document_tasks(row):
            identity = {'source_id': row['source_id'], 'split': row['split'], 'task': task}
            try:
                batch = tokenize_messages(messages, inference, training, args.max_tokens)
                prefix = batch['prefix_tokens']
                assert all(label == -100 for label in batch['labels'][:prefix])
                assert batch['labels'][prefix:] == batch['input_ids'][prefix:]
                report['sequences'].append(identity | {'tokens': len(batch['input_ids']),
                     'prefix_tokens': prefix, 'supervised_tokens': batch['supervised_tokens'], 'eos_supervised': True})
            except ValueError as error:
                report['errors'].append(identity | {'error': str(error)})
    lengths = [item['tokens'] for item in report['sequences']]
    report.update(status='passed' if lengths and not report['errors'] else 'failed',
                  sequence_count=len(lengths), min_tokens=min(lengths, default=0), max_observed_tokens=max(lengths, default=0),
                  elapsed_seconds=round(time.perf_counter()-started, 3),
                  note='Length/mask checks only; labels are unreviewed. No GPU memory, task quality or training readiness claim.')
    (ROOT / 'training/tokenization-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status','sequence_count','min_tokens','max_observed_tokens','max_tokens','elapsed_seconds','errors']},ensure_ascii=False))
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
