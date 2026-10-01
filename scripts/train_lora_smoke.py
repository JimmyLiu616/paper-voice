"""One synthetic QLoRA optimizer step; not task training or a quality benchmark.

Run only in .venv-train. No serving imports, network, private data, or evaluation
examples. A successful report requires finite gradients, a changed adapter and
reloading the saved adapter with matching loss. Never deploys the result.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HOME'] = str(ROOT / '.runtime/hf-train-cache')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', args.name):
        parser.error('Use a unique lowercase run name')
    output = ROOT / '.runtime/training-runs' / args.name
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {'name': args.name, 'purpose': 'synthetic-feasibility-only',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running',
              'quality_improvement_evaluated': False, 'deployed': False,
              'python': sys.version, 'seed': 42, 'optimizer_steps': 0}

    def save(stage):
        report['stage'] = stage
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'stage': stage, 'elapsed_seconds': report['elapsed_seconds']}, ensure_ascii=False), flush=True)

    shutil.copy2(__file__, output / 'train_lora_smoke.py')
    fixture_path = ROOT / 'training/smoke-fixture.json'
    shutil.copy2(fixture_path, output / fixture_path.name)
    report['script_sha256'] = sha(Path(__file__))
    report['fixture_sha256'] = sha(fixture_path)
    try:
        fixture = json.loads(fixture_path.read_text(encoding='utf-8'))
        if fixture['purpose'] != report['purpose'] or fixture['human_reviewed'] is not False:
            raise ValueError('Only the explicitly unreviewed synthetic smoke fixture is allowed')
        from validate_training_data import normalize, reserved_evaluation_sources
        reserved_ids, reserved_texts = reserved_evaluation_sources()
        if (fixture['source_id'] in reserved_ids or fixture['family'] in reserved_ids
                or normalize(fixture['document']) in {normalize(t) for t in reserved_texts}):
            raise ValueError('Smoke input overlaps a reserved evaluation source')
        if fixture['evidence'] not in fixture['document']:
            raise ValueError('Smoke evidence is not verbatim')
        download = json.loads((ROOT / 'training/native-model-download.json').read_text(encoding='utf-8'))
        manifest = json.loads((ROOT / 'training/native-model-manifest.json').read_text(encoding='utf-8'))
        if (download['revision'] != manifest['revision'] or download['model'] != manifest['model']
                or manifest['gated'] or manifest['license'] != 'apache-2.0'):
            raise ValueError('Unexpected checkpoint provenance')
        model_path = ROOT / download['directory']
        report.update(model=download['model'], revision=download['revision'],
                      download_manifest_sha256=sha(ROOT / 'training/native-model-download.json'))
        save('verifying_checkpoint')
        # Check the actual bytes, not just the existence of a download marker.
        for record in download['files']:
            path = model_path / record['file']
            if path.stat().st_size != record['size'] or sha(path) != record['sha256']:
                raise ValueError('Checkpoint changed: ' + record['file'])

        import torch
        import bitsandbytes as bnb
        from transformers import BitsAndBytesConfig, Mistral3ForConditionalGeneration, MistralCommonBackend, set_seed
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from safetensors.torch import load_file
        report['packages'] = {name: metadata.version(name) for name in
                              ['torch', 'transformers', 'peft', 'bitsandbytes', 'accelerate', 'mistral-common']}
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA is required for this GPU feasibility experiment')
        set_seed(42)
        torch.cuda.reset_peak_memory_stats()
        report['gpu'] = torch.cuda.get_device_name(0)
        report['gpu_capability'] = list(torch.cuda.get_device_capability(0))
        report['gpu_free_at_start_bytes'] = torch.cuda.mem_get_info()[0]
        report['quantization'] = {'bits': 4, 'type': 'nf4', 'double_quant': True, 'compute_dtype': 'bfloat16'}
        save('checking_nf4_backward')
        probe = bnb.nn.Linear4bit(128, 128, bias=False, compute_dtype=torch.bfloat16,
                                 compress_statistics=True, quant_type='nf4').to('cuda')
        probe_input = torch.randn(2, 128, device='cuda', dtype=torch.bfloat16, requires_grad=True)
        probe_loss = probe(probe_input).float().square().mean()
        probe_loss.backward()
        probe_ok = (torch.isfinite(probe_loss).item() and probe_input.grad is not None
                    and torch.isfinite(probe_input.grad).all().item()
                    and probe_input.grad.abs().max().item() > 0)
        if not probe_ok:
            raise RuntimeError('4-bit GPU backward probe failed')
        report['nf4_backward_probe_passed'] = True
        del probe, probe_input, probe_loss
        torch.cuda.empty_cache()
        set_seed(42)
        tokenizer = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='test')
        training_tokenizer = MistralCommonBackend.from_pretrained(model_path, local_files_only=True, mode='finetuning')
        user = '依通知回答問題，保留例外條件。\n通知：' + fixture['document'] + '\n問題：' + fixture['question']
        messages = [{'role': 'user', 'content': user}]
        prefix = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False)
        full = training_tokenizer.apply_chat_template(
            messages + [{'role': 'assistant', 'content': fixture['answer']}], tokenize=True, return_dict=False)
        if full[:len(prefix)] != prefix or len(full) <= len(prefix) or len(full) > 256:
            raise ValueError('Unexpected assistant mask boundary or sequence length; no silent truncation')
        if full[-1] != training_tokenizer.eos_token_id:
            raise ValueError('Training target must include the end-of-sequence token')
        report.update(sequence_length=len(full), supervised_tokens=len(full)-len(prefix), batch_size=1)
        save('loading_4bit_model')
        model = Mistral3ForConditionalGeneration.from_pretrained(
            model_path, local_files_only=True, trust_remote_code=False, device_map={'': 0},
            dtype=torch.bfloat16, attn_implementation='sdpa',
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16))
        model.config.use_cache = False
        # Match only the language attention projections; never vision modules.
        targets = [name for name, _ in model.named_modules()
                   if 'language_model' in name and name.endswith(('.q_proj', '.v_proj'))]
        if len(targets) != 52:
            raise ValueError(f'Expected 26 language layers x 2 projections, got {len(targets)}')
        report['target_modules'] = targets
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={'use_reentrant': False})
        model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0,
                              target_modules=targets, bias='none', task_type='CAUSAL_LM'))
        trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
        if not trainable or any('lora_' not in n or 'vision' in n for n in trainable):
            raise ValueError('Unexpected trainable parameters')
        report['trainable_parameters'] = sum(p.numel() for p in trainable.values())
        report['lora'] = {'r': 4, 'alpha': 8, 'dropout': 0.0}
        ids = torch.tensor([full], device='cuda')
        labels = ids.clone()
        labels[:, :len(prefix)] = -100
        batch = {'input_ids': ids, 'attention_mask': torch.ones_like(ids), 'labels': labels}
        before = {n: p.detach().cpu().clone() for n, p in trainable.items()}
        optimizer = torch.optim.AdamW(trainable.values(), lr=1e-4, weight_decay=0.0)
        report['optimizer'] = {'type': 'AdamW', 'lr': 1e-4, 'weight_decay': 0.0}
        save('forward_backward')
        model.train()
        loss = model(**batch).loss
        if not torch.isfinite(loss):
            raise ValueError('Non-finite loss')
        report['loss_before_step'] = float(loss.detach())
        loss.backward()
        grads = [p.grad for p in trainable.values() if p.grad is not None]
        report['gradient_tensors'] = len(grads)
        if not grads or not all(torch.isfinite(g).all().item() for g in grads):
            raise ValueError('Missing or non-finite gradients')
        report['gradient_norm_before_clipping'] = float(torch.nn.utils.clip_grad_norm_(trainable.values(), 1.0))
        if not math.isfinite(report['gradient_norm_before_clipping']) or report['gradient_norm_before_clipping'] <= 0:
            raise ValueError('No learning signal')
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        report['optimizer_steps'] = 1
        del optimizer, loss
        deltas = {n: float((p.detach().cpu() - before[n]).abs().max()) for n, p in trainable.items()}
        report['changed_adapter_tensors'] = sum(d > 0 for d in deltas.values())
        report['max_adapter_change'] = max(deltas.values())
        if report['max_adapter_change'] <= 0:
            raise ValueError('Optimizer did not update adapter weights')
        del before
        model.eval()
        with torch.no_grad():
            after_loss = model(**batch).loss.item()
        report['loss_after_step_same_fixture'] = after_loss
        adapter = output / 'adapter'
        model.peft_config['default'].base_model_name_or_path = download['model']
        model.peft_config['default'].revision = download['revision']
        model.save_pretrained(adapter, safe_serialization=True)
        saved = load_file(str(adapter / 'adapter_model.safetensors'))
        if not saved or any(not torch.isfinite(t).all().item() for t in saved.values()):
            raise ValueError('Invalid serialized adapter')
        report['saved_adapter_tensors'] = len(saved)
        report['adapter_sha256'] = sha(adapter / 'adapter_model.safetensors')
        del saved
        save('reloading_adapter')
        model.load_adapter(str(adapter), adapter_name='roundtrip', is_trainable=False)
        model.set_adapter('roundtrip')
        model.eval()
        with torch.no_grad():
            reloaded_loss = model(**batch).loss.item()
        report['loss_after_reload_same_fixture'] = reloaded_loss
        if abs(reloaded_loss - after_loss) > 1e-4 or not torch.isfinite(torch.tensor(reloaded_loss)):
            raise ValueError('Reloaded adapter failed loss consistency check')
        report['peak_allocated_bytes'] = torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes'] = torch.cuda.max_memory_reserved()
        report['status'] = 'passed'
        save('complete')
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['traceback'] = traceback.format_exc()
        save('failed')
        raise


if __name__ == '__main__':
    main()
