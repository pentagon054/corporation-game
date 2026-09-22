/* Browser zoom and Telegram sheet gestures are separate from atlas camera zoom. */
(()=>{
  'use strict';
  function protectTelegram(){
    const app=window.Telegram?.WebApp;
    if(!app)return;
    try{
      if(typeof app.disableVerticalSwipes==='function' &&
         (!app.isVersionAtLeast || app.isVersionAtLeast('7.7'))){
        app.disableVerticalSwipes();
      }
    }catch(error){console.warn('Telegram swipe protection unavailable',error);}
  }
  protectTelegram();
  window.addEventListener('pageshow',protectTelegram);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)protectTelegram();});
  const cancel=e=>{if(e.cancelable)e.preventDefault();};
  // Safari gesture events must not zoom the viewport. Atlas uses Pointer Events.
  for(const type of ['gesturestart','gesturechange','gestureend'])
    document.addEventListener(type,cancel,{passive:false});
  document.addEventListener('touchmove',e=>{
    if(e.touches.length>1 || e.target.closest?.('.interactive-map-viewport'))cancel(e);
  },{passive:false});
  // Prevent the browser's default double-tap zoom, preserving every button click.
  document.addEventListener('dblclick',cancel,{passive:false});
  let lastTap=null;
  document.addEventListener('touchend',e=>{
    if(e.touches.length || e.changedTouches.length!==1){lastTap=null;return;}
    const t=e.changedTouches[0],now=performance.now();
    const interactive=e.target.closest?.('button,a,input,select,textarea,[role="button"],.interactive-map-viewport');
    if(!interactive && lastTap && now-lastTap.time<320 &&
       Math.hypot(t.clientX-lastTap.x,t.clientY-lastTap.y)<24)cancel(e);
    lastTap={time:now,x:t.clientX,y:t.clientY};
  },{passive:false});
})();
