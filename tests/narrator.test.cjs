const {test}=require('node:test');const assert=require('node:assert/strict');
const {create}=require('../static/narrator.js');
const {narrationInput}=require('../static/narrator.js');
function setup(request){const applied=[],errors=[];const flow=create({request,apply:r=>applied.push(r),fail:e=>errors.push(e.message),busy:()=>{},halt:()=>{}});return {flow,applied,errors};}
test('language switch / stop cancels late audio and changes Q&A epoch',async()=>{
  let finish;const s=setup(()=>new Promise(r=>finish=r));const p=s.flow.run({language:'nan'});const epoch=s.flow.epoch;s.flow.stop();finish({audio:'old'});await p;assert.deepEqual(s.applied,[]);assert.notEqual(s.flow.epoch,epoch);
});
test('latest selected language wins even if earlier request fails late',async()=>{
  let reject,calls=0;const s=setup(b=>++calls===1?new Promise((_,r)=>reject=r):Promise.resolve(b));
  const old=s.flow.run({language:'nan'});await s.flow.run({language:'ami'});reject(Error('old'));await old;assert.deepEqual(s.applied,[{language:'ami'}]);assert.deepEqual(s.errors,[]);
});
test('automatic narration sends supplied answer unchanged with selected dialect',async()=>{
  let body;const s=setup(async b=>{body=b;return {translation:'draft',audio:'wav'};});
  await s.flow.run({text:'免費，惟材料費另收。',language:'hakka',dialect:'hailu'});assert.equal(body.text,'免費，惟材料費另收。');assert.equal(body.dialect,'hailu');assert.equal(s.applied.length,1);
});
test('Hakka explanation retains complete evidence instead of a shortened answer',()=>{
  const context={found:true,evidence:'只有65歲以上才免費，其他人須繳500元。'};
  assert.deepEqual(narrationInput('免費。','hakka',context),{text:context.evidence,basis:'evidence'});
  assert.deepEqual(narrationInput('免費。','zh-TW',context),{text:'免費。',basis:'answer'});
  assert.deepEqual(narrationInput('沒有答案。','hakka',{found:false,evidence:'舊引文'}),{text:'沒有答案。',basis:'answer'});
  assert.deepEqual(narrationInput('500元。','hakka',{found:true,evidence:'其他人須繳500元',narration_evidence:context.evidence}),{text:context.evidence,basis:'evidence'});
  assert.deepEqual(narrationInput('500元。','hakka',{found:true,evidence:'其他人須繳500元',narration_evidence:''}),{text:'500元。',basis:'unresolved'});
});
