(async function () {
  'use strict';
  const R = window.PaperVoiceReview;
  const $ = id => document.getElementById(id);
  const titles = {deadline:'期限',required_documents:'應備文件',amount:'費用／金額',conditions:'例外條件'};
  let rows = [], current = 0, storageKey = '', storageWarning = false;
  const status = message => { $('status').textContent = message; };
  const currentRow = () => rows[current];
  function clearExport(){ $('export-preview').hidden=true;$('export-text').value=''; }
  function save() {
    try { localStorage.setItem(storageKey, JSON.stringify({reviewer:$('reviewer').value,rows})); }
    catch { storageWarning = true; status('瀏覽器無法暫存，請用「匯出全部草稿」保存修改。'); }
  }
  function progress() {
    const count = rows.filter(R.approved).length;
    $('progress').textContent = `已確認 ${count} / ${rows.length} 份`;
    $('export-reviewed').disabled = !count;
    $('export-draft').disabled = !rows.length;
    $('next-document').disabled = current === rows.length-1;
    $('document-status').textContent = R.approved(currentRow()) ? `已由 ${currentRow().review.reviewer} 確認這份標註。` : '這份資料尚未確認，不會匯出為已確認資料。';
    [...$('documents').children].forEach((button, index) => {
      button.setAttribute('aria-current',String(index === current));
      button.lastChild.textContent = `${rows[index].split === 'train' ? '訓練草稿' : '開發草稿'} · ${R.approved(rows[index]) ? '已確認' : '待核對'}`;
    });
  }
  function problems() {
    const messages = R.errors(currentRow());
    $('problems').replaceChildren(...messages.map(message => { const li=document.createElement('li');li.textContent=message;return li; }));
    $('confirm-document').disabled = messages.length > 0 || !$('reviewer').value.trim() || !$('content-confirmed').checked || !$('rights-confirmed').checked;
  }
  function changed() {
    clearExport();
    const wasApproved = currentRow().human_reviewed;
    R.invalidate(currentRow());
    $('content-confirmed').checked = false;
    $('rights-confirmed').checked = false;
    save(); progress(); problems();
    if (wasApproved && !storageWarning) status('這份標註已修改，原確認已失效。請重新核對。');
  }
  function control(label, value, update, lines = 2) {
    const wrapper = document.createElement('label');wrapper.textContent=label;
    const input = document.createElement('textarea');input.rows=lines;input.value=value;
    input.addEventListener('input', () => {update(input.value);changed();});
    wrapper.append(input);return wrapper;
  }
  function render() {
    const row=currentRow();
    $('editor').hidden=false;
    $('title').textContent=row.title;
    $('source-id').textContent=`文件代號：${row.source_id}`;
    $('split').textContent=`${row.split === 'train' ? '訓練' : '開發'}草稿 · 虛構原創 · 尚無最終測試集`;
    $('original').textContent=row.document;
    $('fields').replaceChildren(...R.fields.map(name => control(titles[name],row.fields[name],value=>{row.fields[name]=value;})));
    $('questions').replaceChildren(...row.questions.map((q,index)=>{
      const section=document.createElement('section');section.className='question';
      section.append(control(`第 ${index+1} 題 · 問題`,q.question,value=>{q.question=value;}));
      section.append(control('答案（可用繁體中文解釋）',q.answer,value=>{q.answer=value;}));
      const check=document.createElement('label');check.className='check';
      const found=document.createElement('input');found.type='checkbox';found.checked=q.found;
      check.append(found,document.createTextNode('文件有明確答案（未勾選代表無法從文件回答）'));
      const evidence=control('原文依據（單一連續片段）',q.evidence.join('\n'),value=>{q.evidence=value.trim() ? [value] : [];},3);
      evidence.lastChild.disabled=!q.found;
      found.addEventListener('change',()=>{
        q.found=found.checked;
        if(!q.found){q.evidence=[];evidence.lastChild.value='';}
        evidence.lastChild.disabled=!q.found;changed();
      });
      section.append(check,evidence);return section;
    }));
    $('notes').value=row.review_notes || '';
    $('content-confirmed').checked=R.approved(row);
    $('rights-confirmed').checked=R.approved(row);
    progress();problems();
  }
  function download(reviewedOnly) {
    try {
      const text=R.serialize(rows,reviewedOnly);
      $('export-text').value=text;$('export-preview').hidden=false;$('export-preview').open=true;
      const url=URL.createObjectURL(new Blob([text],{type:'application/x-ndjson;charset=utf-8'}));
      const a=document.createElement('a');a.href=url;
      a.download=reviewedOnly?'paper-voice-reviewed.jsonl':'paper-voice-drafts.jsonl';
      document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
      status(reviewedOnly?'已產生已確認資料並嘗試下載；下方也可複製。尚未開始訓練。':'已產生全部草稿並嘗試下載；下方也可複製。未確認資料仍標為未審核，不能直接訓練。');
      $('export-preview').scrollIntoView({block:'start'});
    } catch(error){status(error.message);}
  }
  try {
    const response=await fetch('/static/training-review-drafts.json');
    if(!response.ok) throw new Error('無法載入草稿，請確認本機服務正常。');
    const source=await response.text();const dataset=JSON.parse(source);
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(source))),b=>b.toString(16).padStart(2,'0')).join('');
    storageKey='paper-voice-review:'+hash;
    rows=R.clone(dataset.rows);
    try {
      const saved=JSON.parse(localStorage.getItem(storageKey) || 'null');
      if(saved && Array.isArray(saved.rows) && saved.rows.length===rows.length){
        rows=rows.map((original,i)=>{
          const value=saved.rows[i];
          if(value?.source_id!==original.source_id || value.schema!==original.schema || value.document!==original.document || value.split!==original.split || value.license!==original.license || value.family!==original.family || !value.fields || !Array.isArray(value.questions))return original;
          if(!R.approved(value)) R.invalidate(value);
          return value;
        });
        $('reviewer').value=typeof saved.reviewer==='string' ? saved.reviewer : '';
      }
    } catch {status('無法讀取先前暫存，已載入原始草稿。');}
    $('documents').replaceChildren(...rows.map((row,index)=>{
      const button=document.createElement('button');button.type='button';
      const name=document.createElement('span');name.textContent=`${index+1}. ${row.title}`;
      const badge=document.createElement('small');button.append(name,badge);
      button.addEventListener('click',()=>{current=index;render();$('editor').scrollIntoView({block:'start'});});return button;
    }));
    $('reviewer').addEventListener('input',()=>{
      // Earlier records retain their own reviewer; this name applies to the next explicit confirmation.
      save();problems();
    });
    $('notes').addEventListener('input',()=>{currentRow().review_notes=$('notes').value;changed();});
    ['content-confirmed','rights-confirmed'].forEach(id=>$(id).addEventListener('change',()=>{
      if(currentRow().human_reviewed && !$(id).checked){R.invalidate(currentRow());clearExport();save();progress();}
      problems();
    }));
    $('confirm-document').addEventListener('click',()=>{
      try {
        rows[current]=R.confirm(currentRow(),$('reviewer').value,{content:$('content-confirmed').checked,rights:$('rights-confirmed').checked});
        clearExport();
        save();render();if(!storageWarning)status('這份標註已記錄你的確認。修改任何標註後，須重新確認。');
      }catch(error){status(error.message);}
    });
    $('export-reviewed').addEventListener('click',()=>download(true));
    $('export-draft').addEventListener('click',()=>download(false));
    $('copy-export').addEventListener('click',async()=>{
      try {await navigator.clipboard.writeText($('export-text').value);status('已複製匯出內容，可貼到 UTF-8 的 .jsonl 檔案。');}
      catch {$('export-text').focus();$('export-text').select();status('瀏覽器未允許自動複製。內容已選取，請按 Ctrl+C 複製。');}
    });
    $('next-document').addEventListener('click',()=>{if(current<rows.length-1){current++;render();$('editor').scrollIntoView({block:'start'});}});
    render();status('草稿已載入。程式只檢查格式與引文是否存在；請自行核對答案語意。');
  } catch(error){status(error.message);}
})();
