'use strict';
(function(root) {
  // Cancellation also rejects late responses from a server still finishing CPU work.
  function create({request, apply, fail, busy, halt}) {
    let active=null;
    function stop(){const old=active;active=null;old?.abort();halt();busy(false);}
    async function run(body){
      stop();const token=new AbortController();active=token;busy(true);
      try {const result=await request(body,token.signal);
        if(active!==token)return;
        await apply(result,()=>active===token);
      }catch(e){if(active===token&&e.name!=='AbortError')fail(e);}
      finally{if(active===token){active=null;busy(false);}}
    }
    return {run,stop};
  }
  if(typeof module==='object'&&module.exports){module.exports={create};return;}
  const el=id=>document.getElementById(id);
  let ready=false,url=null,running=false;
  const status=text=>{el('amis-status').textContent=text;};
  function clearAudio(){el('amis-audio').pause();el('amis-audio').hidden=true;el('amis-audio').removeAttribute('src');if(url)URL.revokeObjectURL(url);url=null;}
  const flow=create({
    request:(body,signal)=>api('/api/amis-translate-speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal}).then(r=>r.json()),
    busy:value=>{running=value;el('amis-run').disabled=value||!ready;},halt:()=>el('amis-audio').pause(),fail:e=>status(e.message),
    apply:async(result,current)=>{
      el('amis-original').textContent=result.source;
      el('amis-output').textContent=result.translation;
      if(result.speech_error||!result.audio_base64){status('翻譯草稿已產生，語音未完成：'+(result.speech_error||'未收到音檔'));return;}
      const bytes=Uint8Array.from(atob(result.audio_base64),c=>c.charCodeAt(0));
      url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));
      el('amis-audio').src=url;el('amis-audio').hidden=false;
      status('翻譯與音檔已完成，正在播放阿美語草稿。');
      try{await el('amis-audio').play();}catch{if(current())status('音檔已完成；瀏覽器阻擋自動播放，請按下方播放器。');}
    }
  });
  function invalidate(){flow.stop();clearAudio();el('amis-original').textContent='';el('amis-output').textContent='';status('輸入中文短句後，按一次「翻譯並朗讀」。');}
  root.PaperVoiceAmis={stop:flow.stop,reset(){invalidate();el('amis-source').value='';el('amis-source-kind').value='manual';},setReady(value){ready=!!value;if(!ready)flow.stop();el('amis-run').disabled=!ready||running;if(!ready)status('阿美語模型尚未安裝，請參考 README。');}};
  for(const id of ['amis-source','amis-dialect','amis-source-kind','amis-field'])el(id).addEventListener('input',invalidate);
  el('amis-example').onclick=()=>{invalidate();el('amis-source-kind').value='manual';el('amis-source').value='本活動免費，不必繳費。';};
  el('amis-source-btn').onclick=()=>{
    invalidate();const field=state.result?.fields.find(f=>f.key===el('amis-field').value);
    if(!field?.evidence){status('請先讀取文件並選擇有原文的重點。');return;}
    if(field.evidence.length>80){status('這段原文超過 80 字，請自行選取完整短句；不會自動截斷條件。');return;}
    el('amis-source-kind').value='document';el('amis-source').value=field.evidence;
  };
  el('amis-run').onclick=()=>{
    stopSpeech();invalidate();
    const source=el('amis-source').value.trim(),doc=el('amis-source-kind').value==='document';
    if(!source){status('請先輸入中文短句。');return;}
    if(doc&&!state.job){status('請先讀取文件，或切換成手動輸入。');return;}
    status('本機正在翻譯及產生語音，完成後自動播放；首次約需數十秒。');
    flow.run({source,dialect:el('amis-dialect').value,job_id:doc?state.job:null});
  };
  el('amis-stop').onclick=()=>{flow.stop();status('已停止。尚未完成的結果不會自動播放。');};
  el('amis-audio').addEventListener('ended',()=>status('阿美語草稿朗讀完成，可用播放器重播。'));
  root.addEventListener('pagehide',()=>{flow.stop();clearAudio();});
})(typeof window==='object'?window:globalThis);
