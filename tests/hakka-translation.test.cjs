const {test}=require('node:test');
const assert=require('node:assert/strict');
const {create}=require('../static/hakka-translation.js');
for(const changed of ['source','job','dialect','kind','text']){
  test(`Hakka draft cannot replace changed ${changed}`,async()=>{
    let data={source:'免費',job:'one',dialect:'sixian',kind:'document',text:''},finish;
    const applied=[],statuses=[];
    const run=create({snapshot:()=>({...data}),request:()=>new Promise(r=>finish=r),apply:r=>applied.push(r),status:s=>statuses.push(s)});
    const pending=run();data[changed]='changed';finish({translation:'免費'});await pending;
    assert.equal(applied.length,0);assert.equal(statuses.at(-1),'stale');
  });
}
test('unsupported input reports failure and can be retried',async()=>{
  let bad=true;const statuses=[],applied=[];
  const run=create({snapshot:()=>({source:'免費'}),request:async()=>{if(bad)throw Error('unsupported');return {translation:'免費'};},apply:r=>applied.push(r),status:s=>statuses.push(s)});
  await run();assert.equal(statuses.at(-1),'error');bad=false;await run();assert.equal(applied.length,1);
});
