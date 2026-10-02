'use strict';
(() => {
  const el = id => document.getElementById(id);
  let ready = false, initialized = false, controller = null, audioUrl = null;
  const stop = () => {
    controller?.abort(); controller = null;
    el('hakka-audio').pause();
    el('hakka-btn').disabled = !ready;
  };
  const invalidate = () => {
    stop();el('hakka-confirm').checked=false;el('hakka-audio').hidden=true;
    el('hakka-audio').removeAttribute('src');
    if(audioUrl){URL.revokeObjectURL(audioUrl);audioUrl=null;}
  };
  window.PaperVoiceHakka = {
    stop, invalidate,
    reset() {
      invalidate();el('hakka-source').value='';el('hakka-text').value='天公落水';
      el('hakka-source-kind').value='manual';el('hakka-translation-output').textContent='';
      el('hakka-translate-status').textContent='可輸入中文短句，或帶入文件原文。';
    },
    setReady(value) {
      ready = !!value;
      el('hakka-btn').disabled = !ready || !!controller;
      if (!initialized || !ready) {
        el('hakka-status').textContent = ready ? '本機客語模型已就緒，可先試聽「天公落水」。' : '客語環境尚未安裝，請參考 README。';
        initialized = true;
      }
    }
  };
  el('hakka-stop').onclick = () => {stop(); el('hakka-status').textContent='已停止客語播放。';};
  for(const id of ['hakka-text','hakka-dialect'])el(id).addEventListener('input',()=>{
    invalidate();el('hakka-status').textContent='文字或腔調已變更，請重新核對並產生音檔。';
  });
  el('hakka-confirm').addEventListener('change',()=>{if(!el('hakka-confirm').checked)invalidate();});
  el('hakka-btn').onclick = async () => {
    stopSpeech();
    const source=el('hakka-source').value.trim(),documentMode=el('hakka-source-kind').value==='document';
    if(source&&!el('hakka-confirm').checked){el('hakka-status').textContent='請先核對客語草稿、原文及數字讀法，再勾選確認。';return;}
    if(source&&documentMode&&!state.job){el('hakka-status').textContent='請先重新讀取文件。';return;}
    const request = new AbortController(); controller = request;
    el('hakka-btn').disabled = true;
    el('hakka-audio').hidden = true;
    el('hakka-status').textContent = '正在本機產生客語語音，首次啟動需要較久…';
    try {
      const response = await api(source?'/api/hakka-draft-speech':'/api/hakka-speech', {
        method:'POST', headers:{'Content-Type':'application/json'}, signal:request.signal,
        body:JSON.stringify({text:el('hakka-text').value.trim(), dialect:el('hakka-dialect').value,
          ...(source?{source,job_id:documentMode?state.job:null,confirmed:el('hakka-confirm').checked}:{})})
      });
      const blob = await response.blob();
      if (controller !== request) return;
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      audioUrl = URL.createObjectURL(blob);
      el('hakka-audio').src = audioUrl; el('hakka-audio').hidden = false;
      el('hakka-status').textContent = '客語音檔已產生，請核對發音；可按播放器重播。';
      try {await el('hakka-audio').play();} catch {}
    } catch(error) {
      if (error.name !== 'AbortError' && controller === request) el('hakka-status').textContent = error.message;
    } finally {
      if (controller === request) {controller = null; el('hakka-btn').disabled = !ready;}
    }
  };
  window.addEventListener('pagehide', () => {stop(); if(audioUrl) URL.revokeObjectURL(audioUrl);});
})();
