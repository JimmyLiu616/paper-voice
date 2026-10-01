import app


def line(text, x, y):
    return {'words': [{'text': text, 'x': x, 'y': y, 'width': 160, 'height': 16}]}


def test_parallel_paragraphs_are_not_interleaved_by_height():
    data = {'lines': [line('費用：首份100元，', 20, 100),
                      line('第二份起20元。', 20, 120),
                      line('First copy: 100', 230, 100),
                      line('Additional copies: 20', 230, 120)]}
    assert app.ocr_reference_text(data) == ('費用：首份100元，\n第二份起20元。\n'
                                            'First copy: 100\nAdditional copies: 20')


def test_word_joining_keeps_chinese_together_and_english_words_separate():
    data = {'lines': [{'words': [{'text': '申請', 'x': 10}, {'text': '文件', 'x': 30}]},
                      {'words': [{'text': 'Required', 'x': 70}, {'text': 'Documents', 'x': 10}]},
                      {'words': []}]}
    assert app.ocr_reference_text(data) == '申請文件\nDocuments Required'


def test_missing_ocr_lines_remains_optional():
    assert app.ocr_reference_text({}) == ''
