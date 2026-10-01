"""Reload the smoke adapter in a fresh process and reproduce both fixture losses."""
import argparse
import json
from pathlib import Path
import re
import time

from train_lora_smoke import ROOT, sha  # also sets offline mode before HF imports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Invalid run name')
    run = ROOT / '.runtime/training-runs' / args.name
    destination = run / 'fresh-process-verification.json'
    if destination.exists():
        raise FileExistsError('Existing verification must not be overwritten')
    started = time.perf_counter()
    report = json.loads((run / 'report.json').read_text(encoding='utf-8'))
    fixture = json.loads((run / 'smoke-fixture.json').read_text(encoding='utf-8'))
    download = json.loads((ROOT / 'training/native-model-download.json').read_text(encoding='utf-8'))
    if (report['status'] != 'passed' or report['revision'] != download['revision']
            or report['model'] != download['model']
            or report['fixture_sha256'] != sha(run / 'smoke-fixture.json')
            or report['adapter_sha256'] != sha(run / 'adapter/adapter_model.safetensors')):
        raise ValueError('Run provenance or adapter changed')
    import torch
    from transformers import BitsAndBytesConfig, Mistral3ForConditionalGeneration, MistralCommonBackend, set_seed
    from peft import PeftModel, prepare_model_for_kbit_training
    set_seed(report['seed'])
    model_path = ROOT / download['directory']
    model = Mistral3ForConditionalGeneration.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=False, device_map={'': 0},
        dtype=torch.bfloat16, attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
    # Reproduce the same non-quantized parameter dtypes used during training.
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    model.config.use_cache = False
    prefix_tokenizer = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='test')
    tokenizer = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='finetuning')
    user = '依通知回答問題，保留例外條件。\n通知：' + fixture['document'] + '\n問題：' + fixture['question']
    messages = [{'role': 'user', 'content': user}]
    prefix = prefix_tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False)
    full = tokenizer.apply_chat_template(messages + [{'role': 'assistant', 'content': fixture['answer']}],
                                         tokenize=True, return_dict=False)
    if full[:len(prefix)] != prefix or len(full) != report['sequence_length']:
        raise ValueError('Tokenization changed')
    ids = torch.tensor([full], device='cuda')
    labels = ids.clone()
    labels[:, :len(prefix)] = -100
    batch = {'input_ids': ids, 'attention_mask': torch.ones_like(ids), 'labels': labels}
    model.eval()
    with torch.no_grad():
        base_loss = model(**batch).loss.item()
    model = PeftModel.from_pretrained(model, run / 'adapter', is_trainable=False, local_files_only=True)
    model.eval()
    with torch.no_grad():
        adapter_loss = model(**batch).loss.item()
    passed = (torch.isfinite(torch.tensor([base_loss, adapter_loss])).all().item()
              and abs(base_loss - report['loss_before_step']) <= 1e-4
              and abs(adapter_loss - report['loss_after_step_same_fixture']) <= 1e-4)
    result = {'run': args.name, 'passed': passed, 'fresh_process': True,
              'base_loss_same_fixture': base_loss, 'adapter_loss_same_fixture': adapter_loss,
              'model': report['model'], 'revision': report['revision'],
              'adapter_sha256': report['adapter_sha256'],
              'script_sha256': sha(Path(__file__)), 'elapsed_seconds': time.perf_counter()-started,
              'note': 'Serialization and reproducibility check on the training fixture; not a quality evaluation.'}
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    if not passed:
        raise RuntimeError('Fresh-process loss reproduction failed')


if __name__ == '__main__':
    main()
