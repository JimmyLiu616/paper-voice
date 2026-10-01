"""Direct Windows OCR binding; same engine, bitmap decoder and word geometry as ocr.ps1."""
import asyncio
import importlib
import importlib.util
from pathlib import Path
import tempfile


def prepare_runtime():
    # Windows OCR can load a DLL that prevents a later first import of torch
    # (c10.dll / WinError 1114). Initialize torch before WinRT when installed.
    # No model is loaded here. Errors propagate so app can use PowerShell OCR.
    if importlib.util.find_spec('torch') is not None:
        importlib.import_module('torch')


async def recognize_path(path):
    prepare_runtime()
    from winrt.windows.storage import StorageFile, FileAccessMode
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    import winrt.windows.foundation.collections  # Registers WinRT collection projections.
    file = await StorageFile.get_file_from_path_async(str(path.resolve()))
    stream = await file.open_async(FileAccessMode.READ)
    bitmap = None
    try:
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        engine = (OcrEngine.try_create_from_language(Language('zh-Hant-TW'))
                  or OcrEngine.try_create_from_user_profile_languages())
        if engine is None:
            raise RuntimeError('Windows OCR language is not installed')
        result = await engine.recognize_async(bitmap)
        return {'language':engine.recognizer_language.language_tag, 'lines':[
            {'text':line.text, 'words':[
                {'text':word.text, 'x':word.bounding_rect.x, 'y':word.bounding_rect.y,
                 'width':word.bounding_rect.width, 'height':word.bounding_rect.height}
                for word in line.words]} for line in result.lines]}
    finally:
        if bitmap is not None:
            bitmap.close()
        stream.close()


def recognize(image):
    # Called by app's worker thread, not the FastAPI event loop.
    async def bounded(path):
        return await asyncio.wait_for(recognize_path(path), timeout=8)
    with tempfile.TemporaryDirectory(prefix='paper-voice-native-ocr-') as tmp:
        path = Path(tmp) / 'document.jpg'
        path.write_bytes(image)
        return asyncio.run(bounded(path))
