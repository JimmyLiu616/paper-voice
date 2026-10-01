const test = require('node:test');
const assert = require('node:assert/strict');
const speech = require('../static/answer-speech.js');

test('short deadline answer is followed by complete verbatim date evidence', () => {
  const answer = {found:true, answer:'下午5時前', evidence:'補件期限：民國115年10月20日下午5時前。'};
  assert.equal(speech.build(answer), `回答：\n${answer.answer}\n\n以下是辨識原文的引用，請一起核對：\n${answer.evidence}`);
});
test('English PM and negated exceptions remain unchanged in the citation', () => {
  const evidence = 'Renewal deadline: October 28, 2026 at 4 PM\n已完成更新者不必再次辦理。';
  assert.ok(speech.build({found:true, answer:'4點以前。', evidence}).endsWith(evidence));
});
test('explicit answer-only selection excludes the evidence', () => {
  assert.equal(speech.build({found:true, answer:'下午5時前', evidence:'完整期限'}, false), '下午5時前');
});
test('refusals never read stale or unsupported evidence', () => {
  for (const found of [false, undefined, 'true']) {
    const answer = {found, answer:'文件沒有提供這項資訊。', evidence:'無關段落'};
    assert.equal(speech.hasEvidence(answer), false);
    assert.equal(speech.build(answer), answer.answer);
  }
});
test('missing or blank evidence still allows the answer to be read', () => {
  for (const evidence of [undefined, null, '', ' \n ', 123]) {
    assert.equal(speech.build({found:true, answer:'請核對原圖。', evidence}), '請核對原圖。');
  }
});
test('combined speech exceeding the API limit is refused rather than truncated', () => {
  const answer = {found:true, answer:'答'.repeat(1790), evidence:'期限115年10月20日'};
  assert.throws(() => speech.build(answer), /1800/);
  assert.equal(speech.build(answer, false), answer.answer);
});
test('exact limit uses Unicode code points, matching the Python API', () => {
  assert.equal(speech.build({answer:'𠮷'.repeat(1800)}), '𠮷'.repeat(1800));
  assert.throws(() => speech.build({answer:'字'.repeat(1801)}), /1800/);
});
test('empty answers cannot trigger speech', () => {
  for (const answer of [undefined, {}, {answer:''}, {answer:' \n '}, {answer:123}]) {
    assert.throws(() => speech.build(answer), /沒有可朗讀/);
  }
});
