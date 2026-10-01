(function(root) {
  'use strict';
  const MAX_LENGTH = 1800;
  function hasEvidence(answer) {
    return answer?.found === true && typeof answer.evidence === 'string' && !!answer.evidence.trim();
  }
  function build(answer, includeEvidence = true) {
    if (typeof answer?.answer !== 'string' || !answer.answer.trim()) {
      throw new Error('沒有可朗讀的回答，請重新提問。');
    }
    const withEvidence = includeEvidence && hasEvidence(answer);
    const text = withEvidence
      ? `回答：\n${answer.answer}\n\n以下是辨識原文的引用，請一起核對：\n${answer.evidence}`
      : answer.answer;
    if (Array.from(text).length > MAX_LENGTH) {
      throw new Error('回答與所選依據超過單次朗讀 1800 字上限，未播放或截斷。請縮小問題範圍後再試。');
    }
    return text;
  }
  const api = {build, hasEvidence, MAX_LENGTH};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PaperVoiceAnswerSpeech = api;
})(globalThis);
