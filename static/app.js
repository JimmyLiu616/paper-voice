'use strict';
const $ = id => document.getElementById(id);
const state = {file:null, mode:'image', job:null, result:null, run:0, busy:false, preview:null};
const headers = {'X-PaperVoice':'local-ui'};
let asrReady=false, asrBusy=false, qaBusy=false, recorder=null, recordStream=null, recordTimer=null, voiceRun=0;
let modelReady = false;
let initialPreparationRequested = false;
function message(text='') { $('alert').textContent=text; $('alert').hidden=!text; }
function textNode(tag,text,cls) { const node=document.createElement(tag); node.textContent=text; if(cls)node.className=cls; return node; }
async function api(path, options={}) {
  const response = await fetch(path,{...options,headers:{...headers,...options.headers}});
  if(!response.ok) { let detail; try {detail=(await response.json()).detail;}catch{} throw new Error(typeof detail==='string'?detail:`操作失敗（${response.status}），請稍後再試。`); }
  return response;
}
const modelPreparation = PaperVoiceWarmup.create({
  request: () => api('/api/warmup', {method:'POST'}).then(r => r.json()),
  onState: status => {
    $('model-preparation').textContent = {
      preparing:'正在提前準備模型，你可以先選照片或拍攝文件。',
      ready:'模型已預先準備，可以送出文件。',
      busy:'模型正在處理文件，新文件將依序處理。',
      unavailable:'可直接送出文件；首次處理可能需要較久。'
    }[status];
  }
});
function buttons() {
  $('analyze-btn').disabled=state.busy || !modelReady || (state.mode==='image'?!state.file:$('source-text').value.trim().length<4);
  $('speak-btn').disabled=!state.result || state.busy;
  $('ask-btn').disabled=!state.result || state.busy || qaBusy;
  $('reanalyze-btn').disabled=state.busy;
  if($('record-btn')) {
    $('record-btn').disabled=!state.result || state.busy || !asrReady || asrBusy;
    $('audio-file').disabled=!state.result || state.busy || !asrReady || asrBusy || !!recorder;
  }
  $('corpus-preview-btn').disabled=!state.result || state.busy;
}
function mode(value) {
  state.mode=value;
  for(const m of ['image','text']) { const selected=m===value; $(m+'-input').hidden=!selected; $(m+'-tab').classList.toggle('selected',selected); $(m+'-tab').setAttribute('aria-selected',String(selected)); $(m+'-tab').tabIndex=selected?0:-1; }
  buttons();
}
function stopSpeech() { window.PaperVoiceNarrator.stop(); }
async function discardJob(id) { if(id) await api('/api/jobs/'+encodeURIComponent(id),{method:'DELETE'}).catch(()=>{}); }
function resetResult() {
  voiceRun++; if(recorder && recorder.state==='recording')recorder.stop();
  $('corpus-preview').hidden=true;
  state.run++;state.busy=false;stopSpeech();discardJob(state.job);state.job=null;state.result=null;
  window.PaperVoiceNarrator.reset();
  $('progress').hidden=true;$('result-content').hidden=true;$('empty-state').hidden=false;
  $('result-meta').textContent='等待放入文件';$('answers').replaceChildren(textNode('p','先讀取一份文件，就能開始提問。','hint'));
  $('step2').classList.remove('current');$('step3').classList.remove('current');buttons();
}
function chooseFile(file) {
  if(!file)return;
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)){message('請選擇 JPG、PNG 或 WebP 圖片。PDF 請先轉成圖片。');return;}
  if(file.size>12*1024*1024){message('圖片請小於 12 MB。');return;}
  resetResult(); mode('image'); message(); state.file=file;
  if(state.preview)URL.revokeObjectURL(state.preview);
  state.preview=URL.createObjectURL(file); $('preview').src=state.preview; $('file-name').textContent=file.name;
  $('dropzone').hidden=true; $('preview-wrap').hidden=false; buttons();
  if(modelReady)modelPreparation.prepare();
}
$('file-input').addEventListener('change',e=>chooseFile(e.target.files[0]));
$('change-file').onclick=()=>$('file-input').click();
$('image-tab').onclick=()=>mode('image'); $('text-tab').onclick=()=>mode('text');
for(const id of ['image-tab','text-tab']) $(id).addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault(); const target=state.mode==='image'?'text':'image';mode(target);$(target+'-tab').focus();}});
$('source-text').addEventListener('input',buttons);
for(const type of ['dragenter','dragover']) $('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.add('drag');});
for(const type of ['dragleave','drop']) $('dropzone').addEventListener(type,e=>{e.preventDefault();$('dropzone').classList.remove('drag');if(type==='drop')chooseFile(e.dataTransfer.files[0]);});
async function sample(name,label) {
  try { const r=await fetch(`/samples/${name}.png`); if(!r.ok)throw new Error('範例圖片尚未建立。'); chooseFile(new File([await r.blob()],label+'.png',{type:'image/png'})); }
  catch(e){message(e.message);}
}
$('sample-notice').onclick=()=>sample('notice','自製範例－補件通知');
$('sample-event').onclick=()=>sample('event','自製範例－社區活動');
$('clear-btn').onclick=()=>{resetResult();state.file=null;if(state.preview)URL.revokeObjectURL(state.preview);state.preview=null;$('preview').removeAttribute('src');$('file-input').value='';$('source-text').value='';$('dropzone').hidden=false;$('preview-wrap').hidden=true;message();buttons();};
function render(result) {
  state.result=result; $('empty-state').hidden=true; $('result-content').hidden=false;
  $('document-title').textContent=result.title; $('document-type').textContent=result.document_type;
  $('result-meta').textContent=`${result.seconds} 秒 · ${result.input_source==='image'?'圖片辨識':'文字整理'}`;
  $('fact-grid').replaceChildren();
  for(const fact of result.fields) {
    const card=textNode('article','','fact-card'); card.append(textNode('div',fact.label,'fact-label'));
    card.append(textNode('p',fact.value || (fact.state==='needs_review'?'需要人工確認':'未找到明確資訊'),fact.value?'':'not-found'));
    if(fact.evidence) { const detail=document.createElement('details');detail.append(textNode('summary','原文已對應 · 查看依據'),textNode('blockquote',fact.evidence));card.append(detail); }
    $('fact-grid').append(card);
  }
  $('raw-text').value=result.raw_text;
  $('condition-list').replaceChildren(...(result.conditions_raw||[]).map(t=>textNode('p','文件提醒：'+t,'hint')));
  $('ocr-reference').textContent=result.ocr_reference||'本次未使用 Windows OCR（文字模式或系統未提供）。';
  $('result-warnings').replaceChildren(...result.warnings.map(w=>textNode('p',w,'warning')));
  $('step2').classList.add('current'); $('step3').classList.add('current');
  $('answers').replaceChildren(textNode('p','可以點選上面的常見問題，或輸入想知道的事。','hint'));buttons();
}
async function analyze(confirmedText) {
  const text = confirmedText || (state.mode==='text'?$('source-text').value.trim():null);
  resetResult();const run=state.run;state.busy=true;buttons();message();$('progress').hidden=false;
  const started=Date.now();
  try {
    let response;
    if(text)response=await api('/api/analyze-text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    else {const body=new FormData();body.append('file',state.file);response=await api('/api/analyze',{method:'POST',body});}
    const {id}=await response.json(); if(run!==state.run){discardJob(id);return;} state.job=id;
    while(run===state.run) {
      const job=await(await api('/api/jobs/'+id)).json();if(run!==state.run)return;
      $('progress-stage').textContent=job.stage;
      $('progress-time').textContent=`已等待 ${Math.round((Date.now()-started)/1000)} 秒 · 首次載入模型需要較久`;
      if(job.raw_text)$('raw-text').value=job.raw_text;
      if(job.status==='done'){render(job.result);break;}
      if(job.status==='error')throw new Error(job.error);
      await new Promise(resolve=>setTimeout(resolve,400));
    }
  } catch(e) {if(run===state.run)message(e.message);}
  finally {if(run===state.run){state.busy=false;$('progress').hidden=true;buttons();}}
}
$('analyze-btn').onclick=()=>analyze();
$('reanalyze-btn').onclick=()=>{if($('raw-text').value.trim().length<4){message('請輸入至少四個字。');return;}analyze($('raw-text').value);};
function readText(){if(!state.result)return '';return $('read-target').value==='raw'?state.result.raw_text:(state.result.summary.join('。\n')||'這份文件未找到可核對的重點，請查看原圖與辨識原文。');}
$('speak-btn').onclick=()=>{const text=readText();if(!text)return;window.PaperVoiceNarrator.speak(text,'文件：'+($('read-target').value==='raw'?'辨識原文':'重要資訊'));$('conversation').scrollIntoView({behavior:'smooth',block:'start'});};
$('question-form').addEventListener('submit',async e=>{
  e.preventDefault();if(!state.result||state.busy||qaBusy)return;
  const question=$('question').value.trim();if(!question)return;
  stopSpeech();qaBusy=true;const job=state.job,epoch=PaperVoiceNarrator.epoch;
  $('ask-btn').disabled=true;message();const waiting=textNode('p','正在根據文件查找答案…','hint');$('answers').prepend(waiting);
  try{
    const answer=await(await api('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:job,question})})).json();
    if(state.job!==job)return;
    const item=textNode('article','','answer-item');item.append(textNode('strong',question),textNode('p',answer.answer));
    if(answer.evidence)item.append(textNode('blockquote','原文依據：'+answer.evidence));
    const listen=textNode('button','用所選語言聽這個回答','secondary-button');listen.type='button';
    listen.onclick=()=>PaperVoiceNarrator.speak(answer.answer,'回答：'+question,answer);
    item.append(listen);$('answers').querySelectorAll(':scope > p.hint').forEach(node=>node.remove());$('answers').prepend(item);
    if($('question').value.trim()===question)$('question').value='';
    PaperVoiceNarrator.remember(answer.answer,'回答：'+question,answer);
    if(PaperVoiceNarrator.epoch===epoch)PaperVoiceNarrator.speak(answer.answer,'回答：'+question,answer);
  }catch(e){if(state.job===job)message(e.message);}
  finally{qaBusy=false;waiting.remove();buttons();}
});
document.querySelectorAll('[data-question]').forEach(button=>button.onclick=()=>{$('question').value=button.dataset.question;if(!state.result){message('請先放入文件並完成辨識。');return;}$('question-form').requestSubmit();});
$('export-btn').onclick=()=>{if(!state.result)return;const blob=new Blob([JSON.stringify({...state.result,notice:'AI 輔助結果，請對照原文件確認；原文對應不代表影像辨識正確。'},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='紙聲通-識讀結果.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('font-btn').onclick=()=>{const on=document.documentElement.classList.toggle('large-text');$('font-btn').setAttribute('aria-pressed',String(on));};
$('about-btn').onclick=()=>$('about-dialog').showModal();$('close-about').onclick=()=>$('about-dialog').close();
$('about-dialog').addEventListener('click',e=>{if(e.target===$('about-dialog'))$('about-dialog').close();});
window.addEventListener('pagehide',()=>{stopSpeech();if(state.job)fetch('/api/jobs/'+encodeURIComponent(state.job),{method:'DELETE',headers,keepalive:true}).catch(()=>{});});
async function checkHealth(){
  try {const health=await(await api('/api/health')).json();modelReady=health.model_ready;
    asrReady=health.asr_ready;
    window.PaperVoiceNarrator.setReady(health);
    $('asr-model-status').textContent=asrReady?'Taiwan Tongues ASR CE · 本機已就緒':'指定語音模型尚未準備完成';
    $('model-status').textContent=modelReady?'Gemma 3 · 本機已就緒':(health.ollama?'模型下載／準備中':'請啟動 Ollama');$('model-status').classList.toggle('wait',!modelReady);
    if(modelReady && !initialPreparationRequested){initialPreparationRequested=true;modelPreparation.prepare();}
  }catch{$('model-status').textContent='本機服務連線中斷';$('model-status').classList.add('wait');modelReady=false;}
  buttons();
}
const voicePanel=document.createElement('details');voicePanel.className='voice-question';
voicePanel.innerHTML='<summary>用語音提問（選用）</summary><div class="voice-actions"><button id="record-btn" type="button" class="secondary-button" disabled>● 錄音提問</button><label class="audio-upload">或選音檔<input id="audio-file" type="file" accept="audio/*" disabled></label><label>語音模式 <select id="asr-language"><option value="zh">中文／在地語音</option><option value="en">英文</option><option value="auto">自動判斷</option></select></label></div><p id="asr-model-status" class="hint">正在檢查指定語音模型</p><p id="asr-status" class="hint" role="status">最長 30 秒、8 MB。辨識後請核對問題文字，再按「提問並朗讀」。台語／客語品質尚待實測。</p>';
$('question-form').before(voicePanel);
async function sendAudio(blob, job, run) {
  if(!blob.size)return;
  asrBusy=true;buttons();$('asr-status').textContent='本機語音辨識中，首次載入需要較久…';
  const body=new FormData();body.append('file',blob,'question.audio');
  try {
    const result=await(await api('/api/transcribe?language='+encodeURIComponent($('asr-language').value),{method:'POST',body})).json();
    if(run!==voiceRun || job!==state.job)return;
    $('question').value=result.text;$('question').focus();
    $('asr-status').textContent=`辨識完成（${result.seconds} 秒）。請核對上方問題，必要時改字，再按「提問並朗讀」。`;
  }catch(e){if(run===voiceRun)message(e.message);}
  finally{asrBusy=false;buttons();}
}
$('record-btn').onclick=async()=>{
  if(recorder?.state==='recording'){recorder.stop();return;}
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder){message('此瀏覽器不支援錄音，請選擇音檔。');return;}
  if(!state.result || asrBusy)return;
  const job=state.job,run=++voiceRun;
  try {
    stopSpeech();recordStream=await navigator.mediaDevices.getUserMedia({audio:true});
    if(run!==voiceRun || job!==state.job){recordStream.getTracks().forEach(t=>t.stop());return;}
    const chunks=[];recorder=new MediaRecorder(recordStream);
    recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    recorder.onstop=()=>{
      clearTimeout(recordTimer);recordStream?.getTracks().forEach(t=>t.stop());
      const mime=recorder.mimeType;recorder=null;recordStream=null;$('record-btn').textContent='● 錄音提問';buttons();
      if(run===voiceRun && job===state.job)sendAudio(new Blob(chunks,{type:mime}),job,run);
    };
    recorder.start();$('record-btn').textContent='■ 停止並辨識';$('asr-status').textContent='錄音中，請說出你想問的事…';buttons();
    recordTimer=setTimeout(()=>{if(recorder?.state==='recording')recorder.stop();},29000);
  }catch(e){recordStream?.getTracks().forEach(t=>t.stop());recorder=null;message('無法使用麥克風，請允許錄音權限或改選音檔。');buttons();}
};
$('audio-file').onchange=e=>{const file=e.target.files[0];e.target.value='';if(!file || !state.result)return;if(file.size>8*1024*1024){message('音檔請小於 8 MB。');return;}sendAudio(file,state.job,++voiceRun);};
window.addEventListener('pagehide',()=>{voiceRun++;clearTimeout(recordTimer);recordStream?.getTracks().forEach(t=>t.stop());});
$('corpus-preview-btn').onclick=async()=>{
  if(!state.result)return;const job=state.job;
  try {
    const result=await(await api('/api/corpus/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:job,corrected:$('raw-text').value})})).json();
    if(job!==state.job)return;
    $('corpus-original').value=result.original;$('corpus-corrected').value=result.corrected;
    $('corpus-reviewed').checked=false;$('corpus-rights').checked=false;
    $('corpus-status').textContent=`自動遮蔽 ${result.redactions} 處；本次修正編輯距離 ${result.metrics.edit_distance}。此數字不是整體模型正確率。`;
    $('corpus-preview').hidden=false;
  }catch(e){message(e.message);}
};
for(const id of ['corpus-original','corpus-corrected','corpus-provenance'])$(id).addEventListener('input',()=>{$('corpus-reviewed').checked=false;$('corpus-rights').checked=false;});
$('corpus-export-btn').onclick=async()=>{
  try {
    const response=await api('/api/corpus/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({original:$('corpus-original').value,corrected:$('corpus-corrected').value,provenance:$('corpus-provenance').value,reviewed:$('corpus-reviewed').checked,rights_confirmed:$('corpus-rights').checked})});
    const url=URL.createObjectURL(await response.blob()),link=document.createElement('a');link.href=url;link.download='paper-voice-correction.jsonl';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('corpus-status').textContent='已下載至本機，尚未對外提交。公開前需由維護者再次審核。';
  }catch(e){message(e.message);}
};
checkHealth();setInterval(checkHealth,20000);
