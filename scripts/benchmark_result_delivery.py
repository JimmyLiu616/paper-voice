"""Measure polling delivery delay against one real job, without changing model work."""
from pathlib import Path
import concurrent.futures,json,sys,time,threading,argparse,hashlib,statistics
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app
from fastapi.testclient import TestClient

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(exist_ok=False,parents=True)
 plan={'app_sha256':app.APP_REVISION,'frontend_sha256':hashlib.sha256((ROOT/'static/app.js').read_bytes()).hexdigest(),'intervals_seconds':[1.3,.4],'samples':['notice','event']*3,'scope':'Two polling clients observe the same actual OCR/VLM job. Completion time recorded immediately after process_job returns; not a browser rendering benchmark.'}
 (args.output/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
 completed={}; original=app.process_job
 async def traced(jid,*a,**kw):
  await original(jid,*a,**kw);completed[jid]=time.monotonic()
 app.process_job=traced;rows=[]
 try:
  with TestClient(app.app,headers={'X-PaperVoice':'local-ui'}) as client:
   client.post('/api/warmup').raise_for_status()
   for sample in plan['samples']:
    p=ROOT/'samples'/f'{sample}.png';started=time.monotonic();response=client.post('/api/analyze',files={'file':(p.name,p.read_bytes(),'image/png')});response.raise_for_status();jid=response.json()['id'];barrier=threading.Barrier(2)
    def poll(interval):
     count=0;barrier.wait()
     while time.monotonic()-started<300:
      job=client.get('/api/jobs/'+jid).json();count+=1
      if job['status'] in ('done','error'):
       assert job['status']=='done',job
       return {'interval_seconds':interval,'received':time.monotonic(),'queries':count,'result':job['result']}
      time.sleep(interval)
     raise TimeoutError('job incomplete')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:pair=list(pool.map(poll,[1.3,.4]))
    assert pair[0]['result']==pair[1]['result']
    row={'sample':sample,'inference_seconds':round(completed[jid]-started,4),'identical_result':True,'polls':[{'interval_seconds':x['interval_seconds'],'delivery_delay_seconds':round(x['received']-completed[jid],4),'queries':x['queries']} for x in pair]}
    rows.append(row);print(json.dumps(row),flush=True);client.delete('/api/jobs/'+jid)
    (args.output/'rows.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 finally:app.process_job=original
 summary={'jobs':len(rows),'same_job_comparisons':True,'baseline_median_delay':round(statistics.median(r['polls'][0]['delivery_delay_seconds'] for r in rows),4),'candidate_median_delay':round(statistics.median(r['polls'][1]['delivery_delay_seconds'] for r in rows),4),'median_paired_saved':round(statistics.median(r['polls'][0]['delivery_delay_seconds']-r['polls'][1]['delivery_delay_seconds'] for r in rows),4),'limitation':'Each polling phase can favor either interval; no claim every request becomes faster. More small loopback GET requests; model calls unchanged.'}
 (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
