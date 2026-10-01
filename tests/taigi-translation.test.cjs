const {test}=require('node:test');
const assert=require('node:assert/strict');
const {create}=require('../static/taigi-translation.js');
for(const changed of ['source','job','hanji','poj']){
  test(`late translation cannot replace edited ${changed}`,async()=>{
    let data={source:'115年',job:'one',hanji:'',poj:''},finish;
    const applied=[],statuses=[];
    const translate=create({snapshot:()=>({...data}),request:()=>new Promise(r=>finish=r),apply:r=>applied.push(r),status:s=>statuses.push(s)});
    const pending=translate();data[changed]='changed';finish({translation:'115年'});await pending;
    assert.equal(applied.length,0);assert.equal(statuses.at(-1),'stale');
  });
}
test('failed translation remains retryable',async()=>{
  let fail=true;const applied=[],statuses=[];
  const translate=create({snapshot:()=>({source:'你好'}),request:async()=>{if(fail)throw Error('offline');return {translation:'你好'};},apply:r=>applied.push(r),status:s=>statuses.push(s)});
  await translate();assert.equal(statuses.at(-1),'error');fail=false;await translate();assert.deepEqual(applied,[{translation:'你好'}]);
});
