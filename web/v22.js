/* Corporation v26.1 — lightweight market live indicator. */
(() => {
  "use strict";
  if(!document.getElementById('corporation-v22-style')){
    const s=document.createElement('style');
    s.id='corporation-v22-style';
    s.textContent=`.corp-v22-news-livebar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;margin:0 0 12px;border-radius:14px;background:linear-gradient(135deg,rgba(214,191,141,.09),rgba(255,255,255,.025));border:1px solid rgba(214,191,141,.16);font-size:12px}.corp-v22-live-label{display:flex;align-items:center;gap:7px;font-weight:800}.corp-v22-live-dot{width:7px;height:7px;border-radius:50%;background:#d75b5b;animation:v22pulse 1.9s ease-out infinite}.corp-v22-news-time{opacity:.62;font-weight:700;font-variant-numeric:tabular-nums}@keyframes v22pulse{70%{box-shadow:0 0 0 6px rgba(215,91,91,0)}}@media(prefers-reduced-motion:reduce){.corp-v22-live-dot{animation:none}}`;
    document.head.appendChild(s);
  }

  const content=document.querySelector('#content');
  let queued=false;
  function installNewsBar(){
    if(!content)return;
    const t=(content.textContent||'').toLowerCase();
    if(!(t.includes('новост')&&(t.includes('рын')||t.includes('акци'))))return;
    if(content.querySelector('.corp-v22-news-livebar'))return;
    const x=document.createElement('div');
    x.className='corp-v22-news-livebar';
    x.innerHTML='<span class="corp-v22-live-label"><i class="corp-v22-live-dot"></i> LIVE · РЫНОК</span><span class="corp-v22-news-time">лента активна</span>';
    content.prepend(x);
  }
  function schedule(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(()=>{queued=false;installNewsBar();});
  }
  installNewsBar();
  if(content)new MutationObserver(schedule).observe(content,{childList:true,subtree:false});
  setInterval(()=>{
    if(document.hidden)return;
    const e=document.querySelector('.corp-v22-news-time');
    if(e)e.textContent='лента активна · '+new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'});
  },30000);
})();
