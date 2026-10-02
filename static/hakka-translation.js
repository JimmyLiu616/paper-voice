'use strict';
(function() {
  function create({snapshot,request,apply,status}) {
    let sequence=0;
    return async()=>{
      const before=snapshot(),run=++sequence;status('working');
      try {
        const result=await request(before);
        if(run!==sequence)return;
        if(JSON.stringify(before)!==JSON.stringify(snapshot())){status('stale');return;}
        apply(result);status('ready',result.warning);
      }catch(error){if(run===sequence)status(JSON.stringify(before)===JSON.stringify(snapshot())?'error':'stale',error.message);}
    };
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={create};
  if(typeof document==='undefined')return;
  const el=id=>document.getElementById(id);
  const invalidate=()=>{
    window.PaperVoiceHakka.invalidate();
    el('hakka-confirm').checked=false;el('hakka-text').value='';
    el('hakka-translation-output').textContent='';
  };
  el('hakka-source').addEventListener('input',invalidate);
  el('hakka-source-kind').onchange=()=>{invalidate();el('hakka-source').value='';};
  el('hakka-source-btn').onclick=()=>{
    if(!state.result)return;
    const field=state.result.fields.find(f=>f.key===el('hakka-field').value);
    const source=field?.evidence||state.result.raw_text;
    if(source.length>80){message('原文超過 80 字，請在文件原文模式貼入完整短句，保留否定與例外。');return;}
    invalidate();el('hakka-source-kind').value='document';el('hakka-source').value=source;
    el('hakka-translate-status').textContent='已帶入文件原文，可產生客語草稿。';
  };
  el('hakka-example').onclick=()=>{
    invalidate();el('hakka-source-kind').value='manual';
    el('hakka-source').value='本活動免費，不必繳費。';
    el('hakka-translate-status').textContent='這是自製中文範例，可產生客語草稿。';
  };
  el('hakka-translate').onclick=create({
    snapshot:()=>({source:el('hakka-source').value.trim(),dialect:el('hakka-dialect').value,
      kind:el('hakka-source-kind').value,job:state.job,text:el('hakka-text').value}),
    request:async s=>{
      if(!s.source||s.source.length>80)throw Error('請輸入 1–80 字的完整中文短句。');
      if(s.kind==='document'&&!s.job)throw Error('請先讀取文件，或切換手動輸入中文。');
      return (await api('/api/hakka-translation',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({source:s.source,dialect:s.dialect,job_id:s.kind==='document'?s.job:null})})).json();
    },
    apply:r=>{el('hakka-text').value=r.reading;el('hakka-translation-output').textContent='客語草稿（保留原數字）：'+r.translation;el('hakka-confirm').checked=false;},
    status:(s,detail)=>{
      el('hakka-translate').disabled=s==='working';
      if(s==='working'){window.PaperVoiceHakka.invalidate();el('hakka-confirm').checked=false;el('hakka-translation-output').textContent='';}
      if(s==='error')el('hakka-text').value='';
      el('hakka-translate-status').textContent={working:'正在本機轉換通知短句…',ready:detail,error:detail,stale:'原文、文件或腔調已變更，未套用舊草稿。'}[s];
    }
  });
})();
