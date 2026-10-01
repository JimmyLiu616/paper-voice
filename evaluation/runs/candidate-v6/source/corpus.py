"""Local, opt-in correction export. Regex screening is NOT complete anonymization."""
import re
import unicodedata

PATTERNS = [
    ('email', re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')),
    ('id', re.compile(r'(?<![A-Za-z0-9])[A-Za-z][12]\d{8}(?!\d)')),
    ('phone', re.compile(r'(?<!\d)(?:\+886[-\s]?|0)(?:\d[-\s]?){7,10}(?!\d)')),
    ('labelled', re.compile(r'(?m)(?:姓名|收件人|聯絡人|住址|地址|身分證字號|身份證字號|病歷號|帳號|學號)\s*[:：][^\n]+')),
    ('long_number', re.compile(r'(?<!\d)\d{7,}(?!\d)')),
]


def redact_pair(original, corrected):
    # Replace the same sensitive string consistently across both sides.
    replacements = {}
    for _, pattern in PATTERNS:
        for text in (original, corrected):
            for match in pattern.finditer(text):
                replacements[match.group()] = '[已遮蔽]'
    for value in sorted(replacements, key=len, reverse=True):
        original, corrected = original.replace(value, '[已遮蔽]'), corrected.replace(value, '[已遮蔽]')
    return original, corrected, len(replacements)


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        next_row = [i]
        for j, cb in enumerate(b, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j-1] + (ca != cb)))
        row = next_row
    return row[-1]


def correction_metric(original, corrected):
    def norm(s):
        return ''.join(c for c in unicodedata.normalize('NFKC', s) if not c.isspace())
    a, b = norm(original), norm(corrected)
    distance = edit_distance(a, b)
    return {'edit_distance': distance, 'reference_characters': len(b),
            'character_error_rate': round(distance / len(b), 4) if b else None,
            'normalization': 'NFKC; remove whitespace; keep punctuation',
            'scope': 'Single human-corrected text pair; not overall model accuracy'}
