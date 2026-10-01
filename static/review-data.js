/* Pure review/export rules. A checked UI records a user's declaration, not identity proof. */
(function (root) {
  'use strict';
  const fields = ['deadline', 'required_documents', 'amount', 'conditions'];
  const clone = value => JSON.parse(JSON.stringify(value));
  const normalize = text => text.normalize('NFKC').replace(/\s+/gu, '');
  function errors(row) {
    const out = [];
    if (!row || typeof row.document !== 'string' || !row.document.trim()) return ['通知原文不可空白。'];
    if (!row.fields || Object.keys(row.fields).sort().join() !== [...fields].sort().join()) return ['需要完整的四個欄位。'];
    for (const name of fields) {
      const value = row.fields[name];
      if (typeof value !== 'string' || (value && (!normalize(value) || !normalize(row.document).includes(normalize(value))))) {
        out.push(`${name} 必須留空或使用原文的連續片段。`);
      }
    }
    if (!Array.isArray(row.questions) || !row.questions.length) return [...out, '至少需要一題問答。'];
    row.questions.forEach((q, i) => {
      const label = `第 ${i + 1} 題`;
      if (typeof q.question !== 'string' || !q.question.trim() || typeof q.answer !== 'string' || !q.answer.trim()) out.push(`${label}的問題及答案不可空白。`);
      if (typeof q.found !== 'boolean' || !Array.isArray(q.evidence)) { out.push(`${label}的依據格式不正確。`); return; }
      if (q.found !== Boolean(q.evidence.length)) out.push(`${label}：有明確答案須附引文；無答案須清空引文。`);
      if (q.evidence.some(e => typeof e !== 'string' || !normalize(e) || !normalize(row.document).includes(normalize(e)))) out.push(`${label}的引文不在原文中。`);
    });
    return out;
  }
  function snapshot(row) {
    return JSON.stringify([row.schema, row.source_id, row.family, row.split, row.license, row.document, row.fields, row.questions]);
  }
  function invalidate(row) {
    row.human_reviewed = false;
    row.rights_confirmed = false;
    delete row.review;
    delete row.review_snapshot;
    return row;
  }
  function confirm(row, reviewer, consent, now = new Date().toISOString()) {
    if (!reviewer.trim()) throw new Error('請填寫核對者姓名或代號。');
    if (!consent.content || !consent.rights) throw new Error('請逐份確認內容與使用授權。');
    const problems = errors(row);
    if (problems.length) throw new Error(problems.join('\n'));
    const result = clone(row);
    result.human_reviewed = true;
    result.rights_confirmed = true;
    result.review = {reviewer: reviewer.trim(), reviewed_at: now, method: 'explicit-per-document-confirmation'};
    result.review_snapshot = snapshot(result);
    return result;
  }
  function approved(row) {
    return row.human_reviewed === true && row.rights_confirmed === true &&
      Boolean(row.review?.reviewer?.trim() && row.review?.reviewed_at) &&
      row.review_snapshot === snapshot(row) && errors(row).length === 0;
  }
  function serialize(rows, reviewedOnly) {
    const chosen = reviewedOnly ? rows.filter(approved) : rows;
    if (!chosen.length) throw new Error('還沒有可匯出的已確認資料。');
    return chosen.map(row => {
      const value = clone(row);
      if (!approved(value)) invalidate(value);
      delete value.review_snapshot;
      return JSON.stringify(value);
    }).join('\n') + '\n';
  }
  const api = {fields, clone, normalize, errors, snapshot, invalidate, confirm, approved, serialize};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PaperVoiceReview = api;
})(globalThis);
