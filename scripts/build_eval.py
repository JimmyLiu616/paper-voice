"""Deterministic original fixture images; all transforms stay within a document split."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[1]


def wrap(draw,text,font,width):
    lines=[]; current=''
    for char in text:
        if current and draw.textlength(current+char,font=font)>width:
            lines.append(current); current=char
        else: current+=char
    if current:lines.append(current)
    return lines


def build():
    source=ROOT/'evaluation/cases.json'; data=json.loads(source.read_text(encoding='utf-8'))
    output=ROOT/'evaluation/images'; output.mkdir(exist_ok=True,parents=True)
    manifest={'version':data['version'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'synthetic':True,'variants':['clean','tilt_blur'],'documents':[]}
    regular=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',30)
    titlefont=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',40)
    seen=set()
    for case in data['cases']:
        if case['family'] in seen:raise ValueError('Each template family must be unique in v1')
        seen.add(case['family'])
        im=Image.new('RGB',(1100,1250),'white'); draw=ImageDraw.Draw(im)
        y=70
        for line in wrap(draw,case['title'],titlefont,960):
            draw.text((70,y),line,font=titlefont,fill='#142f35');y+=62
        y+=35
        for line in case['lines']:
            for piece in wrap(draw,line,regular,960):
                draw.text((70,y),piece,font=regular,fill='#172d35');y+=46
            y+=15
        if y>1200:raise ValueError(f'Clipped fixture: {case["id"]}')
        images={}
        for variant in manifest['variants']:
            rendered=im if variant=='clean' else im.rotate(2.3,Image.Resampling.BICUBIC,expand=True,fillcolor='#dfdfdf').filter(ImageFilter.GaussianBlur(.7))
            name=f'{case["id"]}-{variant}.jpg'; path=output/name
            rendered.save(path,quality=93 if variant=='clean' else 72)
            images[variant]={'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest['documents'].append({'id':case['id'],'split':case['split'],'family':case['family'],
            'reference':case['title']+'\n'+'\n'.join(case['lines']),'images':images})
    (ROOT/'evaluation/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built {len(seen)} document families, {len(seen)*2} images; test split remains reserved.')


if __name__=='__main__':build()
