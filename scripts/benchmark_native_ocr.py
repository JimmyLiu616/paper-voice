"""Pair original PowerShell and native Windows OCR; optionally run actual photo APIs."""
import argparse,hashlib,io,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app
from scripts.native_ocr import recognize, prepare_runtime
from PIL import Image,ImageOps
from fastapi.testclient import TestClient


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--public-images',type=Path)
    parser.add_argument('--photos',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    sources=[ROOT/'samples/notice.png',ROOT/'samples/event.png']
    if args.public_images:sources.extend(sorted(args.public_images.glob('*.png')))
    plan={'scope':'Same image preparation and Windows zh-Hant-TW engine. OCR text identity; not an OCR accuracy score. Photo pairs have preloaded Gemma and use one observation per condition. OS caches are not cleared.',
          'app_sha256':app.APP_REVISION,'jpeg_quality':93,'images':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]}
    (args.output/'plan.json').write_bytes((json.dumps(plan,indent=2)+'\n').encode())
    (args.output/'runner.py').write_bytes(Path(__file__).read_bytes())
    (args.output/'app.py').write_bytes((ROOT/'app.py').read_bytes())
    startup=time.monotonic(); prepare_runtime()
    (args.output/'runtime-init.json').write_text(json.dumps({'seconds':round(time.monotonic()-startup,4),'note':'Same initialization performed at app startup; excluded from per-image OCR timer'}),encoding='utf-8')
    rows=[]
    for index,path in enumerate(sources):
        with Image.open(path) as original:
            im=ImageOps.exif_transpose(original).convert('RGB');im.thumbnail((1800,1800))
            buffer=io.BytesIO();im.save(buffer,format='JPEG',quality=93)
        image=buffer.getvalue();results={}
        for mode in (['powershell','native'] if index%2==0 else ['native','powershell']):
            started=time.monotonic()
            text=app.windows_ocr_powershell(image) if mode=='powershell' else app.ocr_reference_text(recognize(image))
            assert text
            results[mode]={'seconds':round(time.monotonic()-started,4),'text':text}
        assert results['native']['text']==results['powershell']['text'],path.name
        row={'name':path.name,'native_seconds':results['native']['seconds'],'powershell_seconds':results['powershell']['seconds'],
             'characters':len(results['native']['text']),'text_identical':True,
             'text_sha256':hashlib.sha256(results['native']['text'].encode()).hexdigest()}
        rows.append(row);print(json.dumps(row),flush=True)
    (args.output/'ocr-pairs.json').write_bytes((json.dumps(rows,indent=2)+'\n').encode())
    if not args.photos:return
    native=app.windows_ocr;photo_rows=[]
    with TestClient(app.app,headers={'X-PaperVoice':'local-ui'}) as client:
        client.post('/api/warmup').raise_for_status()
        for sample,mode in [('notice','powershell'),('notice','native'),('event','native'),('event','powershell')]:
            app.windows_ocr=app.windows_ocr_powershell if mode=='powershell' else native
            path=ROOT/'samples'/f'{sample}.png';started=time.monotonic()
            response=client.post('/api/analyze',files={'file':(path.name,path.read_bytes(),'image/png')});response.raise_for_status()
            identifier=response.json()['id'];deadline=time.monotonic()+300
            while time.monotonic()<deadline:
                job=client.get('/api/jobs/'+identifier).json()
                if job['status'] in ('done','error'):break
                time.sleep(.1)
            assert job['status']=='done',job.get('error')
            row={'sample':sample,'mode':mode,'seconds':round(time.monotonic()-started,3),'result':job['result']}
            photo_rows.append(row)
            with (args.output/'photo-results.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
            client.delete('/api/jobs/'+identifier)
            print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    app.windows_ocr=native
    summary=[]
    for sample in ['notice','event']:
        old=next(r for r in photo_rows if r['sample']==sample and r['mode']=='powershell')
        new=next(r for r in photo_rows if r['sample']==sample and r['mode']=='native')
        summary.append({'sample':sample,'powershell_seconds':old['seconds'],'native_seconds':new['seconds'],
                        'transcript_identical':old['result']['raw_text']==new['result']['raw_text'],
                        'fields_identical':old['result']['fields']==new['result']['fields']})
    (args.output/'photo-summary.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
