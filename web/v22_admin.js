/* Corporation v26.1 — player moderation + owner-only private balance correction. */
(() => {
  "use strict";
  const tg = window.Telegram?.WebApp;
  tg?.ready?.();

  const headers = () => {
    const h = {"Content-Type":"application/json"};
    if (tg?.initData) h["X-Telegram-Init-Data"] = tg.initData;
    const dev = new URLSearchParams(location.search).get("user_id");
    if (dev && ["localhost","127.0.0.1"].includes(location.hostname)) h["X-User-Id"] = dev;
    return h;
  };
  async function req(url, options={}){
    const res = await fetch(url,{...options,headers:{...headers(),...(options.headers||{})},cache:"no-store"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.detail||`HTTP ${res.status}`);
    return data;
  }
  const esc = s => String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money = n => new Intl.NumberFormat("ru-RU",{maximumFractionDigits:2}).format(Number(n||0))+" ₽";

  const style=document.createElement("style");
  style.textContent=`
    #v22-player-control{margin:18px auto;max-width:980px;padding:16px;border:1px solid rgba(255,255,255,.12);border-radius:20px;background:rgba(20,20,22,.96);color:#fff;font-family:Inter,system-ui,sans-serif}
    #v22-player-control *{box-sizing:border-box}.v22-head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}.v22-head h2{margin:0}.v22-search{display:flex;gap:8px;flex:1;min-width:230px}.v22-search input{flex:1;min-width:0;padding:11px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:#101014;color:#fff}.v22-search button,.v22-actions button{border:0;border-radius:11px;padding:10px 12px;font-weight:800;cursor:pointer}.v22-list{display:grid;gap:10px;margin-top:14px}.v22-player{padding:13px;border:1px solid rgba(255,255,255,.1);border-radius:15px;background:#111216}.v22-player-top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.v22-player h3{margin:0 0 4px;font-size:16px}.v22-meta{font-size:12px;color:#a9abb3;line-height:1.5}.v22-cap{font-weight:900;white-space:nowrap}.v22-flags{display:flex;gap:6px;flex-wrap:wrap;margin:9px 0}.v22-badge{font-size:11px;padding:5px 8px;border-radius:999px;background:#262830}.v22-badge.freeze{background:#45370c;color:#ddc28b}.v22-badge.block{background:#4b1616;color:#ff8d8d}.v22-actions{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.v22-actions .freeze{background:#b99655;color:#17130a}.v22-actions .grant{background:#d6bf8d;color:#17130a}.v22-actions .block{background:#8e2d2d;color:#fff}.v22-actions .delete{background:#3a1515;color:#ff9f9f;border:1px solid #6e2525}.v22-status{margin-top:10px;font-size:12px;color:#aaa}.v22-status.ok{color:#9ad8b6}.v22-empty{padding:20px;text-align:center;color:#999}
    .v22-private-overlay{position:fixed;inset:0;z-index:9000;display:grid;place-items:end center;padding:16px;background:rgba(0,0,0,.68);backdrop-filter:blur(5px)}.v22-private-card{width:min(560px,100%);padding:18px;border:1px solid rgba(255,255,255,.14);border-radius:20px;background:#171b22;box-shadow:0 24px 80px rgba(0,0,0,.55);animation:v22PrivateIn .16s ease-out}.v22-private-card h3{margin:0 0 5px}.v22-private-grid{display:grid;gap:11px;margin-top:15px}.v22-private-grid label{display:grid;gap:6px;color:#a9abb3;font-size:11px}.v22-private-grid input,.v22-private-grid select,.v22-private-grid textarea{width:100%;border:1px solid rgba(255,255,255,.14);border-radius:11px;background:#0d1117;color:#fff;padding:12px;font:inherit;outline:none}.v22-private-grid textarea{min-height:78px;resize:vertical}.v22-private-grid input:focus,.v22-private-grid select:focus,.v22-private-grid textarea:focus{border-color:#d6bf8d}.v22-private-note{font-size:11px;color:#8e98a7;line-height:1.45}.v22-private-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}.v22-private-actions button{min-height:44px;border-radius:11px;border:1px solid rgba(255,255,255,.12);font-weight:800}.v22-private-cancel{background:#202630;color:#fff}.v22-private-submit{background:#d6bf8d;color:#17130a}.v22-private-submit:disabled{opacity:.55}.v22-private-error{min-height:17px;color:#ff9b9b;font-size:11px;margin-top:8px}@keyframes v22PrivateIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
    @media(max-width:600px){.v22-actions{grid-template-columns:1fr}.v22-player-top{display:grid}.v22-cap{white-space:normal}.v22-private-overlay{padding:10px}.v22-private-card{border-radius:18px}.v22-private-actions{grid-template-columns:1fr}}
    @media(prefers-reduced-motion:reduce){.v22-private-card{animation:none}}
  `;
  document.head.appendChild(style);

  const root=document.createElement("section");
  root.id="v22-player-control";
  root.innerHTML=`<div class="v22-head"><div><h2>👤 Управление игроками</h2><div class="v22-meta">Заморозка, блокировка и полное удаление</div></div><div class="v22-search"><input id="v22-q" placeholder="ID, @username или корпорация"><button id="v22-find">Найти</button></div></div><div id="v22-status" class="v22-status"></div><div id="v22-list" class="v22-list"><div class="v22-empty">Загрузка…</div></div>`;
  (document.querySelector("main")||document.querySelector(".app")||document.body).appendChild(root);

  let rows=[];
  let canPrivateCredit=false;

  async function load(){
    const q=document.querySelector("#v22-q").value.trim();
    const status=document.querySelector("#v22-status");
    status.className="v22-status";
    status.textContent="Обновление списка…";
    const [players,meta]=await Promise.all([
      req(`/api/admin/players?limit=100&q=${encodeURIComponent(q)}`),
      req('/api/admin/overview')
    ]);
    rows=players;
    canPrivateCredit=Boolean(meta?.private_capabilities?.grant_money);
    render();
    status.textContent=`Игроков показано: ${rows.length}`;
  }

  function render(){
    const list=document.querySelector("#v22-list");
    if(!rows.length){list.innerHTML='<div class="v22-empty">Игроки не найдены</div>';return;}
    list.innerHTML=rows.map(p=>{
      const frozen=!!Number(p.is_frozen||0),blocked=!!Number(p.is_blocked||0);
      const grant=canPrivateCredit?`<button class="grant" data-act="grant" data-id="${p.user_id}" data-name="${esc(p.corp_name||'Игрок')}">Коррекция баланса</button>`:'';
      return `<article class="v22-player"><div class="v22-player-top"><div><h3>${esc(p.corp_name||"Без названия")}</h3><div class="v22-meta">ID: ${esc(p.user_id)} · ${p.username?"@"+esc(p.username):"без username"}</div></div><div class="v22-cap">${money(p.capital)}</div></div><div class="v22-flags">${frozen?'<span class="v22-badge freeze">Заморожен</span>':''}${blocked?'<span class="v22-badge block">Заблокирован</span>':''}${!frozen&&!blocked?'<span class="v22-badge">Активен</span>':''}</div><div class="v22-actions">${grant}<button class="freeze" data-act="freeze" data-id="${p.user_id}" data-enabled="${!frozen}">${frozen?"Разморозить":"Заморозить"}</button><button class="block" data-act="block" data-id="${p.user_id}" data-enabled="${!blocked}">${blocked?"Разблокировать":"Заблокировать"}</button><button class="delete" data-act="delete" data-id="${p.user_id}">Удалить игрока</button></div></article>`;
    }).join("");
  }

  function privateCreditDialog({id,name}){
    return new Promise(resolve=>{
      const overlay=document.createElement('div');
      overlay.className='v22-private-overlay';
      overlay.innerHTML=`<div class="v22-private-card" role="dialog" aria-modal="true"><h3>Коррекция баланса</h3><div class="v22-meta">${esc(name||'Игрок')} · ID ${id}</div><div class="v22-private-grid"><label>Сумма<input id="v22-credit-amount" type="text" inputmode="decimal" autocomplete="off" value="10000"></label><label>Как отразить в статистике<select id="v22-credit-category"><option value="prize">Приз / бонус</option><option value="business">Доход бизнеса</option><option value="dividends">Дивиденды</option><option value="bonds">Доход облигаций</option><option value="rent">Аренда недвижимости</option><option value="stock_profit">Прибыль от акций</option><option value="other">Прочий доход</option><option value="balance">Только баланс — не считать прибылью</option></select></label><label>Комментарий<textarea id="v22-credit-note" maxlength="300" placeholder="Необязательно"></textarea></label><div class="v22-private-note">Операция проходит только через защищённый серверный доступ владельца. Категория «Только баланс» не меняет общую прибыль игрока.</div></div><div id="v22-credit-error" class="v22-private-error"></div><div class="v22-private-actions"><button class="v22-private-cancel" type="button">Отмена</button><button class="v22-private-submit" type="button">Начислить</button></div></div>`;
      document.body.appendChild(overlay);
      const amount=overlay.querySelector('#v22-credit-amount');
      const category=overlay.querySelector('#v22-credit-category');
      const note=overlay.querySelector('#v22-credit-note');
      const error=overlay.querySelector('#v22-credit-error');
      const submit=overlay.querySelector('.v22-private-submit');
      const close=value=>{overlay.remove();resolve(value)};
      overlay.querySelector('.v22-private-cancel').onclick=()=>close(null);
      overlay.addEventListener('click',e=>{if(e.target===overlay)close(null)});
      submit.onclick=()=>{
        const normalized=String(amount.value||'').replace(/\s/g,'').replace(',','.');
        const n=Number(normalized);
        if(!Number.isFinite(n)||n<=0){error.textContent='Введите положительную сумму.';amount.focus();return;}
        if(n>1_000_000_000_000){error.textContent='Сумма слишком большая.';amount.focus();return;}
        close({amount:n,category:category.value,note:note.value||'',count_as_income:category.value!=='balance'});
      };
      setTimeout(()=>{amount.focus({preventScroll:true});amount.select();},0);
    });
  }

  root.addEventListener("click",async e=>{
    const b=e.target.closest("button[data-act]"); if(!b)return;
    const id=Number(b.dataset.id),act=b.dataset.act;
    try{
      if(act==="grant"){
        if(!canPrivateCredit)return;
        const payload=await privateCreditDialog({id,name:b.dataset.name||`Игрок ${id}`});
        if(!payload)return;
        b.disabled=true;
        const result=await req(`/api/admin/player/${id}/grant`,{method:"POST",body:JSON.stringify(payload)});
        const status=document.querySelector('#v22-status');
        status.className='v22-status ok';
        status.textContent=`Баланс обновлён: +${money(result.amount)} · новый баланс ${money(result.state?.player?.money)}`;
      }else if(act==="delete"){
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
    }catch(err){
      document.querySelector('#v22-status').textContent=err.message;
      alert(err.message);
    }finally{b.disabled=false;}
  });

  document.querySelector("#v22-find").onclick=()=>load().catch(e=>alert(e.message));
  document.querySelector("#v22-q").addEventListener("keydown",e=>{if(e.key==="Enter")load().catch(x=>alert(x.message));});
  load().catch(err=>{document.querySelector("#v22-list").innerHTML=`<div class="v22-empty">${esc(err.message)}</div>`;});
})();
