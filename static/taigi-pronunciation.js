'use strict';
// A pronunciation draft must never approve a translation or overwrite newer edits.
(function(root) {
  function create({snapshot, request, apply, status}) {
    let sequence = 0;
    return async function convert() {
      const current = ++sequence, before = snapshot();
      status('working');
      try {
        const result = await request(before.text);
        if (current !== sequence) return;
        if (JSON.stringify(snapshot()) !== JSON.stringify(before)) {status('stale'); return;}
        apply(result); status('ready', result.warning);
      } catch (error) {
        if (current === sequence) status('error', error.message);
      }
    };
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {create};
  if (typeof document === 'undefined') return;
  const el = id => document.getElementById(id);
  const convert = create({
    snapshot: () => ({text:el('taigi-hanji').value.trim(), source:el('taigi-source').value,
                     poj:el('taigi-text').value, job:state.job}),
    request: async text => (await api('/api/taigi-pronunciation', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})
    })).json(),
    apply: result => {
      stopSpeech();
      el('taigi-audio').hidden = true;
      el('taigi-text').value = result.poj;
      el('taigi-confirm').checked = false;
    },
    status: (status, detail) => {
      el('taigi-convert').disabled = status === 'working';
      el('taigi-convert-status').textContent = {
        working:'正在本機轉寫台語漢字…',
        stale:'內容已變更，未套用舊草稿，請重新轉寫。',
        ready:'草稿已填入下方，請核對後按「試聽台語」。' + (detail || ''),
        error:detail
      }[status];
    }
  });
  el('taigi-convert').onclick = convert;
  el('taigi-hanji').addEventListener('input', () => {
    stopSpeech(); buttons();
    el('taigi-confirm').checked = false;
    el('taigi-text').value = '';
    el('taigi-audio').pause(); el('taigi-audio').hidden = true;
    el('taigi-play-status').textContent = '漢字已變更，請重新轉寫再試聽。';
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
