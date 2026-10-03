'use strict';
(function(root){
  function narration(result,target='summary'){
    return target==='raw'?result.raw_text:result.narration_text||'';
  }
  function exportText(result){
    const lines=[result.title,'',result.review_notice||'AI 輔助整理，請對照原文。',''];
    for(const p of result.highlights||[]){
      lines.push(p.heading,p.text,`原文依據（第 ${p.source_start}–${p.source_end} 行）：`,p.evidence,'');
    }
    lines.push('朗讀稿',result.narration_text||'','提醒',...(result.warnings||[]),'','完整辨識原文',result.raw_text);
    return lines.join('\n');
  }
  const api={narration,exportText};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.PaperVoiceDocument=api;
})(typeof window==='object'?window:globalThis);
