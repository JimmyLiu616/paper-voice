"""CPU execution and isolated fake review declarations, never task-training data."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts.train_document_lora import ROOT, read_sources, train_epochs, dev_outputs
from scripts.prepare_training_messages import prepare


def rows():
    return [dict(schema='paper-voice-understanding-v1', source_id='trainer-unit-' + split,
                 family='trainer-unit-family-' + split, split=split, license='MIT',
                 human_reviewed=True, rights_confirmed=True,
                 review={'reviewer':'TEST_AUTOMATION_NOT_A_PERSON',
                         'reviewed_at':'2026-10-01T00:00:00+00:00', 'method':'isolated-unit-test'},
                 document=f'{split}單元測試：費用免費。',
                 fields={'deadline':'', 'required_documents':'', 'amount':'費用免費。', 'conditions':''},
                 questions=[{'question':'收費？', 'answer':'免費。', 'found':True, 'evidence':['費用免費。']}])
            for split in ('train', 'dev', 'test')]


def write_rows(path, values):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in values), encoding='utf-8')


def cli(path, name, *options):
    return subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts/train_document_lora.py'),
                           str(path), '--name', name, *options], capture_output=True, text=True, encoding='utf-8')


def test_real_unreviewed_drafts_rejected_before_output_or_gpu(tmp_path):
    drafts = json.loads((ROOT/'static/training-review-drafts.json').read_text(encoding='utf-8'))['rows']
    path = tmp_path/'drafts.jsonl'; write_rows(path, drafts)
    name = 'unit-rejected-' + tmp_path.name.lower().replace('_', '-')[:28]
    destination = ROOT/'.runtime/document-training'/name
    assert not destination.exists()
    result = cli(path, name)  # No --check-only: the actual training entry must reject.
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report['training_started'] is False and report['files_written'] is False
    assert any('human review' in e for e in report['errors'])
    assert not destination.exists()


def test_check_only_preserves_holdout_and_does_not_write(tmp_path):
    path = tmp_path/'fake-unit-declarations.jsonl'; write_rows(path, rows())
    name = 'unit-check-' + tmp_path.name.lower().replace('_', '-')[:28]
    result = cli(path, name, '--check-only')
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['messages_by_split'] == {'train':2, 'dev':2}
    assert report['files_written'] is False
    assert not (ROOT/'.runtime/document-training'/name).exists()
    output, manifest = read_sources([path])
    assert set(output) == {'train', 'dev'}
    assert rows()[2]['document'] not in json.dumps([output, manifest], ensure_ascii=False)


@pytest.mark.parametrize('options', [('--learning-rate','nan'), ('--epochs','0'),
                                    ('--accumulation','-1'), ('--max-new-tokens','0')])
def test_invalid_settings_rejected(tmp_path, options):
    result = cli(tmp_path/'missing.jsonl', 'unit-invalid', *options)
    assert result.returncode == 2
    assert 'positive' in result.stderr


def toy_model():
    import torch
    class Toy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor(2.0))
            self.seen = []

        def forward(self, input_ids, attention_mask, labels):
            self.seen.append(input_ids.tolist())
            # Constant unit derivative reveals accidental underweighting of tails.
            return SimpleNamespace(loss=self.weight * input_ids.float().mean())
    return Toy()


def test_accumulation_tail_has_full_gradient_and_all_examples_each_epoch():
    model = toy_model()
    batch = {'input_ids':[1], 'attention_mask':[1], 'labels':[1]}
    records = []
    count = train_epochs(model, [batch]*5, epochs=2, accumulation=4,
                         learning_rate=.01, seed=42, on_step=records.append)
    assert count == 4 and len(model.seen) == 10
    assert [r['examples'] for r in records] == [4, 1, 4, 1]
    assert [r['gradient_norm_before_clipping'] for r in records] == pytest.approx([1]*4)
    assert model.weight.item() < 2


def test_nonfinite_loss_stops_before_an_optimizer_step():
    model = toy_model()
    records = []
    batch = {'input_ids':[float('nan')], 'attention_mask':[1], 'labels':[1]}
    with pytest.raises(ValueError, match='Non-finite training loss'):
        train_epochs(model, [batch], epochs=1, accumulation=1,
                     learning_rate=.01, seed=42, on_step=records.append)
    assert model.weight.item() == 2 and records == []


def test_dev_generation_never_receives_assistant_reference_tokens(tmp_path):
    import torch
    model = toy_model()
    def generate(**kwargs):
        assert kwargs['input_ids'].tolist() == [[11, 12]]
        assert kwargs['attention_mask'].tolist() == [[1, 1]]
        assert kwargs['do_sample'] is False
        return torch.tensor([[11, 12, 81, 99]])
    model.generate = generate
    tokenizer = SimpleNamespace(eos_token_id=99, decode=lambda ids, **kw: '模型輸出')
    output, _ = prepare(rows())
    encoded = {'input_ids':[11, 12, 71, 72, 99], 'prefix_tokens':2}
    path = tmp_path/'dev.jsonl'
    dev_outputs(model, tokenizer, output['dev'][:1], [encoded], path, 32)
    record = json.loads(path.read_text(encoding='utf-8'))
    assert record['output'] == '模型輸出' and record['ended_with_eos'] is True
    assert record['source_id'] == 'trainer-unit-dev'
    assert record['reference'] == output['dev'][0]['messages'][1]['content']
    assert record['generated_tokens'] == 2
    with pytest.raises(FileExistsError):
        dev_outputs(model, tokenizer, output['dev'][:1], [encoded], path, 32)
