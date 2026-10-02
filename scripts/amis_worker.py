"""Offline NLLB Amis draft -> MMS speech; no human-confirmation stage."""
import argparse
import gc
import io
import json
import os
from pathlib import Path
import re
import time
import unicodedata

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
ROOT = Path(__file__).resolve().parents[1]
DIALECTS = {'ami_Xiug':'秀姑巒', 'ami_Coas':'海岸', 'ami_Heng':'恆春',
            'ami_Mala':'馬蘭', 'ami_Sout':'南勢'}


def validate_source(source, dialect):
    source=source.strip()
    if not 1 <= len(source) <= 80 or not any(c.isalnum() for c in source):
        raise ValueError('請輸入 1–80 字的中文完整短句。')
    if dialect not in DIALECTS:
        raise ValueError('不支援此阿美語譯文語別。')
    return source


def speech_text(text, vocab):
    # Respect glottal/apostrophe letters. Never silently discard unsupported
    # letters, digits, or untranslated Hanzi through VITS normalization.
    text=unicodedata.normalize('NFC',text.lower()).replace('’',"'").replace('‘',"'").replace('ʼ',"'")
    text=re.sub(r'[，。！？、；：,.!?;:"「」『』（）()“”\s]+',' ',text).strip()
    unsupported=sorted(set(text)-(set(vocab)-{'|','0','<unk>'}))
    if unsupported:
        raise ValueError('譯文含語音模型不支援的字元，未略過朗讀：'+' '.join(unsupported))
    if not text or not any(c.isalpha() for c in text) or len(text)>500:
        raise ValueError('阿美語譯文為空或超過 500 字元，無法朗讀。')
    return text


class Translator:
    def __init__(self):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        torch.set_num_threads(4)
        folder=ROOT/'.runtime/nllb-formosan'
        self.tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True,src_lang='zho_Hant')
        self.model=AutoModelForSeq2SeqLM.from_pretrained(folder,local_files_only=True).eval()

    def translate(self, source, dialect):
        import torch
        source=validate_source(source,dialect)
        self.tokenizer.src_lang='zho_Hant'
        target=self.tokenizer.convert_tokens_to_ids(dialect)
        if target==self.tokenizer.unk_token_id:
            raise ValueError('模型缺少指定阿美語語別。')
        inputs=self.tokenizer(source,return_tensors='pt')
        with torch.inference_mode():
            ids=self.model.generate(**inputs,forced_bos_token_id=target,max_new_tokens=180,
                num_beams=5,no_repeat_ngram_size=4,renormalize_logits=True,do_sample=False)[0]
        if ids[-1].item()!=self.tokenizer.eos_token_id:
            raise ValueError('翻譯未完整生成，請縮短中文原文。')
        text=self.tokenizer.decode(ids,skip_special_tokens=True).strip()
        if not text:
            raise ValueError('模型沒有產生譯文，請換一段中文短句。')
        return text


class Speaker:
    def __init__(self):
        import torch
        from transformers import VitsModel, AutoTokenizer
        torch.set_num_threads(4)
        folder=ROOT/'.runtime/mms-tts-ami'
        self.tokenizer=AutoTokenizer.from_pretrained(folder,local_files_only=True)
        self.model=VitsModel.from_pretrained(folder,local_files_only=True).eval()

    def speak(self, translation):
        import numpy as np
        import torch
        import soundfile as sf
        text=speech_text(translation,self.tokenizer.get_vocab())
        with torch.inference_mode():
            torch.manual_seed(42)
            wave=self.model(**self.tokenizer(text,return_tensors='pt')).waveform[0].cpu().numpy()
        rate=self.model.config.sampling_rate
        if not wave.size or not np.isfinite(wave).all() or np.max(np.abs(wave))<=.001 or wave.size>rate*90:
            raise ValueError('阿美語音檔格式異常，未播放。')
        out=io.BytesIO();sf.write(out,wave,rate,format='WAV',subtype='PCM_16')
        return out.getvalue(),text


def run(body, audio_path):
    source=validate_source(body['source'],body['dialect'])
    start=time.perf_counter()
    translator=Translator();translation=translator.translate(source,body['dialect'])
    del translator;gc.collect()
    translated_at=time.perf_counter()
    result={'source':source,'dialect':body['dialect'],'translation':translation,
            'translation_seconds':round(translated_at-start,3),
            'warning':'AI 翻譯與朗讀草稿，可能誤譯或漏譯；請以中文原文為準。語別選擇影響譯文，MMS 使用同一阿美語聲音，未驗證與各語別的發音一致。',
            'speech_error':'','model_text':''}
    # Translation remains inspectable if synthesis fails; no confirmation gate.
    try:
        speaker=Speaker();audio,text=speaker.speak(translation)
        audio_path.write_bytes(audio);result['model_text']=text
    except (ValueError,ImportError,OSError) as exc:
        result['speech_error']=str(exc)
    result['speech_seconds']=round(time.perf_counter()-translated_at,3)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--audio',type=Path,required=True)
    args=parser.parse_args()
    body=json.loads(args.request.read_text(encoding='utf8'))
    try:result=run(body,args.audio)
    except (ValueError,ImportError,OSError) as exc:
        args.result.write_text(json.dumps({'error':str(exc)},ensure_ascii=False),encoding='utf8')
        raise SystemExit(2)
    args.result.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')


if __name__=='__main__':main()
