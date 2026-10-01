"""No-speech preflight avoids heavy loads and preserves speech decoding settings."""
from types import SimpleNamespace
import numpy as np
import pytest
import faster_whisper
import faster_whisper.vad
from scripts import asr_worker


def forbid_model(*args, **kwargs):
    raise AssertionError('ASR model must not load for rejected input')


def test_vad_without_speech_rejects_before_asr_model_allocation(monkeypatch):
    audio = np.full(16000, .02, dtype='float32')
    monkeypatch.setattr(asr_worker, 'decode_bounded', lambda _: audio)
    seen = []
    def vad(value, options):
        assert value is audio
        seen.append(options)
        return []
    monkeypatch.setattr(faster_whisper.vad, 'get_speech_timestamps', vad)
    monkeypatch.setattr(faster_whisper, 'WhisperModel', forbid_model)
    with pytest.raises(ValueError, match='未辨識到問題'):
        asr_worker.recognize('unused', 'unused')
    assert len(seen) == 1 and seen[0].min_silence_duration_ms == 500
    assert seen[0].threshold == .5


def test_existing_quiet_threshold_still_rejects_without_vad_or_asr(monkeypatch):
    monkeypatch.setattr(asr_worker, 'decode_bounded', lambda _: np.zeros(16000, dtype='float32'))
    monkeypatch.setattr(faster_whisper.vad, 'get_speech_timestamps', forbid_model)
    monkeypatch.setattr(faster_whisper, 'WhisperModel', forbid_model)
    with pytest.raises(ValueError, match='沒有偵測到清楚的聲音'):
        asr_worker.recognize('unused', 'unused')


@pytest.mark.parametrize('language,beam', [('zh', 1), ('en', 5), ('auto', 1)])
def test_speech_keeps_original_audio_and_decoder_configuration(monkeypatch, language, beam):
    audio = np.full(16000, .05, dtype='float32')
    monkeypatch.setattr(asr_worker, 'decode_bounded', lambda _: audio)
    monkeypatch.setattr(faster_whisper.vad, 'get_speech_timestamps', lambda *_: [{'start': 100, 'end': 900}])
    calls = []
    class Model:
        def __init__(self, path, **kwargs):
            assert kwargs['device'] == 'cpu' and kwargs['compute_type'] == 'int8'
            assert kwargs['cpu_threads'] == 4 and kwargs['local_files_only'] is True
        def transcribe(self, value, **kwargs):
            assert value is audio  # Preflight must not crop or replace speech audio.
            calls.append(kwargs)
            return [SimpleNamespace(text='需要什麼文件')], SimpleNamespace(language='zh')
    monkeypatch.setattr(faster_whisper, 'WhisperModel', Model)
    result = asr_worker.recognize('unused', 'unused', language, beam)
    assert result['text'] == '需要什麼文件'
    assert calls == [{'language': None if language == 'auto' else language,
                     'task': 'transcribe', 'beam_size': beam, 'temperature': 0,
                     'vad_filter': True, 'vad_parameters': {'min_silence_duration_ms': 500},
                     'condition_on_previous_text': False, 'hallucination_silence_threshold': 1}]


def test_decode_error_does_not_load_asr(monkeypatch):
    def bad_audio(_):
        raise ValueError('音檔太短')
    monkeypatch.setattr(asr_worker, 'decode_bounded', bad_audio)
    monkeypatch.setattr(faster_whisper, 'WhisperModel', forbid_model)
    with pytest.raises(ValueError, match='太短'):
        asr_worker.recognize('unused', 'unused')
