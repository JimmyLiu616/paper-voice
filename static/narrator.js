'use strict';
(function(root){
  function narrationInput(text,language,context={}){
    if(language==='hakka'&&context.found===true&&Object.hasOwn(context,'narration_evidence')){
      return typeof context.narration_evidence==='string'&&context.narration_evidence.trim()
        ?{text:context.narration_evidence.trim(),basis:'evidence'}
        :{text,basis:'unresolved'};
    }
    if(language==='hakka'&&context.found===true&&typeof context.evidence==='string'&&context.evidence.trim()){
      return {text:context.evidence.trim(),basis:'evidence'};
    }
    return {text,basis:'answer'};
  }
  function create({request,apply,fail,busy,halt}){
    let active=null,epoch=0;
    function stop(){epoch++;const old=active;active=null;old?.abort();halt();busy(false);}
    async function run(body){stop();const token=new AbortController();active=token;busy(true);
      try{const result=await request(body,token.signal);if(active!==token)return;await apply(result,()=>active===token);}
      catch(e){if(active===token&&e.name!=='AbortError')fail(e);}
      finally{if(active===token){active=null;busy(false);}}
    }
    return {run,stop,get epoch(){return epoch;}};
  }
  if(typeof module==='object'&&module.exports){module.exports={create,narrationInput};return;}
  const el=id=>document.getElementById(id),player=el('audio');
  let url=null,lastText='',lastLabel='',lastContext={},running=false,health={};
  const names={'zh-TW':'華語',nan:'台語',hakka:'客語',ami:'阿美語'};
  const info={
    'zh-TW':'以台灣華語朗讀中文回答。',
    nan:'中文回答將翻譯成台語草稿並朗讀；首次切換模型需要較久。',
    hakka:'客語重點解說：有原文依據時，直接依據原文整理期限、文件、費用與例外後朗讀；無法完整處理時保留中文。',
    ami:'中文回答將翻譯成阿美語草稿並朗讀；五種譯文語別共用同一阿美語聲音。'
  };
  const status=t=>{el('narration-status').textContent=t;};
  function selection(){return {language:el('output-language').value,dialect:el('output-dialect').value};}
  function enabled(){const l=selection().language;return l==='zh-TW'||!!health[{nan:'taigi_ready',hakka:'hakka_ready',ami:'amis_ready'}[l]];}
  function updateButtons(){el('replay-answer').disabled=running||!lastText||!enabled();}
  function clearAudio(){player.pause();player.hidden=true;player.removeAttribute('src');if(url)URL.revokeObjectURL(url);url=null;}
  function clearOutput(){clearAudio();el('narration-source').textContent='';el('narration-translation').textContent='';el('narration-warning').hidden=true;el('narration-facts').replaceChildren();el('narration-facts-panel').hidden=true;}
  const flow=create({
    request:(body,signal)=>api('/api/narrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal}).then(r=>r.json()),
    busy:b=>{running=b;updateButtons();},halt:()=>player.pause(),fail:e=>status(e.message),
    apply:async(r,current)=>{
      el('narration-source').textContent=r.source;
      el('narration-translation').textContent=r.translation||'尚未產生譯文。';
      el('narration-warning').textContent=r.warning;el('narration-warning').hidden=!r.warning;
      const labels={deadline:'截止時間',documents:'應備文件',age_fee:'年齡與費用',completed:'已完成事項的例外',completed_registration:'已登記者免重複申請',delegation:'委託辦理文件',paper_only:'申請方式',holiday:'假日順延',fee:'費用與退費',legacy:'通知事項'};
      el('narration-facts').replaceChildren(...(r.frames||[]).map(frame=>{const li=document.createElement('li');li.textContent=(labels[frame.kind]||'通知事項')+'：'+frame.evidence;return li;}));
      el('narration-facts-panel').hidden=!(r.frames||[]).length;
      if(r.speech_error||!r.audio_base64){status('未播放：'+(r.speech_error||'未收到音檔。')+' 已保留中文；如有部分譯文，僅供參考。');return;}
      const bytes=Uint8Array.from(atob(r.audio_base64),c=>c.charCodeAt(0));
      url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));player.src=url;player.hidden=false;player.playbackRate=Number(el('speed').value);
      status(names[r.language]+'朗讀中，可暫停或重播。');
      try{await player.play();}catch{if(current())status('音檔已完成，請按播放器播放。');}
    }
  });
  function remember(text,label,context={}){lastText=text;lastLabel=label;lastContext=context;updateButtons();}
  async function speak(text,label='回答',context={}){
    flow.stop();clearOutput();remember(text,label,context);
    const s=selection(),input=narrationInput(text,s.language,context);
    el('narration-context').textContent=(input.basis==='evidence'?'依據原文解說 · ':'')+label;
    el('narration-source').textContent=input.text;
    el('narration-language').textContent=names[s.language]+(s.dialect?'・'+el('output-dialect').selectedOptions[0].textContent:'');
    if(input.basis==='unresolved'){status('無法唯一對應完整原文段落，已保留中文；請縮小問題範圍或切換華語。');return;}
    if(!enabled()){status('這個語言的本機模型尚未就緒，請參考安裝說明或切換其他語言。');return;}
    status(s.language==='zh-TW'?'正在產生華語語音…':s.language==='hakka'?'正在整理公文重點、核對條件並產生客語語音…':'正在翻譯並產生語音，完成後自動播放；首次可能需數十秒。');
    await flow.run({text:input.text,...s});
  }
  function changed(){
    flow.stop();clearOutput();el('language-hint').textContent=info[selection().language];
    el('narration-language').textContent=names[selection().language];
    status(lastText?'已切換語言，按「用此語言重讀」聽同一份內容。':'先讀取文件，再提問；回答會自動翻譯朗讀。');updateButtons();
  }
  function languageChanged(){
    const options={hakka:[['sixian','四縣腔'],['hailu','海陸腔']],ami:[['ami_Xiug','秀姑巒'],['ami_Coas','海岸'],['ami_Heng','恆春'],['ami_Mala','馬蘭'],['ami_Sout','南勢']]}[selection().language]||[['','預設']];
    el('output-dialect').replaceChildren(...options.map(([value,label])=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;}));
    el('dialect-control').hidden=options.length===1;
    el('dialect-label').textContent=selection().language==='ami'?'譯文語別':'客語腔調';changed();
  }
  root.PaperVoiceNarrator={speak,remember,stop:flow.stop,get epoch(){return flow.epoch;},
    setReady(h){health=h;updateButtons();},reset(){flow.stop();clearOutput();remember('','');status('先讀取文件，再提問；回答會自動翻譯朗讀。');el('narration-context').textContent='尚未開始';}};
  el('output-language').onchange=languageChanged;el('output-dialect').onchange=changed;
  el('replay-answer').onclick=()=>speak(lastText,lastLabel,lastContext);
  el('stop-btn').onclick=()=>{flow.stop();status('已停止；尚未完成的舊結果不會播放。');};
  el('speed').onchange=()=>{player.playbackRate=Number(el('speed').value);};
  player.addEventListener('ended',()=>status('朗讀完成，可按播放器重播，或切換語言重讀。'));
  root.addEventListener('pagehide',()=>{flow.stop();clearAudio();});languageChanged();
})(typeof window==='object'?window:globalThis);
