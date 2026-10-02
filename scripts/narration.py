"""Full-sentence segmentation and validated PCM WAV joining for narration."""
import io
import re
import wave


def sentences(text,limit=80,max_parts=6):
    text=text.strip()
    if not text:
        raise ValueError('沒有可翻譯的文字。')
    # Keep semicolons/commas and qualifications together, never truncate.
    parts=[m.group().strip() for m in re.finditer(r'[^。！？!?\n]+[。！？!?\n]*',text)]
    if not parts or len(parts)>max_parts or any(len(p)>limit for p in parts):
        raise ValueError('翻譯朗讀每次最多 6 個完整短句，每句 80 字；請縮小問題範圍或選擇華語朗讀完整內容。未截斷原文。')
    if re.sub(r'\s','',''.join(parts))!=re.sub(r'\s','',text):
        raise ValueError('無法完整分句，未略過文字。')
    return parts


def join_wav(clips):
    frames=[];fmt=None
    for clip in clips:
        with wave.open(io.BytesIO(clip),'rb') as w:
            current=(w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype())
            if current[3]!='NONE' or not w.getnframes() or (fmt and fmt!=current):
                raise ValueError('語音片段格式不一致。')
            fmt=current;frames.append(w.readframes(w.getnframes()))
    if not fmt:raise ValueError('沒有產生音檔。')
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(fmt[0]);w.setsampwidth(fmt[1]);w.setframerate(fmt[2])
        pause=b'\0'*(int(fmt[2]*.25)*fmt[0]*fmt[1])
        w.writeframes(pause.join(frames))
    return out.getvalue()
