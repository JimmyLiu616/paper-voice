const {test}=require('node:test');
const assert=require('node:assert/strict');
const {create}=require('../static/amis-speech.js');
function setup(request){const applied=[],errors=[],busy=[];const flow=create({request,apply:r=>applied.push(r),fail:e=>errors.push(e.message),busy:b=>busy.push(b),halt:()=>{}});return {flow,applied,errors,busy};}
test('one request automatically applies translation and audio without confirmation',async()=>{
  let sent;const s=setup(async b=>{sent=b;return {translation:'ngaʼay ho.',audio_base64:'wave'};});
  await s.flow.run({source:'你好。',dialect:'ami_Xiug'});
  assert.equal('confirmed' in sent,false);assert.equal(s.applied[0].audio_base64,'wave');assert.equal(s.busy.at(-1),false);
});
test('stop discards a late successful translation and audio',async()=>{
  let finish;const s=setup(()=>new Promise(r=>finish=r));const pending=s.flow.run({});s.flow.stop();finish({audio_base64:'old'});await pending;assert.deepEqual(s.applied,[]);
});
test('replaced request cannot overwrite newer audio or report an old failure',async()=>{
  let reject;let calls=0;const s=setup(()=>++calls===1?new Promise((_,r)=>reject=r):Promise.resolve({translation:'new'}));
  const first=s.flow.run({});await s.flow.run({});reject(Error('old'));await first;assert.deepEqual(s.applied,[{translation:'new'}]);assert.deepEqual(s.errors,[]);
});
