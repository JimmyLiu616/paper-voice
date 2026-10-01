"""One-shot local ASR worker: release model RAM when each request completes."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'


def decode_bounded(path, max_seconds=30):
    import av
    import numpy as np
    chunks, count = [], 0
    with av.open(path if hasattr(path, 'read') else str(path)) as container:
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                data = converted.to_ndarray().reshape(-1)
                count += len(data)
                if count > max_seconds * 16000:
                    raise ValueError('音檔最多 30 秒，請分段提問。')
                chunks.append(data)
        for converted in resampler.resample(None):
            data = converted.to_ndarray().reshape(-1)
            count += len(data)
            if count > max_seconds * 16000:
                raise ValueError('音檔最多 30 秒，請分段提問。')
            chunks.append(data)
    if count < 3200:
        raise ValueError('音檔太短，請錄製完整問題。')
    return np.concatenate(chunks).astype('float32') / 32768


def recognize(path, model_dir, language='zh', beam=1):
    import numpy as np
    from faster_whisper import WhisperModel
    from opencc import OpenCC
    started = time.monotonic()
    audio = decode_bounded(path)
    if np.max(np.abs(audio)) < 0.003:
        raise ValueError('沒有偵測到清楚的聲音，請靠近麥克風重錄。')
    model = WhisperModel(str(model_dir), device='cpu', compute_type='int8',
                         cpu_threads=4, num_workers=1, local_files_only=True)
    loaded = time.monotonic()
    segments, info = model.transcribe(audio, language=None if language == 'auto' else language,
        task='transcribe', beam_size=beam, temperature=0, vad_filter=True,
        vad_parameters={'min_silence_duration_ms': 500},
        condition_on_previous_text=False, hallucination_silence_threshold=1)
    raw = ''.join(s.text for s in segments).strip()
    # Convert characters only; avoid phrase substitution (e.g. 文件 -> 檔案).
    text = OpenCC('s2tw').convert(raw)
    if not text:
        raise ValueError('未辨識到問題，請放慢速度重錄或改用文字。')
    if len(text) > 300:
        raise ValueError('問題超過 300 字，請縮短後重錄。')
    return {'text': text, 'raw_text': raw, 'language': info.language,
        'duration': round(len(audio) / 16000, 2),
        'seconds': round(time.monotonic() - started, 2),
        'load_seconds': round(loaded - started, 2), 'beam_size': beam,
        'device': 'cpu', 'compute_type': 'int8',
        'model': 'adi-gov-tw/Taiwan-Tongues-ASR-CE-v1.0',
        'revision': '46b5eb7ee167ac2fd06cfe02f40e8fac416e5086'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('audio')
    parser.add_argument('output')
    parser.add_argument('--language', choices=['zh', 'en', 'auto'], default='zh')
    parser.add_argument('--beam', type=int, choices=[1, 5], default=1)
    args = parser.parse_args()
    try:
        result = recognize(args.audio, Path(__file__).resolve().parents[1] / '.runtime' / 'taiwan-tongues-asr', args.language, args.beam)
    except ValueError as exc:
        result = {'error': str(exc)}
    except Exception:
        result = {'error': 'ASR 無法讀取音檔或模型，請檢查安裝，或改用 WAV 音檔。'}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
