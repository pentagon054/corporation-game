/* Corporation v22 player moderation panel */
(() => {
  "use strict";
  const tg = window.Telegram?.WebApp;
  tg?.ready?.();

  const headers = () => {
    const h = {"Content-Type":"application/json"};
    if (tg?.initData) h["X-Telegram-Init-Data"] = tg.initData;
    const dev = new URLSearchParams(location.search).get("user_id");
    if (dev) h["X-User-Id"] = dev;
    return h;
  };
  async function req(url, options={}){
    const res = await fetch(url,{...options,headers:{...headers(),...(options.headers||{})},cache:"no-store"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.detail||`HTTP ${res.status}`);
    return data;
  }
  const esc = s => String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money = n => new Intl.NumberFormat("ru-RU",{maximumFractionDigits:0}).format(Number(n||0))+" ₽";

  const style=document.createElement("style");
  style.textContent=`
    #v22-player-control{margin:18px auto;max-width:980px;padding:16px;border:1px solid rgba(255,255,255,.12);border-radius:20px;background:rgba(20,20,22,.96);color:#fff;font-family:Inter,system-ui,sans-serif}
    #v22-player-control *{box-sizing:border-box} .v22-head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}.v22-head h2{margin:0}.v22-search{display:flex;gap:8px;flex:1;min-width:230px}.v22-search input{flex:1;min-width:0;padding:11px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:#101014;color:#fff}.v22-search button,.v22-actions button{border:0;border-radius:11px;padding:10px 12px;font-weight:800;cursor:pointer}.v22-list{display:grid;gap:10px;margin-top:14px}.v22-player{padding:13px;border:1px solid rgba(255,255,255,.1);border-radius:15px;background:#111216}.v22-player-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.v22-player h3{margin:0 0 4px;font-size:16px}.v22-meta{font-size:12px;color:#a9abb3;line-height:1.5}.v22-cap{font-weight:900;white-space:nowrap}.v22-flags{display:flex;gap:6px;flex-wrap:wrap;margin:9px 0}.v22-badge{font-size:11px;padding:5px 8px;border-radius:999px;background:#262830}.v22-badge.freeze{background:#45370c;color:#ffd766}.v22-badge.block{background:#4b1616;color:#ff8d8d}.v22-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.v22-actions .freeze{background:#f1c94e;color:#17130a}.v22-actions .block{background:#8e2d2d;color:#fff}.v22-actions .delete{background:#3a1515;color:#ff9f9f;border:1px solid #6e2525}.v22-status{margin-top:10px;font-size:12px;color:#aaa}.v22-empty{padding:20px;text-align:center;color:#999}@media(max-width:600px){.v22-actions{grid-template-columns:1fr}.v22-player-top{display:grid}.v22-cap{white-space:normal}}
  `;
  document.head.appendChild(style);

  const root=document.createElement("section");
  root.id="v22-player-control";
  root.innerHTML=`<div class="v22-head"><div><h2>👤 Управление игроками</h2><div class="v22-meta">Заморозка, блокировка и полное удаление</div></div><div class="v22-search"><input id="v22-q" placeholder="ID, @username или корпорация"><button id="v22-find">Найти</button></div></div><div id="v22-status" class="v22-status"></div><div id="v22-list" class="v22-list"><div class="v22-empty">Загрузка…</div></div>`;
  (document.querySelector("main")||document.querySelector(".app")||document.body).appendChild(root);

  let rows=[];
  async function load(){
    const q=document.querySelector("#v22-q").value.trim();
    document.querySelector("#v22-status").textContent="Обновление списка…";
    rows=await req(`/api/admin/players?limit=100&q=${encodeURIComponent(q)}`);
    render();
    document.querySelector("#v22-status").textContent=`Игроков показано: ${rows.length}`;
  }
  function render(){
    const list=document.querySelector("#v22-list");
    if(!rows.length){list.innerHTML='<div class="v22-empty">Игроки не найдены</div>';return;}
    list.innerHTML=rows.map(p=>{
      const frozen=!!Number(p.is_frozen||0),blocked=!!Number(p.is_blocked||0);
      return `<article class="v22-player"><div class="v22-player-top"><div><h3>${esc(p.corp_name||"Без названия")}</h3><div class="v22-meta">ID: ${esc(p.user_id)} · ${p.username?"@"+esc(p.username):"без username"}</div></div><div class="v22-cap">${money(p.capital)}</div></div><div class="v22-flags">${frozen?'<span class="v22-badge freeze">Заморожен</span>':''}${blocked?'<span class="v22-badge block">Заблокирован</span>':''}${!frozen&&!blocked?'<span class="v22-badge">Активен</span>':''}</div><div class="v22-actions"><button class="freeze" data-act="freeze" data-id="${p.user_id}" data-enabled="${!frozen}">${frozen?"Разморозить":"Заморозить"}</button><button class="block" data-act="block" data-id="${p.user_id}" data-enabled="${!blocked}">${blocked?"Разблокировать":"Заблокировать"}</button><button class="delete" data-act="delete" data-id="${p.user_id}">Удалить игрока</button></div></article>`;
    }).join("");
  }
  root.addEventListener("click",async e=>{
    const b=e.target.closest("button[data-act]"); if(!b)return;
    const id=Number(b.dataset.id),act=b.dataset.act;
    try{
      if(act==="delete"){
        const ok=confirm(`Удалить игрока ${id} полностью? Перед удалением сервер создаст backup базы.`); if(!ok)return;
        const phrase=prompt('Для подтверждения введи: DELETE PLAYER'); if(phrase!=="DELETE PLAYER")return;
        await req(`/api/admin/player/${id}`,{method:"DELETE",body:JSON.stringify({confirmation:phrase})});
      }else{
        const enabled=b.dataset.enabled==="true";
        const word=act==="freeze"?(enabled?"заморозить":"разморозить"):(enabled?"заблокировать":"разблокировать");
        if(!confirm(`${word[0].toUpperCase()+word.slice(1)} игрока ${id}?`))return;
        await req(`/api/admin/player/${id}/${act}`,{method:"POST",body:JSON.stringify({enabled})});
      }
      await load();
    }catch(err){alert(err.message);}
  });
  document.querySelector("#v22-find").onclick=()=>load().catch(e=>alert(e.message));
  document.querySelector("#v22-q").addEventListener("keydown",e=>{if(e.key==="Enter")load().catch(x=>alert(x.message));});
  load().catch(err=>{document.querySelector("#v22-list").innerHTML=`<div class="v22-empty">${esc(err.message)}</div>`;});
})();
