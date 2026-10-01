"""Local-only bundle of the catalogued public documents and recorded evaluations."""
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    base=ROOT/'.runtime/public-documents';catalog=ROOT/'evaluation/public-documents'
    cases=json.loads((catalog/'cases.json').read_text(encoding='utf-8'))['cases']
    sources=json.loads((catalog/'sources.json').read_text(encoding='utf-8'))['sources']
    entries=[(base/(s['id']+'.pdf'),'sources/'+s['id']+'.pdf') for s in sources]
    entries += [(base/'images'/(c['id']+'.png'),'images/'+c['id']+'.png') for c in cases]
    entries += [(p,p.name) for p in catalog.iterdir() if p.is_file()]
    entries += [(p,'runs/'+p.parent.name+'/'+p.name) for p in (base/'runs').glob('*/*') if p.is_file()]
    # Only the explicitly recorded public-document experiments, never arbitrary user uploads.
    layout=ROOT/'.runtime/layout-experiments'
    for run in ['moi-order-v1','moi-order-v2']:
        entries += [(p,'layout-experiments/'+run+'/'+p.name) for p in (layout/run).glob('*') if p.is_file()]
    output=base/'public-document-test-pack.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path,name in entries:archive.write(path,name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise RuntimeError('Archive verification failed')
    print(output)
    print(f'{len(entries)} files; {output.stat().st_size:,} bytes. Local archive only; no publication.')


if __name__=='__main__':main()
