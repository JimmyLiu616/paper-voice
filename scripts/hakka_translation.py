"""Conservative notice phrase conversion, NOT a general Hakka translation model.

Only whole supported clauses are converted; unknown clauses reject the entire
draft. Shared formal wording is retained for both TTS dialects. Output is an
unreviewed draft. This does not call an LLM or a cloud service.
"""
import re

from scripts.taigi_translation import NUMBER, integer_hanji
from scripts.hakka_worker import validate_text

DATE = r'(?:(?:民國)?[0-9]{1,4}年)?[0-9]{1,2}月[0-9]{1,2}日(?:[上下]午[0-9]{1,2}[時點])?'
DOCUMENT = r'(?:身分證(?:正本|影本)?|(?:填妥的|填好的)?報名表|申請表|戶口名簿(?:影本)?|印章)'
DOCUMENTS = DOCUMENT + r'(?:[、及與和]' + DOCUMENT + r')*'


def documents(text):
    return re.sub(r'[及與和]', '摎', text).replace('填妥的', '填好个').replace('填好的', '填好个')


def date(text):
    return text.replace('上午', '上晝').replace('下午', '下晝')


# Whole clauses only: qualifiers and negatives must never be silently dropped.
RULES = [
    (r'請(?:攜帶|準備|帶)(?P<docs>'+DOCUMENTS+r')', lambda m:'請帶'+documents(m['docs'])),
    (r'(?:應備文件|需要準備|所需文件)[:：]\s*(?P<docs>'+DOCUMENTS+r')', lambda m:'愛準備个文件：'+documents(m['docs'])),
    (r'(?P<docs>'+DOCUMENTS+r')', lambda m:documents(m['docs'])),
    (r'本活動免費', lambda m:'這隻活動免費'),
    (r'(?:費用[:：]\s*)?免費', lambda m:m[0]),
    (r'(?:不必|無須|不用|不需要)繳費', lambda m:'毋使繳費'),
    (r'(?:如|如果)已完成補件', lambda m:'係講已經完成補件'),
    (r'請忽略本通知', lambda m:'請毋使理會這張通知'),
    (r'請(?:於|在)(?P<date>'+DATE+r')前(?P<action>提出申請|補交文件|送達|繳清)', lambda m:'請在'+date(m['date'])+'前'+m['action']),
    (r'(?P<label>補件期限|申請期限|截止日期)[:：]\s*(?P<date>'+DATE+r')(?P<before>前)?', lambda m:m['label']+'：'+date(m['date'])+(m['before'] or '')),
    (r'只接受紙本申請', lambda m:'單淨接受紙本申請'),
    (r'不接受線上申請', lambda m:'毋接受線上申請'),
    (r'逾期不受理', lambda m:'過期毋受理'),
    (r'(?P<age>[0-9]{1,3})歲以上免費', lambda m:m['age']+'歲以上免費'),
    (r'未滿(?P<age>[0-9]{1,3})歲(?:仍須|須)繳(?P<amount>[0-9]{1,4})元', lambda m:'未滿'+m['age']+'歲愛繳'+m['amount']+'元'),
    (r'費用(?:為|是)(?P<amount>[0-9]{1,4})元', lambda m:'費用係'+m['amount']+'元'),
    (r'已繳費者不必再繳', lambda m:'已經繳費个人毋使再繳'),
    (r'尚未繳費者須於(?P<date>'+DATE+r')前繳清', lambda m:'還吂繳費个人愛在'+date(m['date'])+'前繳清'),
]


def reading_draft(translation):
    def replace(match):
        following = translation[match.end():].lstrip()
        if not re.fullmatch('[0-9]+', match.group()) or not following or following[0] not in '年月日號時點元歲份':
            raise ValueError('電話、編號或特殊數字請先人工寫成客語讀法。')
        return integer_hanji(match.group())
    return validate_text(NUMBER.sub(replace, translation))


def translate_notice(source):
    source = source.strip()
    if not 1 <= len(source) <= 80:
        raise ValueError('中文原文請使用 1–80 字的完整短句。')
    parts = re.split(r'([，,。；;\n]+)', source)
    converted = []; changes = []; clauses = 0
    for part in parts:
        if not part.strip() or re.fullmatch(r'[，,。；;\n]+', part):
            converted.append(part); continue
        clause = part.strip(); match = None
        for pattern, render in RULES:
            match = re.fullmatch(pattern, clause)
            if match:
                target = render(match); converted.append(target)
                changes.append({'source':clause, 'draft':target}); clauses += 1
                break
        if match is None:
            raise ValueError('這段含尚未支援的句型，未產生翻譯。請保留完整條件改用支援短句，或在下方輸入人工核對的客語。')
    if not clauses:
        raise ValueError('請輸入包含文字的通知短句。')
    translation = ''.join(converted)
    if NUMBER.findall(source) != NUMBER.findall(translation):
        raise ValueError('數字核對失敗，未產生草稿。')
    return {'translation':translation, 'reading':reading_draft(translation), 'changes':changes,
            'method':'local_notice_rules_v1',
            'warning':'這是生活通知限定句型的客語草稿，並非通用 AI 翻譯。四縣與海陸共用此文字草稿，由語音模型切換腔調。請核對意思、數字讀法及發音；尚未經母語者驗證。'}
