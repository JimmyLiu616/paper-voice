'use strict';
(() => {
  const el = id => document.getElementById(id);
  let ready = false, initialized = false, controller = null, audioUrl = null;
  const stop = () => {
    controller?.abort(); controller = null;
    el('hakka-audio').pause();
    el('hakka-btn').disabled = !ready;
  };
  window.PaperVoiceHakka = {
    stop,
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
  el('hakka-btn').onclick = async () => {
    stopSpeech();
    const request = new AbortController(); controller = request;
    el('hakka-btn').disabled = true;
    el('hakka-audio').hidden = true;
    el('hakka-status').textContent = '正在本機產生客語語音，首次啟動需要較久…';
    try {
      const response = await api('/api/hakka-speech', {
        method:'POST', headers:{'Content-Type':'application/json'}, signal:request.signal,
        body:JSON.stringify({text:el('hakka-text').value.trim(), dialect:el('hakka-dialect').value})
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
