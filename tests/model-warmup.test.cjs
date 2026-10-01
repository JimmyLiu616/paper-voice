const test = require('node:test');
const assert = require('node:assert/strict');
const {create} = require('../static/model-warmup.js');

test('simultaneous page/file preparation shares one request and recent success is reused', async () => {
  let resolve, calls = 0, clock = 0;
  const states = [];
  const warmup = create({request: () => {calls++;return new Promise(r => {resolve=r;});},
    onState:s=>states.push(s), now:()=>clock});
  const first=warmup.prepare(), second=warmup.prepare();
  assert.equal(first,second);
  await Promise.resolve();
  resolve({status:'ready'}); await first;
  assert.equal((await warmup.prepare()).status,'ready');
  assert.equal(calls,1); assert.deepEqual(states,['preparing','ready']);
  clock=60001;
  const later=warmup.prepare(); await Promise.resolve(); resolve({status:'ready'}); await later;
  assert.equal(calls,2);
});

test('preparation failure remains retryable and does not reject the upload caller', async () => {
  let calls=0; const states=[];
  const warmup=create({request:async()=>{if(++calls===1)throw Error('offline');return {status:'ready'};},onState:s=>states.push(s)});
  assert.equal((await warmup.prepare()).status,'unavailable');
  assert.equal((await warmup.prepare()).status,'ready');
  assert.deepEqual(states,['preparing','unavailable','preparing','ready']);
});

test('busy response is not mistaken for a successfully loaded model', async () => {
  let calls=0;
  const warmup=create({request:async()=>({status:++calls===1?'busy':'ready'}),onState:()=>{}});
  assert.equal((await warmup.prepare()).status,'busy');
  assert.equal((await warmup.prepare()).status,'ready');
  assert.equal(calls,2);
});
