const {test}=require('node:test');const assert=require('node:assert/strict');
const {narration,exportText}=require('../static/document-result.js');
test('export and narration use the displayed highlights without fixed field names',()=>{
  const r={title:'算力通知',review_notice:'AI 草稿',highlights:[{heading:'可用額度',text:'每隊最高100點。',source_start:2,source_end:3,evidence:'每隊最高100點。\n實際核發另定。'}],narration_text:'每隊最高100點。',raw_text:'完整原文',warnings:['核對原圖']};
  assert.equal(narration(r),'每隊最高100點。');assert.equal(narration(r,'raw'),'完整原文');
  const txt=exportText(r);for(const s of ['可用額度','100點','實際核發另定','核對原圖','完整原文','第 2–3 行'])assert.ok(txt.includes(s));
  assert.ok(!txt.includes('金額／費用'));
});
