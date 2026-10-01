'use strict';
(function(root) {
  function create({request, onState, now = Date.now}) {
    let active = null, lastReady = -Infinity;
    function prepare() {
      if(active)return active;
      if(now() - lastReady < 60000)return Promise.resolve({status:'ready'});
      onState('preparing');
      active = Promise.resolve().then(request).then(result => {
        if(result.status === 'ready')lastReady = now();
        onState(result.status === 'ready' ? 'ready' : 'busy');
        return result;
      }).catch(() => {
        onState('unavailable');
        return {status:'unavailable'};
      }).finally(() => { active = null; });
      return active;
    }
    return {prepare};
  }
  if(typeof module !== 'undefined' && module.exports)module.exports = {create};
  else root.PaperVoiceWarmup = {create};
})(typeof window !== 'undefined' ? window : globalThis);
