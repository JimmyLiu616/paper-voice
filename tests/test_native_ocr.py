import asyncio
from pathlib import Path
import pytest
import app
from scripts import native_ocr


def test_direct_ocr_preserves_native_lines_and_english_word_spacing(monkeypatch):
    monkeypatch.setattr(native_ocr, 'recognize', lambda _: {'lines':[
        {'words':[{'text':'Please','x':1},{'text':'apply','x':2}]},
        {'words':[{'text':'10','x':1},{'text':'月','x':2}]}]})
    monkeypatch.setattr(app,'windows_ocr_powershell',lambda _:pytest.fail('unnecessary fallback'))
    assert app.windows_ocr(b'image') == 'Please apply\n10月'


@pytest.mark.parametrize('error',[ImportError('not installed'), OSError('engine unavailable'), TimeoutError('timeout')])
def test_native_failure_uses_existing_powershell_path(monkeypatch,error):
    def fail(_): raise error
    monkeypatch.setattr(native_ocr,'recognize',fail)
    monkeypatch.setattr(app,'windows_ocr_powershell',lambda data:'fallback' if data==b'image' else '')
    assert app.windows_ocr(b'image') == 'fallback'


@pytest.mark.parametrize('fail',[False,True])
def test_native_temporary_image_is_removed_after_success_or_failure(monkeypatch,fail):
    seen=[]
    async def operation(path):
        seen.append(path)
        assert path.read_bytes()==b'image'
        if fail: raise OSError('bad image')
        return {'lines':[]}
    monkeypatch.setattr(native_ocr,'recognize_path',operation)
    if fail:
        with pytest.raises(OSError): native_ocr.recognize(b'image')
    else:
        assert native_ocr.recognize(b'image')=={'lines':[]}
    assert seen and not seen[0].exists() and not seen[0].parent.exists()


def test_native_wait_has_bounded_timeout(monkeypatch):
    async def operation(path): return {'lines':[]}
    async def bounded(awaitable,timeout):
        assert timeout==8
        awaitable.close()
        raise TimeoutError()
    monkeypatch.setattr(native_ocr,'recognize_path',operation)
    monkeypatch.setattr(asyncio,'wait_for',bounded)
    with pytest.raises(TimeoutError): native_ocr.recognize(b'image')
