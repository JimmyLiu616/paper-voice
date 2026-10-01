'use strict';
// Separate from document state: a cancelled photo never replaces the current document.
(() => {
  const el = id => document.getElementById(id);
  const dialog = el('camera-dialog'), video = el('camera-video');
  let stream = null, photo = null, photoURL = null, generation = 0, opening = false;
  const say = text => { el('camera-status').textContent = text; };
  function release() {
    if(stream)stream.getTracks().forEach(track => track.stop());
    stream = null; video.srcObject = null; video.hidden = true;
    el('camera-placeholder').hidden = false; el('camera-shutter').disabled = true;
  }
  function clearPhoto() {
    photo = null;
    if(photoURL)URL.revokeObjectURL(photoURL);
    photoURL = null; el('camera-photo').removeAttribute('src');
    el('camera-photo').hidden = true; video.hidden = true; el('camera-placeholder').hidden = false;
    el('camera-retake').hidden = true; el('camera-use').hidden = true;
  }
  function stop() {
    generation++; opening = false; release(); clearPhoto();
    el('camera-select').disabled = true; el('camera-start').disabled = false;
    el('camera-start').hidden = false; el('camera-shutter').hidden = false;
  }
  function close() { stop(); if(dialog.open)dialog.close(); }
  function cameraError(error) {
    const messages = {
      NotAllowedError:'攝影機權限未允許。請在瀏覽器網站權限中允許攝影機，再按「啟動預覽」。',
      NotFoundError:'找不到攝影機，請連接攝影機或改用上傳圖片。',
      NotReadableError:'攝影機可能被其他程式占用，請關閉視訊軟體後重試。',
      OverconstrainedError:'這個攝影機不支援所選設定，請選擇其他攝影機後重試。',
      SecurityError:'瀏覽器禁止此頁使用攝影機，請使用本機 localhost 網址或 HTTPS。'
    };
    return messages[error?.name] || '無法開啟攝影機，請檢查連線與瀏覽器權限，或改用上傳圖片。';
  }
  async function start(deviceId) {
    if(opening || !dialog.open)return;
    release(); clearPhoto();
    const run = ++generation; opening = true;
    el('camera-start').disabled = true; el('camera-select').disabled = true;
    el('camera-shutter').hidden = false;
    say('正在開啟攝影機；如果瀏覽器詢問，請允許相機權限。');
    try {
      if(!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        throw {name:'SecurityError'};
      }
      const acquired = await navigator.mediaDevices.getUserMedia({audio:false,video:{
        width:{ideal:1920},height:{ideal:1080},
        ...(deviceId ? {deviceId:{exact:deviceId}} : {facingMode:{ideal:'environment'}})
      }});
      // Permission prompts may resolve after the user closed the dialog.
      if(run !== generation || !dialog.open) { acquired.getTracks().forEach(t=>t.stop()); return; }
      stream = acquired; video.srcObject = acquired; video.hidden = false; el('camera-placeholder').hidden = true;
      await video.play();
      if(run !== generation || !dialog.open)return;
      el('camera-start').hidden = true;
      el('camera-shutter').disabled = !(video.videoWidth && video.videoHeight);
      say('預覽已開啟。請讓文字對焦清楚，再按「拍照」。');
      for(const track of stream.getVideoTracks())track.onended = () => {
        if(run !== generation || !dialog.open || photo)return;
        release(); el('camera-start').hidden = false;
        say('攝影機連線已中斷，請重新啟動預覽。');
      };
      try {
        const devices = (await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='videoinput');
        if(run !== generation || !stream)return;
        const selected = stream.getVideoTracks()[0]?.getSettings().deviceId;
        el('camera-select').replaceChildren();
        devices.forEach((device,index)=>{
          const option = document.createElement('option'); option.value=device.deviceId;
          option.textContent=device.label || `攝影機 ${index+1}`; el('camera-select').append(option);
        });
        if(selected)el('camera-select').value=selected;
        el('camera-select').disabled=devices.length<2;
      }catch { /* Device enumeration is optional; the acquired camera still works. */ }
    }catch(error) {
      if(run === generation && dialog.open) {
        release(); say(cameraError(error)); el('camera-start').hidden = false;
        el('camera-select').disabled = el('camera-select').options.length < 2;
      }
    }finally {
      if(run === generation) { opening = false; el('camera-start').disabled = false; }
    }
  }
  video.addEventListener('loadeddata',()=>{
    if(stream && dialog.open && !photo)el('camera-shutter').disabled=!(video.videoWidth && video.videoHeight);
  });
  el('camera-open').onclick = () => {
    stop(); dialog.showModal();
    say('按「啟動預覽」，並允許瀏覽器使用攝影機。');
    el('camera-start').focus();
  };
  el('camera-start').onclick = () => start();
  el('camera-select').onchange = () => start(el('camera-select').value);
  el('camera-close').onclick = close;
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
  dialog.addEventListener('close',()=>{if(!dialog.open)stop();});
  el('camera-retake').onclick = () => start(el('camera-select').value || undefined);
  el('camera-shutter').onclick = async () => {
    if(!stream || !video.videoWidth || !video.videoHeight)return;
    const run = generation;
    el('camera-shutter').disabled=true; el('camera-select').disabled=true;
    try {
      const canvas=document.createElement('canvas');
      const scale=Math.min(1,2400/Math.max(video.videoWidth,video.videoHeight));
      canvas.width=Math.round(video.videoWidth*scale); canvas.height=Math.round(video.videoHeight*scale);
      canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
      release(); // Still image captured; no reason to keep the camera running.
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.94));
      if(run !== generation || !dialog.open)return;
      if(!blob || blob.size>12*1024*1024)throw new Error('capture failed');
      photo=new File([blob],'攝影機文件.jpg',{type:'image/jpeg'});
      photoURL=URL.createObjectURL(blob); el('camera-photo').src=photoURL;
      video.hidden=true; el('camera-photo').hidden=false; el('camera-placeholder').hidden=true;
      el('camera-shutter').hidden=true; el('camera-retake').hidden=false; el('camera-use').hidden=false;
      say('已拍照並關閉攝影機。請確認文字清楚；不清楚可以重拍。');
    }catch {
      if(run !== generation)return;
      release(); el('camera-start').hidden=false;
      say('無法擷取照片，請重新啟動預覽後重拍。');
    }
  };
  el('camera-use').onclick = () => {
    if(!photo)return;
    const file=photo; close(); chooseFile(file);
    if(modelReady)analyze();
    else message('照片已放入，模型就緒後請按「幫我讀懂」。');
  };
  window.addEventListener('pagehide',close);
  document.addEventListener('visibilitychange',()=>{if(document.hidden && dialog.open)close();});
})();
