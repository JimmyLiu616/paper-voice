"""Offline VoxHakka synthesis in an isolated CPU environment; fixed released speaker."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import List
try:
    from scripts.model_policy import verify_files
except ModuleNotFoundError:
    from model_policy import verify_files

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
ROOT = Path(__file__).resolve().parents[1]
DIALECTS = {'sixian': 'hak_sx', 'hailu': 'hak_hl'}


def validate_text(text):
    text = text.strip()
    if not 1 <= len(text) <= 80 or not re.search(r'[\u3400-\u9fff]', text):
        raise ValueError('請輸入 1–80 字的客語漢字短句。')
    if re.search(r'[^\u3400-\u9fff\s，。！？、；：,.!?;:]', text):
        raise ValueError('請使用客語漢字，數字請先改成客語讀法；暫不接受外文或特殊符號。')
    return text


def phoneme_tokens(pronunciations):
    ipa = ' '.join(p.replace(' ', '|') for p in pronunciations)
    tokens = []
    for part in re.split(r'(?<![\d])(?=[\d])|(?<=[\d])(?![\d])', ipa):
        if part.isdigit():
            tokens.append(part)
        else:
            tokens.extend(re.sub(r'[+\-|_]', '', part).replace('，', ' ， '))
    return tokens


def speech_punctuation(text):
    # The released tokenizer has comma/space pauses, but no full-stop tokens.
    # Keep every spoken character; map sentence/list boundaries to supported
    # pauses instead of dropping unknown punctuation in the tokenizer.
    return re.sub(r'[。！？、；：.!?;:\n]+', '，', text)


def synthesize(text, dialect, output):
    text = validate_text(text)
    if dialect not in DIALECTS:
        raise ValueError('目前支援四縣腔與海陸腔。')
    verify_files('formospeech/yourtts-htia-240704', ROOT / '.runtime/voxhakka')
    import numpy as np
    import torch
    import soundfile as sf
    import TTS.tts.configs.vits_config as vits_config
    from TTS.tts.configs.shared_configs import CharactersConfig
    from TTS.utils.synthesizer import Synthesizer
    from formog2p.hakka import g2p

    # VoxHakka uses multi-character tone tokens; preserve list vocabulary order.
    @dataclass
    class ListCharacters(CharactersConfig):
        characters: List[str] = None

    @dataclass
    class ListVitsConfig(vits_config.VitsConfig):
        characters: ListCharacters = None

    vits_config.VitsConfig = ListVitsConfig
    conversion = g2p(speech_punctuation(text), DIALECTS[dialect], include_eng=False)
    if conversion.unknown_words:
        raise ValueError('客語字典未收錄部分用字，請換成已核對的客語短句。')
    tokens = phoneme_tokens(conversion.pronunciations)
    if not tokens:
        raise ValueError('沒有可朗讀的客語音節。')
    model_dir = ROOT / '.runtime/voxhakka'
    config = json.loads((model_dir / 'config.json').read_text(encoding='utf-8'))
    for block in (config, config['model_args']):
        block['speakers_file'] = str(model_dir / 'speakers.pth')
        block['language_ids_file'] = str(model_dir / 'language_ids.json')
        block['d_vector_file'] = [str(model_dir / 'speaker_embs.pth')]
    for key in ['speaker_encoder_model_path', 'speaker_encoder_config_path']:
        config['model_args'][key] = ''
    config['model_args']['use_speaker_encoder_as_loss'] = False
    torch.set_num_threads(4)
    with tempfile.TemporaryDirectory(prefix='paper-voice-hakka-config-') as tmp:
        config_path = Path(tmp) / 'config.json'
        config_path.write_text(json.dumps(config), encoding='utf-8')
        model = Synthesizer(tts_checkpoint=str(model_dir / 'model.pth'),
                            tts_config_path=str(config_path), use_cuda=False)
        try:
            for token in tokens:
                model.tts_model.tokenizer.characters.char_to_id(token)
        except KeyError as exc:
            raise ValueError('模型不支援部分音標，請換句話試聽。') from exc
        torch.manual_seed(42)
        with torch.inference_mode():
            wave = np.asarray(model.tts(tokens, speaker_name='XF', language_name=dialect,
                                        split_sentences=False), dtype=np.float32)
        rate = model.tts_model.config.audio.sample_rate
        if (wave.ndim != 1 or not wave.size or not np.isfinite(wave).all()
                or np.max(np.abs(wave)) <= .001 or len(wave) > rate * 90):
            raise RuntimeError('Invalid generated waveform')
        if model.tts_model.tokenizer.not_found_characters:
            raise ValueError('模型略過了部分音標，已停止播放。')
        sf.write(output, wave, rate, subtype='PCM_16')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--error', type=Path, required=True)
    args = parser.parse_args()
    body = json.loads(args.request.read_text(encoding='utf-8'))
    try:
        synthesize(body['text'], body['dialect'], args.output)
    except ValueError as exc:
        args.error.write_text(str(exc), encoding='utf-8')
        raise SystemExit(2)


if __name__ == '__main__':
    main()
