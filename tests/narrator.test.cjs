const {test}=require('node:test');const assert=require('node:assert/strict');
const {create}=require('../static/narrator.js');
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
