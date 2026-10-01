"""Fresh-process adapter tensor and dev-generation reproducibility verification."""
import argparse
import json
import os
from pathlib import Path
import re
import time

try:
    from .train_document_lora import ROOT, file_hash, dev_outputs
    from .training_tokens import tokenize_messages
except ImportError:
    from train_document_lora import ROOT, file_hash, dev_outputs
    from training_tokens import tokenize_messages


def same_outputs(expected, actual):
    return len(expected) == len(actual) and all(
        {k: v for k, v in left.items() if k != 'elapsed_seconds'} ==
        {k: v for k, v in right.items() if k != 'elapsed_seconds'}
        for left, right in zip(expected, actual))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Invalid run name')
    directory = ROOT / '.runtime/document-training' / args.name
    result_path = directory / 'fresh-process-verification.json'
    output_path = directory / 'fresh-adapter-dev.jsonl'
    if result_path.exists() or output_path.exists():
        raise FileExistsError('Existing verification must not be overwritten')
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
    if report['status'] not in ('completed-synthetic-flow-only', 'completed-awaiting-quality-review'):
        raise ValueError('Training run did not complete')
    artifacts = ('baseline-dev.jsonl', 'adapter-dev.jsonl', 'adapter/adapter_model.safetensors',
                 'adapter/adapter_config.json', 'inputs/manifest.json')
    for name in artifacts:
        if file_hash(directory / name) != report['artifacts_sha256'][name]:
            raise ValueError('Run artifact changed: ' + name)
    manifest = json.loads((directory/'inputs/manifest.json').read_text(encoding='utf-8'))
    for split in ('train', 'dev'):
        if file_hash(directory/'inputs'/f'{split}.jsonl') != manifest['outputs'][f'{split}.jsonl']['sha256']:
            raise ValueError('Prepared input changed')
    for name in ('train_document_lora.py', 'training_tokens.py'):
        if file_hash(ROOT/'scripts'/name) != report['code_sha256'][name]:
            raise ValueError('Runtime helper changed; restore the run snapshot first')
    download_path = ROOT/'training/native-model-download.json'
    if file_hash(download_path) != report['download_manifest_sha256']:
        raise ValueError('Download manifest changed')
    download = json.loads(download_path.read_text(encoding='utf-8'))
    if download['model'] != report['model'] or download['revision'] != report['revision']:
        raise ValueError('Base model provenance changed')
    model_path = ROOT/download['directory']
    for record in download['files']:
        path = model_path/record['file']
        if path.stat().st_size != record['size'] or file_hash(path) != record['sha256']:
            raise ValueError('Base checkpoint changed: ' + record['file'])
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HOME'] = str(ROOT/'.runtime/hf-train-cache')
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from transformers import BitsAndBytesConfig, Mistral3ForConditionalGeneration, MistralCommonBackend, set_seed
    from peft import PeftModel, prepare_model_for_kbit_training, get_peft_model_state_dict
    from safetensors.torch import load_file
    started = time.perf_counter()
    set_seed(report['config']['seed'])
    model = Mistral3ForConditionalGeneration.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=False, device_map={'': 0},
        dtype=torch.bfloat16, attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    model.config.use_cache = False
    model = PeftModel.from_pretrained(model, directory/'adapter', is_trainable=False, local_files_only=True)
    saved = load_file(str(directory/'adapter/adapter_model.safetensors'))
    loaded = get_peft_model_state_dict(model)
    tensors_equal = bool(saved) and saved.keys() == loaded.keys() and all(
        torch.equal(saved[key], loaded[key].detach().cpu()) for key in saved)
    if not tensors_equal:
        raise ValueError('Reloaded adapter tensors do not exactly match the serialized adapter')
    tokenizer = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='test')
    training = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='finetuning')
    records = [json.loads(line) for line in (directory/'inputs/dev.jsonl').read_text(encoding='utf-8').splitlines()]
    tokens = [tokenize_messages(row['messages'], tokenizer, training, report['config']['max_tokens']) for row in records]
    dev_outputs(model, tokenizer, records, tokens, output_path, report['config']['max_new_tokens'])
    expected = [json.loads(line) for line in (directory/'adapter-dev.jsonl').read_text(encoding='utf-8').splitlines()]
    actual = [json.loads(line) for line in output_path.read_text(encoding='utf-8').splitlines()]
    result = {'run': args.name, 'purpose': report['purpose'], 'fresh_process': True,
              'adapter_tensors_exactly_equal': tensors_equal, 'tensor_count': len(saved),
              'generation_exactly_equal_excluding_timing': same_outputs(expected, actual),
              'records': len(actual), 'elapsed_after_checkpoint_check_seconds': round(time.perf_counter()-started, 3),
              'script_sha256': file_hash(Path(__file__)), 'outputs_sha256': file_hash(output_path),
              'adapter_sha256': report['artifacts_sha256']['adapter/adapter_model.safetensors'],
              'task_quality_verified': False, 'deployed': False,
              'note': 'Serialization and generation reproducibility only. Synthetic runs reuse their training fixture.'}
    result['passed'] = tensors_equal and result['generation_exactly_equal_excluding_timing']
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if not result['passed']:
        raise RuntimeError('Fresh-process generation differs; retain the evidence for investigation')


if __name__ == '__main__':
    main()
