const {test} = require('node:test');
const assert = require('node:assert/strict');
const {create} = require('../static/taigi-pronunciation.js');

for (const changed of ['text','source','poj','job']) {
  test(`new ${changed} prevents a late pronunciation draft overwriting current work`, async () => {
    let input = {text:'你好',source:'',poj:'',job:null}, finish;
    const applied = [], statuses = [];
    const convert = create({snapshot:()=>({...input}),request:()=>new Promise(r=>{finish=r;}),
      apply:x=>applied.push(x),status:x=>statuses.push(x)});
    const pending = convert(); input[changed]='changed'; finish({poj:'lí hó'}); await pending;
    assert.equal(applied.length,0); assert.equal(statuses.at(-1),'stale');
  });
}
test('a matching draft is applied; request failure remains retryable',async()=>{
  let fail=true;const applied=[],statuses=[];
  const convert=create({snapshot:()=>({text:'你好'}),request:async()=>{if(fail)throw Error('offline');return {poj:'lí hó'};},
    apply:x=>applied.push(x),status:x=>statuses.push(x)});
  await convert(); assert.equal(statuses.at(-1),'error');
  fail=false;await convert();assert.deepEqual(applied,[{poj:'lí hó'}]);assert.equal(statuses.at(-1),'ready');
});
