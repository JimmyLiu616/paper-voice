const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const R=require('../static/review-data.js');

function fixture(){return {schema:'paper-voice-understanding-v1',source_id:'test-only',family:'test-only',split:'train',
  license:'MIT',human_reviewed:false,rights_confirmed:false,document:'費用：免費。期限：未提供。',
  fields:{deadline:'',required_documents:'',amount:'免費。',conditions:''},
  questions:[{question:'收費嗎？',answer:'免費。',found:true,evidence:['費用：免費。']}]};}
const confirm=row=>R.confirm(row,'TEST_AUTOMATION_NOT_A_PERSON',{content:true,rights:true},'2026-10-01T00:00:00Z');

test('unreviewed and forged flags cannot enter reviewed-only export',()=>{
  const row=fixture();assert.throws(()=>R.serialize([row],true));
  row.human_reviewed=true;row.rights_confirmed=true;
  assert.throws(()=>R.serialize([row],true));
  const exported=JSON.parse(R.serialize([row],false));
  assert.equal(exported.human_reviewed,false);assert.equal(exported.rights_confirmed,false);
});
test('name and two separate declarations are required',()=>{
  assert.throws(()=>R.confirm(fixture(),' ',{content:true,rights:true}));
  assert.throws(()=>R.confirm(fixture(),'TEST',{content:true,rights:false}));
  assert.throws(()=>R.confirm(fixture(),'TEST',{content:false,rights:true}));
});
test('editing a confirmed answer invalidates eligibility even without a UI event',()=>{
  const row=confirm(fixture());assert.equal(R.approved(row),true);
  row.questions[0].answer='要收100元。';assert.equal(R.approved(row),false);
  assert.throws(()=>R.serialize([row],true));
  assert.equal(JSON.parse(R.serialize([row],false)).human_reviewed,false);
});
test('invented quotes and contradictory found/evidence are rejected',()=>{
  const row=fixture();row.questions[0].evidence=['費用：100元。'];assert.ok(R.errors(row).length);
  assert.throws(()=>confirm(row));row.questions[0].evidence=['費用：免費。'];row.questions[0].found=false;
  assert.ok(R.errors(row).length);assert.throws(()=>confirm(row));
});
test('only confirmed rows export; declaration metadata survives without internal snapshot',()=>{
  const reviewed=confirm(fixture());const draft=fixture();draft.source_id='another-test';
  const rows=R.serialize([reviewed,draft],true).trim().split('\n').map(JSON.parse);
  assert.equal(rows.length,1);assert.equal(rows[0].human_reviewed,true);
  assert.equal(rows[0].review.reviewer,'TEST_AUTOMATION_NOT_A_PERSON');
  assert.equal(rows[0].review_snapshot,undefined);
});
test('changing source, split or field after confirmation also invalidates it',()=>{
  for(const change of [r=>{r.document+='變更';},r=>{r.split='dev';},r=>{r.fields.amount='';}]){
    const row=confirm(fixture());change(row);assert.equal(R.approved(row),false);
  }
});
test('shipped candidates stay unreviewed, with grounded spans and no test split',()=>{
  const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../static/training-review-drafts.json'),'utf8'));
  assert.equal(data.rows.length,12);
  assert.equal(data.rows.filter(r=>r.split==='train').length,8);
  assert.equal(data.rows.filter(r=>r.split==='dev').length,4);
  assert.equal(data.rows.filter(r=>r.split==='test').length,0);
  assert.equal(data.rows.reduce((n,r)=>n+r.questions.length,0),36);
  for(const row of data.rows){assert.deepEqual(R.errors(row),[]);assert.equal(row.human_reviewed,false);assert.equal(row.rights_confirmed,false);}
});

test('contrast batch is separately exportable but cannot export as reviewed',()=>{
  const data=JSON.parse(fs.readFileSync(path.join(__dirname,'../static/training-review-contrast.json'),'utf8'));
  assert.equal(data.rows.length,6);
  for(const row of data.rows){assert.deepEqual(R.errors(row),[]);assert.equal(row.split,'train');assert.equal(R.approved(row),false);}
  assert.throws(()=>R.serialize(data.rows,true));
  const exported=R.serialize(data.rows,false).trim().split('\n').map(JSON.parse);
  assert.equal(exported.length,6);
  assert.ok(exported.every(row=>!row.human_reviewed && !row.rights_confirmed));
});
