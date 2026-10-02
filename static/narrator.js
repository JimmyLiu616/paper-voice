'use strict';
(function(root){
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
  if(typeof module==='object'&&module.exports){module.exports={create};return;}
  const el=id=>document.getElementById(id),player=el('audio');
  let url=null,lastText='',lastLabel='',running=false,health={};
  const names={'zh-TW':'華語',nan:'台語',hakka:'客語',ami:'阿美語'};
  const info={
    'zh-TW':'以台灣華語朗讀中文回答。',
    nan:'中文回答將翻譯成台語草稿並朗讀；首次切換模型需要較久。',
    hakka:'客語目前支援生活通知的期限、文件、費用與部分例外句型；不支援的回答會保留中文並說明原因。',
    ami:'中文回答將翻譯成阿美語草稿並朗讀；五種譯文語別共用同一阿美語聲音。'
  };
  const status=t=>{el('narration-status').textContent=t;};
  function selection(){return {language:el('output-language').value,dialect:el('output-dialect').value};}
  function enabled(){const l=selection().language;return l==='zh-TW'||!!health[{nan:'taigi_ready',hakka:'hakka_ready',ami:'amis_ready'}[l]];}
  function updateButtons(){el('replay-answer').disabled=running||!lastText||!enabled();}
  function clearAudio(){player.pause();player.hidden=true;player.removeAttribute('src');if(url)URL.revokeObjectURL(url);url=null;}
  function clearOutput(){clearAudio();el('narration-source').textContent='';el('narration-translation').textContent='';el('narration-warning').hidden=true;}
  const flow=create({
    request:(body,signal)=>api('/api/narrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal}).then(r=>r.json()),
    busy:b=>{running=b;updateButtons();},halt:()=>player.pause(),fail:e=>status(e.message),
    apply:async(r,current)=>{
      el('narration-source').textContent=r.source;
      el('narration-translation').textContent=r.translation||'尚未產生譯文。';
      el('narration-warning').textContent=r.warning;el('narration-warning').hidden=!r.warning;
      if(r.speech_error||!r.audio_base64){status('未播放：'+(r.speech_error||'未收到音檔。')+' 已保留中文；如有部分譯文，僅供參考。');return;}
      const bytes=Uint8Array.from(atob(r.audio_base64),c=>c.charCodeAt(0));
      url=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));player.src=url;player.hidden=false;player.playbackRate=Number(el('speed').value);
      status(names[r.language]+'朗讀中，可暫停或重播。');
      try{await player.play();}catch{if(current())status('音檔已完成，請按播放器播放。');}
    }
  });
  function remember(text,label){lastText=text;lastLabel=label;updateButtons();}
  async function speak(text,label='回答'){
    flow.stop();clearOutput();remember(text,label);el('narration-context').textContent=label;
    el('narration-source').textContent=text;
    const s=selection();el('narration-language').textContent=names[s.language]+(s.dialect?'・'+el('output-dialect').selectedOptions[0].textContent:'');
    if(!enabled()){status('這個語言的本機模型尚未就緒，請參考安裝說明或切換其他語言。');return;}
    status(s.language==='zh-TW'?'正在產生華語語音…':'正在翻譯並產生語音，完成後自動播放；首次可能需數十秒。');
    await flow.run({text,...s});
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
  el('replay-answer').onclick=()=>speak(lastText,lastLabel);
  el('stop-btn').onclick=()=>{flow.stop();status('已停止；尚未完成的舊結果不會播放。');};
  el('speed').onchange=()=>{player.playbackRate=Number(el('speed').value);};
  player.addEventListener('ended',()=>status('朗讀完成，可按播放器重播，或切換語言重讀。'));
  root.addEventListener('pagehide',()=>{flow.stop();clearAudio();});languageChanged();
})(typeof window==='object'?window:globalThis);
