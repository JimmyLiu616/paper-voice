"""Download the explicitly catalogued public PDFs and render unmodified selected pages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import httpx

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--render-only',action='store_true');args=parser.parse_args()
    catalog=json.loads((ROOT/'evaluation/public-documents/sources.json').read_text(encoding='utf-8'))
    output=ROOT/'.runtime/public-documents';output.mkdir(parents=True,exist_ok=True)
    images=output/'images';images.mkdir(exist_ok=True)
    records=[]
    with httpx.Client(follow_redirects=True,timeout=60) as client:
        for item in catalog['sources']:
            path=output/(item['id']+'.pdf')
            if not path.exists():
                if args.render_only:raise FileNotFoundError(path)
                if os.name=='nt':
                    # Use Windows certificate validation for official sites with older CA chains.
                    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                        str(ROOT/'scripts/download_public_pdf.ps1'),'-Uri',item['url'],'-Destination',str(path)],check=True,timeout=90)
                else:
                    response=client.get(item['url']);response.raise_for_status();path.write_bytes(response.content)
            if not path.read_bytes().startswith(b'%PDF'):raise ValueError('Not a PDF: '+item['id'])
            record=dict(item,pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),images=[])
            for page in item['pages']:
                prefix=images/f'{item["id"]}-p{page}'
                subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-singlefile','-r','150','-png',str(path),str(prefix)],check=True,timeout=60)
                picture=prefix.with_suffix('.png')
                record['images'].append({'page':page,'path':str(picture.relative_to(ROOT)).replace('\\','/'),
                                         'sha256':hashlib.sha256(picture.read_bytes()).hexdigest()})
            records.append(record)
            print(item['id'],path.stat().st_size,'bytes;',len(record['images']),'rendered pages',flush=True)
    (ROOT/'evaluation/public-documents/manifest.json').write_text(json.dumps({'retrieval_date':catalog['retrieval_date'],
        'dpi':150,'synthetic':False,'capture':'PDF rasterization, not physical camera photographs','sources':records},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
