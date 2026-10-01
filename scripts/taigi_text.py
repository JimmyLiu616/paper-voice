"""Local Taiwanese Hanji pronunciation draft and explicit MMS input normalization.

Taibun is transliteration, not Mandarin-to-Taiwanese sentence translation.
"""
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
PUNCTUATION = '，。！？、；：,.!?;:「」『』（）()“”"'


def is_han(char):
    return unicodedata.name(char, '').startswith(('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-'))


def mms_text(poj, vocab):
    # Reject numbers BEFORE compatibility normalization; never drop document dates.
    if any(c.isnumeric() or is_han(c) for c in poj):
        raise ValueError('請使用白話字；漢字請先轉寫，數字請先寫成台語讀法。')
    # MMS public data preparation defaults to NFKC (including superscript ⁿ -> n).
    # This preserves a nasal letter instead of silently dropping the unsupported ⁿ.
    text = unicodedata.normalize('NFKC', poj.lower())
    punctuation = set(unicodedata.normalize('NFKC', PUNCTUATION))
    text = ''.join(' ' if c in punctuation or c.isspace() else c for c in text)
    text = re.sub(r'\s+', ' ', text).strip()
    unsupported = sorted(set(text) - (set(vocab) - {'|'}))
    if unsupported:
        raise ValueError('模型不支援這些字元：' + ' '.join(unsupported) + '。請核對白話字。')
    if not any(c.isalpha() for c in text):
        raise ValueError('請輸入可朗讀的白話字句子。')
    if len(text) > 500:
        raise ValueError('白話字超過 500 字元，請分句。')
    return text


@lru_cache(maxsize=1)
def converter():
    from taibun import Converter
    return Converter(system='POJ', dialect='south', format='mark', sandhi='none',
                     punctuation='none', convert_non_cjk=False)


def load_vocab():
    return json.loads((ROOT / '.runtime/mms-tts-nan/vocab.json').read_text(encoding='utf-8'))


def pronunciation_draft(text):
    text = text.strip()
    if not 1 <= len(text) <= 80 or not any(is_han(c) for c in text):
        raise ValueError('請輸入 1–80 字的台語漢字短句。')
    if any(not (is_han(c) or c.isspace() or c in PUNCTUATION) for c in text):
        raise ValueError('請使用台語漢字；數字請寫成讀法，外文與符號請先移除。')
    poj = unicodedata.normalize('NFC', converter().get(text))
    unknown = ''.join(dict.fromkeys(c for c in poj if is_han(c)))
    if unknown:
        raise ValueError('字典未收錄這些字，無法完整轉寫：' + unknown)
    vocab = load_vocab()
    normalized = mms_text(poj, vocab)
    return {'text':text, 'poj':poj, 'model_text':normalized,
            'engine':'Taibun 1.1.8 / POJ / south / citation tones',
            'warning':'這是台語漢字的讀音草稿，不是華語翻譯；多音字、文白讀與變調仍須核對。MMS 前處理會將鼻音上標 ⁿ 轉為 n，標點轉為空白；聲音口音尚待驗證。'}
