'use strict';
(function(root) {
  function create({snapshot,request,apply,status}) {
    let sequence=0;
    return async function translate() {
      const before=snapshot(),current=++sequence;status('working');
      try {
        const result=await request(before);
        if(current!==sequence)return;
        if(JSON.stringify(before)!==JSON.stringify(snapshot())){status('stale');return;}
        apply(result);status('ready',result.warning);
      }catch(error){if(current===sequence)status('error',error.message);}
    };
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={create};
  if(typeof document==='undefined')return;
  const el=id=>document.getElementById(id);
  const invalidate=()=>{
    stopSpeech();el('taigi-confirm').checked=false;el('taigi-audio').hidden=true;
    el('taigi-translation-output').textContent='';buttons();
  };
  el('taigi-source-btn').onclick=()=>{
    if(!state.result)return;
    const fact=state.result.fields.find(f=>f.key===el('taigi-field').value);
    const source=fact?.evidence||state.result.raw_text;
    if(source.length>500){message('這段原文較長，請從辨識原文複製一段完整短句。');return;}
    invalidate();el('taigi-source').value=source;el('taigi-hanji').value='';el('taigi-text').value='';
    el('taigi-translate-status').textContent=source.length>80?'這段超過 80 字，請選取一段完整短句；不要省略否定與例外。':'已帶入原文，可產生翻譯草稿。';
  };
  el('taigi-source').addEventListener('input',()=>{invalidate();el('taigi-hanji').value='';el('taigi-text').value='';});
  const translate=create({
    snapshot:()=>({job:state.job,source:el('taigi-source').value.trim(),hanji:el('taigi-hanji').value,poj:el('taigi-text').value}),
    request:async before=>{
      if(!before.job||!before.source||before.source.length>80)throw Error('請先讀取文件，並選取 1–80 字的完整原文短句。');
      return (await api('/api/taigi-translation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:before.job,source:before.source})})).json();
    },
    apply:result=>{
      invalidate();el('taigi-translation-output').textContent='台語譯文（保留原數字）：'+result.translation;
      el('taigi-hanji').value=result.reading||result.translation;el('taigi-text').value=result.poj||'';
      el('taigi-confirm').checked=false;
    },
    status:(status,detail)=>{
      el('taigi-translate').disabled=status==='working';
      if(status==='working')invalidate();
      el('taigi-translate-status').textContent={working:'正在本機產生翻譯草稿，首次切換模型可能需要數十秒…',stale:'內容或文件已變更，未套用舊翻譯。',ready:detail,error:detail}[status];
    }
  });
  el('taigi-translate').onclick=translate;
})(typeof globalThis!=='undefined'?globalThis:this);
