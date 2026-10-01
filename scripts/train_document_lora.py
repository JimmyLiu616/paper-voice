"""Offline reviewed-text QLoRA experiment, with paired dev outputs; never deploy.

Train/dev/test declarations are checked before importing GPU libraries. Test
labels only participate in source validation, never optimization or generation.
Use --check-only to inspect eligibility without creating files or loading weights.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time

try:
    from .prepare_training_messages import ROOT, prepare, write_bundle, digest
    from .training_tokens import tokenize_messages
except ImportError:
    from prepare_training_messages import ROOT, prepare, write_bundle, digest
    from training_tokens import tokenize_messages


def read_sources(paths):
    rows, inputs = [], []
    for path in paths:
        raw = path.read_bytes()
        rows.extend(json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip())
        inputs.append({'sha256': digest(raw), 'bytes': len(raw)})
    output, manifest = prepare(rows)
    manifest['inputs'] = inputs
    return output, manifest


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def train_epochs(model, examples, *, epochs, accumulation, learning_rate, seed, on_step):
    """Batch size one, equal example weighting; normalize a short final group."""
    import torch
    if not examples or epochs < 1 or accumulation < 1 or not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError('Positive training settings and nonempty examples required')
    parameters = [p for p in model.parameters() if p.requires_grad]
    if not parameters:
        raise ValueError('No trainable parameters')
    optimizer = torch.optim.AdamW(parameters, lr=learning_rate, weight_decay=0.0)
    device = parameters[0].device
    rng = random.Random(seed)
    step = 0
    model.train()
    for epoch in range(epochs):
        order = list(range(len(examples)))
        rng.shuffle(order)
        for start in range(0, len(order), accumulation):
            indices = order[start:start + accumulation]
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for index in indices:
                batch = {k: torch.tensor([examples[index][k]], device=device)
                         for k in ('input_ids', 'attention_mask', 'labels')}
                loss = model(**batch).loss
                if not torch.isfinite(loss).item():
                    raise ValueError('Non-finite training loss')
                losses.append(float(loss.detach()))
                (loss / len(indices)).backward()
            gradients = [p.grad for p in parameters if p.grad is not None]
            if not gradients or not all(torch.isfinite(g).all().item() for g in gradients):
                raise ValueError('Missing or non-finite training gradients')
            norm = float(torch.nn.utils.clip_grad_norm_(parameters, 1.0))
            if not math.isfinite(norm):
                raise ValueError('Non-finite gradient norm')
            optimizer.step()
            step += 1
            on_step({'step': step, 'epoch': epoch + 1, 'examples': len(indices),
                     'mean_example_loss': sum(losses) / len(losses),
                     'gradient_norm_before_clipping': norm})
    optimizer.zero_grad(set_to_none=True)
    return step


def dev_outputs(model, tokenizer, records, tokens, destination, max_new_tokens):
    """Greedy generation never includes reference assistant tokens in input."""
    import torch
    model.eval()
    # No generated answers are accepted as correct here; save them for review.
    with destination.open('x', encoding='utf-8') as stream, torch.inference_mode():
        for row, encoded in zip(records, tokens, strict=True):
            prompt_ids = encoded['input_ids'][:encoded['prefix_tokens']]
            ids = torch.tensor([prompt_ids], device=next(model.parameters()).device)
            began = time.perf_counter()
            result = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                                    do_sample=False, max_new_tokens=max_new_tokens,
                                    eos_token_id=tokenizer.eos_token_id,
                                    pad_token_id=tokenizer.eos_token_id, use_cache=True)
            generated = result[0, len(prompt_ids):].tolist()
            record = {k: row[k] for k in ('source_id', 'family', 'task', 'document_sha256')}
            record.update(prompt_sha256=digest(row['messages'][0]['content'].encode('utf-8')),
                          reference=row['messages'][1]['content'],
                          output=tokenizer.decode(generated, skip_special_tokens=True),
                          generated_tokens=len(generated),
                          ended_with_eos=bool(generated and generated[-1] == tokenizer.eos_token_id),
                          elapsed_seconds=round(time.perf_counter() - began, 3))
            stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            stream.flush()


def run(output, manifest, args):
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HOME'] = str(ROOT / '.runtime/hf-train-cache')
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    destination = ROOT / '.runtime/document-training' / args.name
    destination.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'purpose': 'reviewed-document-text-experiment',
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'config': {k: getattr(args, k) for k in
                         ('name', 'epochs', 'accumulation', 'learning_rate', 'seed', 'max_tokens', 'max_new_tokens')},
              'optimizer_steps': 0, 'deployed': False, 'task_quality_verified': False,
              'test_generation_performed': False, 'steps': [],
              'code_sha256': {name: file_hash(ROOT / 'scripts' / name) for name in
                             ('train_document_lora.py', 'prepare_training_messages.py',
                              'validate_training_data.py', 'training_tokens.py')}}

    def save(stage):
        report['stage'] = stage
        (destination / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'stage': stage, 'optimizer_steps': report['optimizer_steps']}), flush=True)

    def log_step(record):
        report['steps'].append(record)
        report['optimizer_steps'] = record['step']
        save('training')

    try:
        write_bundle(destination / 'inputs', output, manifest)
        for name in report['code_sha256']:
            (destination / name).write_bytes((ROOT / 'scripts' / name).read_bytes())
        download_path = ROOT / 'training/native-model-download.json'
        download = json.loads(download_path.read_text(encoding='utf-8'))
        provenance = json.loads((ROOT / 'training/native-model-manifest.json').read_text(encoding='utf-8'))
        if (download['model'] != 'mistralai/Ministral-3-3B-Instruct-2512-BF16'
                or download['revision'] != 'b6d637bef2393152b3da2b2fde72eecdee30557e'
                or download['model'] != provenance['model'] or download['revision'] != provenance['revision']
                or provenance['gated'] or provenance['license'] != 'apache-2.0'):
            raise ValueError('Unexpected checkpoint provenance')
        model_path = ROOT / download['directory']
        report.update(model=download['model'], revision=download['revision'],
                      download_manifest_sha256=file_hash(download_path))
        save('verifying_checkpoint')
        for record in download['files']:
            path = model_path / record['file']
            if path.stat().st_size != record['size'] or file_hash(path) != record['sha256']:
                raise ValueError('Checkpoint changed: ' + record['file'])

        import importlib.metadata as metadata
        import torch
        from transformers import BitsAndBytesConfig, Mistral3ForConditionalGeneration, MistralCommonBackend, set_seed
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from safetensors.torch import load_file
        if not torch.cuda.is_available():
            raise RuntimeError('Run this experiment in the CUDA training environment')
        report['packages'] = {name: metadata.version(name) for name in
                              ('torch', 'transformers', 'peft', 'bitsandbytes', 'accelerate', 'mistral-common')}
        inference = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='test')
        training = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='finetuning')
        tokens = {split: [tokenize_messages(row['messages'], inference, training, args.max_tokens)
                          for row in rows] for split, rows in output.items()}
        report['token_lengths'] = {split: [len(t['input_ids']) for t in values] for split, values in tokens.items()}
        set_seed(args.seed)
        torch.cuda.reset_peak_memory_stats()
        report['gpu'] = torch.cuda.get_device_name(0)
        report['gpu_free_at_start_bytes'] = torch.cuda.mem_get_info()[0]
        report['quantization'] = {'bits': 4, 'type': 'nf4', 'double_quant': True, 'compute_dtype': 'bfloat16'}
        report['lora'] = {'r': 4, 'alpha': 8, 'dropout': 0.0}
        save('loading_model')
        model = Mistral3ForConditionalGeneration.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False, device_map={'': 0},
            dtype=torch.bfloat16, attn_implementation='sdpa',
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
        model.config.use_cache = False
        targets = [name for name, _ in model.named_modules()
                   if 'language_model' in name and name.endswith(('.q_proj', '.v_proj'))]
        if len(targets) != 52:
            raise ValueError('Expected 52 language attention projections')
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                               gradient_checkpointing_kwargs={'use_reentrant': False})
        model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0,
                              target_modules=targets, bias='none', task_type='CAUSAL_LM'))
        parameters = {n: p for n, p in model.named_parameters() if p.requires_grad}
        if not parameters or any('lora_' not in n or 'vision' in n for n in parameters):
            raise ValueError('Unexpected trainable parameters')
        before = {n: p.detach().cpu().clone() for n, p in parameters.items()}
        report['trainable_parameters'] = sum(p.numel() for p in parameters.values())
        save('baseline_dev_generation')
        with model.disable_adapter():
            dev_outputs(model, inference, output['dev'], tokens['dev'],
                        destination / 'baseline-dev.jsonl', args.max_new_tokens)
        train_epochs(model, tokens['train'], epochs=args.epochs, accumulation=args.accumulation,
                     learning_rate=args.learning_rate, seed=args.seed, on_step=log_step)
        changes = [float((p.detach().cpu() - before[n]).abs().max()) for n, p in parameters.items()]
        if not all(math.isfinite(v) for v in changes) or max(changes) <= 0:
            raise ValueError('Adapter did not receive a finite nonzero update')
        report['changed_adapter_tensors'] = sum(v > 0 for v in changes)
        del before
        adapter = destination / 'adapter'
        model.peft_config['default'].base_model_name_or_path = download['model']
        model.peft_config['default'].revision = download['revision']
        model.save_pretrained(adapter, safe_serialization=True)
        tensors = load_file(str(adapter / 'adapter_model.safetensors'))
        if not tensors or any(not torch.isfinite(t).all().item() for t in tensors.values()):
            raise ValueError('Invalid saved adapter')
        del tensors
        model.load_adapter(str(adapter), adapter_name='roundtrip', is_trainable=False)
        model.set_adapter('roundtrip')
        save('reloaded_adapter_dev_generation')
        dev_outputs(model, inference, output['dev'], tokens['dev'],
                    destination / 'adapter-dev.jsonl', args.max_new_tokens)
        report['artifacts_sha256'] = {name: file_hash(destination / name) for name in
                                     ('baseline-dev.jsonl', 'adapter-dev.jsonl', 'adapter/adapter_model.safetensors',
                                      'adapter/adapter_config.json', 'inputs/manifest.json')}
        report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        report['status'] = 'completed-awaiting-quality-review'
        save('complete')
    except Exception as error:
        report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        save('failed')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--name', required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--epochs', type=int, default=1)
    parser.add_argument('--accumulation', type=int, default=4)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-tokens', type=int, default=1024)
    parser.add_argument('--max-new-tokens', type=int, default=512)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Use a unique lowercase run name')
    if (min(args.epochs, args.accumulation, args.max_tokens, args.max_new_tokens) < 1
            or not math.isfinite(args.learning_rate) or args.learning_rate <= 0 or args.seed < 0):
        parser.error('Training limits and rate must be positive; seed must be nonnegative')
    try:
        output, manifest = read_sources(args.files)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({'eligible': False, 'errors': str(error).splitlines(),
                          'training_started': False, 'files_written': False}, ensure_ascii=False, indent=2))
        return 1
    if args.check_only:
        print(json.dumps({'eligible': True, 'documents_by_split': manifest['documents_by_split'],
                          'messages_by_split': manifest['messages_by_split'],
                          'training_started': False, 'files_written': False,
                          'note': 'Data checks only; no GPU, token length or semantic quality verification.'}, ensure_ascii=False))
        return 0
    run(output, manifest, args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
