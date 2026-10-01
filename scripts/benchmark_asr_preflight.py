"""Local synthetic audio benchmark with real ASR and instrumented model loads."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.runtime/asr-preflight-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    import numpy as np
    import soundfile as sf
    sys.path.insert(0, str(ROOT))
    from scripts.asr_worker import decode_bounded
    # Prepare synthetic prompts with the running local Windows TTS service.
    import httpx
    sources = [ROOT / '.runtime' / f'asr-test-{i}.wav' for i in range(2)]
    for path, prompt in zip(sources, ['最晚什麼時候要完成？', '我需要準備什麼文件？']):
        if not path.exists():
            with httpx.Client(timeout=60, headers={'X-PaperVoice': 'local-ui'}) as client:
                response = client.post('http://127.0.0.1:8765/api/speech',
                    json={'text': prompt, 'language': 'zh-TW', 'rate': -1})
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
    baseline = ROOT / 'evaluation/asr-preflight-v1/baseline-worker.py'
    assert baseline.is_file()
    BASE.mkdir(exist_ok=False)
    (BASE / 'baseline-worker.py').write_bytes(baseline.read_bytes())
    (BASE / 'candidate-worker.py').write_bytes((ROOT / 'scripts/asr_worker.py').read_bytes())
    samples = BASE / 'audio'
    samples.mkdir()
    deadline = decode_bounded(ROOT / '.runtime/asr-test-0.wav')
    documents = decode_bounded(ROOT / '.runtime/asr-test-1.wav')
    silence = np.zeros(3 * 16000, dtype='float32')
    click = silence.copy()
    click[16000:16008] = .5
    cases = [
        ('silence', silence, ''),
        ('click', click, ''),
        ('tone', .08 * np.sin(2 * np.pi * 440 * np.arange(48000) / 16000), ''),
        ('noise', np.random.default_rng(42).normal(0, .02, 48000), ''),
        ('deadline', deadline, '最晚什麼時候要完成？'),
        ('documents', documents, '我需要準備什麼文件？'),
        ('quiet-documents', documents * .1, '我需要準備什麼文件？'),
        ('padded-deadline', np.concatenate([silence[:16000], deadline, silence[:16000]]), '最晚什麼時候要完成？'),
    ]
    rows = []
    for name, audio, text in cases:
        path = samples / (name + '.wav')
        sf.write(path, audio, 16000, subtype='PCM_16')
        rows.append({'id': name, 'file': path.name, 'sha256': sha(path),
                     'reference_tts_prompt': text, 'has_synthetic_speech': bool(text)})
    plan = {'scope': 'Four generated non-speech signals and four variants of two Windows Hanhan synthetic questions. No human or Taiwanese/Hakka speech.',
            'baseline_worker_sha256': sha(BASE / 'baseline-worker.py'),
            'cases': rows, 'sampling_rate': 16000, 'beam': 1, 'language': 'zh',
            'method': 'Fresh child process for each item; actual model factory instrumented and delegated unchanged. File-system cache is not cleared.',
            'gates': ['Preserve all speech transcripts and existing silence rejection.',
                      'No new transcript for non-speech; zero ASR model construction when the unchanged VAD finds no speech.',
                      'Compare elapsed times descriptively; one paired sample per fixture is not a population latency estimate.'],
            'no_training': True}
    (BASE / 'plan.json').write_bytes((json.dumps(plan, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'prepared_cases': len(rows), 'baseline_worker_sha256': plan['baseline_worker_sha256']}), flush=True)


def child(worker, audio):
    import faster_whisper
    calls = []
    original = faster_whisper.WhisperModel
    def recorded_model(*args, **kwargs):
        calls.append({'device': kwargs.get('device'), 'compute_type': kwargs.get('compute_type')})
        return original(*args, **kwargs)
    faster_whisper.WhisperModel = recorded_model
    spec = importlib.util.spec_from_file_location('measured_asr_worker', worker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    started = time.monotonic()
    try:
        result = module.recognize(audio, ROOT / '.runtime/taiwan-tongues-asr', 'zh', 1)
        status = 'transcribed'
    except ValueError as exc:
        result, status = {'error': str(exc)}, 'rejected'
    report = {'status': status, 'result': result, 'model_loads': len(calls),
              'recognize_seconds': round(time.monotonic() - started, 3)}
    print(json.dumps(report, ensure_ascii=False), flush=True)


def run(variant):
    plan = json.loads((BASE / 'plan.json').read_text(encoding='utf-8'))
    worker = BASE / (variant + '-worker.py')
    out = BASE / variant
    out.mkdir(exist_ok=False)
    for case in plan['cases']:
        audio = BASE / 'audio' / case['file']
        assert sha(audio) == case['sha256']
        started = time.monotonic()
        process = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), '--child', str(worker), str(audio)],
                                 capture_output=True, text=True, encoding='utf-8', timeout=180,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if process.returncode:
            (out / (case['id'] + '-error.txt')).write_text(process.stderr, encoding='utf-8')
            raise RuntimeError('Child failed: ' + case['id'])
        result = json.loads(process.stdout)
        result.update(id=case['id'], audio_sha256=case['sha256'], worker_sha256=sha(worker),
                      process_seconds=round(time.monotonic() - started, 3))
        with (out / 'results.jsonl').open('a', encoding='utf-8', newline='\n') as file:
            file.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--variant', choices=['baseline', 'candidate'])
    parser.add_argument('--child', nargs=2, metavar=('WORKER', 'AUDIO'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.child:
        child(*args.child)
    elif args.variant:
        run(args.variant)
    else:
        parser.error('Choose --prepare or --variant')
