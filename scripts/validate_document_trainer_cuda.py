"""Run the real document trainer on ONLY the pinned, unreviewed smoke fixture.

Same fixture before/after is deliberately not an independent dev comparison.
No arbitrary input files, false review declarations, task data, or deployment.
"""
import argparse
import json
from pathlib import Path
import re
from types import SimpleNamespace

try:
    from .prepare_training_messages import ROOT, VERSION, QA_PROMPT, encode, digest
    from .train_document_lora import run
except ImportError:
    from prepare_training_messages import ROOT, VERSION, QA_PROMPT, encode, digest
    from train_document_lora import run

FIXTURE_SHA256 = '43f848e29cc2d6cedb29e3ce79cf7e9ab88d11515260fbe9d6c509ef1f7e6164'


def fixture_inputs(fixture):
    canonical = json.dumps(fixture, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    if digest(canonical.encode('utf-8')) != FIXTURE_SHA256:
        raise ValueError('Only the exact original unreviewed smoke fixture is allowed')
    assert fixture['human_reviewed'] is False and fixture['purpose'] == 'synthetic-feasibility-only'
    record = {'schema': VERSION, 'source_id': fixture['source_id'], 'family': fixture['family'],
              'task': 'qa-1', 'license': fixture['license'], 'human_reviewed': False,
              'purpose': fixture['purpose'], 'document_sha256': digest(fixture['document'].encode('utf-8')),
              'messages': [{'role': 'user', 'content': QA_PROMPT + encode({
                  'document': fixture['document'], 'question': fixture['question']})},
                  {'role': 'assistant', 'content': encode({'answer': fixture['answer'],
                      'found': True, 'evidence': [fixture['evidence']]})}]}
    output = {split: [dict(record, split=split)] for split in ('train', 'dev')}
    manifest = {'schema': VERSION, 'purpose': fixture['purpose'], 'human_reviewed': False,
                'fixture_canonical_sha256': FIXTURE_SHA256,
                'runner_sha256': digest(Path(__file__).read_bytes()),
                'same_fixture_train_and_dev': True, 'test_labels_exported': False,
                'quality_improvement_evaluated': False,
                'note': 'One pinned synthetic fixture for CUDA integration only, not reviewed task data or independent evaluation.'}
    return output, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'cuda-smoke-[a-z0-9][a-z0-9-]{0,48}', args.name):
        parser.error('Name must start cuda-smoke- and contain lowercase letters, digits or hyphens')
    fixture = json.loads((ROOT / 'training/smoke-fixture.json').read_text(encoding='utf-8'))
    output, manifest = fixture_inputs(fixture)
    settings = SimpleNamespace(name=args.name, epochs=1, accumulation=4, learning_rate=1e-4,
                               seed=42, max_tokens=1024, max_new_tokens=192)
    run(output, manifest, settings)


if __name__ == '__main__':
    main()
