import app


def fields(result):
    return {f['key']:f['value'] for f in result['fields']}


def test_standalone_document_heading_keeps_numbered_list_until_next_section():
    raw='應備文件：\n一、借用證正本，查驗後歸還。\n二、設備領取單。\n三、費用：免費。\n※說明\n請依號碼領取。'
    result=fields(app.validate_extraction({},raw))
    assert result['required_documents']=='一、借用證正本，查驗後歸還。\n二、設備領取單。'
    assert result['amount']=='免費。'


def test_bilingual_heading_with_missing_ocr_numbers_preserves_original_list():
    raw='Documents Required:\n、借用證正本，\n驗畢歸還。\n、領取單影本。\n四、證書費：每份新臺幣五十元\n※說明\n僅限本人領取。'
    result=fields(app.validate_extraction({},raw))
    assert result['required_documents']=='、借用證正本，\n驗畢歸還。\n、領取單影本。'
    assert result['amount']=='每份新臺幣五十元'


def test_numbered_section_does_not_swallow_sibling_heading_without_colon():
    raw='一、應備文件：\n（一）借用證。\n（二）領取單。\n二、領取規定\n限本人領取。'
    result=fields(app.validate_extraction({},raw))
    assert result['required_documents']=='（一）借用證。\n（二）領取單。'


def test_note_marker_in_content_is_not_a_section_boundary():
    raw='費用：新臺幣五十元，\n表格標有※說明者免收。\n※備註\n本表請妥善保存。'
    result=fields(app.validate_extraction({},raw))
    assert result['amount']=='新臺幣五十元，\n表格標有※說明者免收。'


def test_fee_fix_does_not_accept_an_invented_amount():
    raw='費用：新臺幣五十元\n※說明\n次日領取。'
    result=fields(app.validate_extraction({'amount':{'value':'新臺幣五百元','evidence':raw}},raw))
    assert result['amount']==''
