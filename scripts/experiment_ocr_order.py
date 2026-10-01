"""Paired OCR reading-order experiment; real model calls, no production changes.

Both modes use the same cached Windows OCR word boxes and original image.
Results are development evidence, not a held-out accuracy estimate.
"""
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app


def join_words(words):
    text = ''
    for word in sorted(words, key=lambda w: w['x']):
        token = word['text']
        if text and re.search(r'[A-Za-z]$', text) and re.match(r'[A-Za-z]', token):
            text += ' '
        text += token
    return text


def render(data, mode):
    lines = [line for line in data['lines'] if line.get('words')]
    if mode == 'native':
        return '\n'.join(join_words(line['words']) for line in lines)
    # The current application's row-merging baseline, frozen for comparison.
    lines.sort(key=lambda line: (min(w['y'] for w in line['words']), min(w['x'] for w in line['words'])))
    rows = []
    for line in lines:
        top = min(w['y'] for w in line['words'])
        height = max(w['height'] for w in line['words'])
        if rows and abs(rows[-1]['top'] - top) < height * .45:
            rows[-1]['words'].extend(line['words'])
        else:
            rows.append({'top': top, 'words': list(line['words'])})
    return '\n'.join(join_words(row['words']) for row in rows)


async def run(args):
    out = ROOT / '.runtime/layout-experiments' / args.name
    out.mkdir(parents=True, exist_ok=False)
    image = args.image.read_bytes()
    boxes = args.boxes.read_bytes()
    metadata = {'app_sha256': app.APP_REVISION,
                'image_sha256': hashlib.sha256(image).hexdigest(),
                'boxes_sha256': hashlib.sha256(boxes).hexdigest(),
                'health': await app.health(), 'questions': args.question,
                'scope': 'One development image; same image, boxes, model settings and prompts; only hint reading order differs.'}
    for name, content in [('app.py', (ROOT/'app.py').read_bytes()), ('runner.py', Path(__file__).read_bytes()), ('boxes.json', boxes)]:
        (out/name).write_bytes(content)
    (out/'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    original = app.windows_ocr
    try:
        for mode in ['rows', 'native']:
            hint = render(json.loads(boxes.decode('utf-8-sig')), mode)
            app.windows_ocr = lambda image, hint=hint: hint
            start = time.monotonic()
            job_id = app.new_job('layout-experiment')
            try:
                await app.process_job(job_id, base64.b64encode(image).decode(), None)
                job = app.jobs[job_id]
                answers = []
                record = {'mode': mode, 'job': job, 'answers': answers}
                path = out/(mode+'.json')
                path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'mode':mode, 'stage':'transcription-and-extraction', 'status':job['status']}, ensure_ascii=False), flush=True)
                if job['status'] == 'done':
                    for question in args.question:
                        try:
                            answer = await app.ask(app.Question(job_id=job_id, question=question))
                            answers.append({'question': question, 'answer': answer})
                        except app.HTTPException as exc:
                            answers.append({'question':question, 'error':exc.detail, 'status_code':exc.status_code})
                        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
                record['seconds'] = round(time.monotonic()-start, 2)
                path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps({'mode':mode, 'status':job['status'], 'seconds':record['seconds'], 'answers':answers}, ensure_ascii=False), flush=True)
            finally:
                app.jobs.pop(job_id, None)
    finally:
        app.windows_ocr = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--boxes', type=Path, required=True)
    parser.add_argument('--question', action='append', default=[])
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.name):
        parser.error('Use a new run name with letters, digits, hyphens or underscores')
    asyncio.run(run(args))
