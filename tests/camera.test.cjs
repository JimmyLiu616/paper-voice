// Pure JS lifecycle tests, using synthetic streams. Does not access physical devices.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/camera.js'),'utf8');
function fixture(getUserMedia) {
  const nodes=new Map(), events={}, chosen=[], messages=[];
  let analyses=0;
  function node(id){
    if(nodes.has(id))return nodes.get(id);
    const n={hidden:false,disabled:false,open:false,value:'',options:[],events:{},videoWidth:1920,videoHeight:1080,
      addEventListener(name,fn){this.events[name]=fn;},removeAttribute(name){delete this[name];},
      showModal(){this.open=true;},close(){this.open=false;this.events.close?.();},focus(){},
      play:async()=>{},getContext:()=>({drawImage(){}}),
      toBlob(callback){callback(new Blob(['synthetic jpeg'],{type:'image/jpeg'}));},
      replaceChildren(){this.options=[];},append(value){this.options.push(value);}};
    nodes.set(id,n);return n;
  }
  const context={document:{hidden:false,getElementById:node,createElement:tag=>node('new-'+tag),addEventListener:(name,fn)=>events[name]=fn},
    window:{isSecureContext:true,addEventListener:(name,fn)=>events[name]=fn},
    navigator:{mediaDevices:{getUserMedia,enumerateDevices:async()=>[{kind:'videoinput',deviceId:'one',label:'Test camera'}]}},
    URL:{createObjectURL:()=> 'blob:synthetic',revokeObjectURL(){}},Blob,File,
    chooseFile:file=>chosen.push(file),modelReady:true,analyze:()=>analyses++,message:text=>messages.push(text)};
  vm.runInNewContext(source,context);
  return {node,context,events,chosen,messages,analyses:()=>analyses};
}
function syntheticStream(){
  const track={stops:0,stop(){this.stops++;},getSettings:()=>({deviceId:'one'})};
  return {track,getTracks:()=>[track],getVideoTracks:()=>[track]};
}
test('opening the dialog does not request camera permission',()=>{
  let calls=0;const f=fixture(()=>{calls++;});f.node('camera-open').onclick();
  assert.equal(f.node('camera-dialog').open,true);assert.equal(calls,0);
});
test('camera granted after closing is immediately released',async()=>{
  let grant;const f=fixture(()=>new Promise(resolve=>grant=resolve));const stream=syntheticStream();
  f.node('camera-open').onclick();const pending=f.node('camera-start').onclick();
  f.node('camera-close').onclick();grant(stream);await pending;
  assert.equal(stream.track.stops,1);assert.equal(f.node('camera-video').srcObject,null);
  assert.equal(f.chosen.length,0);
});
test('capture releases camera and only confirmation submits the photo',async()=>{
  const stream=syntheticStream();let constraints;const f=fixture(async c=>{constraints=c;return stream;});
  f.node('camera-open').onclick();await f.node('camera-start').onclick();
  assert.equal(constraints.audio,false);assert.equal(f.node('camera-shutter').disabled,false);
  await f.node('camera-shutter').onclick();assert.equal(stream.track.stops,1);
  assert.equal(f.chosen.length,0);assert.equal(f.node('camera-use').hidden,false);
  f.node('camera-use').onclick();assert.equal(f.chosen[0].type,'image/jpeg');
  assert.equal(f.analyses(),1);assert.equal(f.node('camera-dialog').open,false);
});
test('permission denial offers retry and does not submit',async()=>{
  const f=fixture(async()=>{throw {name:'NotAllowedError'};});
  f.node('camera-open').onclick();await f.node('camera-start').onclick();
  assert.match(f.node('camera-status').textContent,/權限未允許/);
  assert.equal(f.node('camera-start').disabled,false);assert.equal(f.chosen.length,0);
});
test('hidden page releases stream and closes preview',async()=>{
  const stream=syntheticStream(),f=fixture(async()=>stream);
  f.node('camera-open').onclick();await f.node('camera-start').onclick();
  f.context.document.hidden=true;f.events.visibilitychange();
  assert.equal(stream.track.stops,1);assert.equal(f.node('camera-dialog').open,false);
});
test('closing while JPEG is encoding cannot resurrect the captured photo',async()=>{
  const stream=syntheticStream(),f=fixture(async()=>stream);let encode;
  f.node('new-canvas').toBlob=callback=>{encode=callback;};
  f.node('camera-open').onclick();await f.node('camera-start').onclick();
  const pending=f.node('camera-shutter').onclick();f.node('camera-close').onclick();
  encode(new Blob(['fake'],{type:'image/jpeg'}));await pending;
  assert.equal(f.chosen.length,0);assert.equal(f.node('camera-use').hidden,true);
});
