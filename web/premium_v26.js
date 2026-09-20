/* Corporation 26 — reliability/UX patch: stable scroll, native-dialog replacement,
   second-accurate timers, company logos and income-source statistics. */
(() => {
  'use strict';

  const LOGO = {
    bmw:'https://cdn.simpleicons.org/bmw', kfc:'https://cdn.simpleicons.org/kfc', spotify:'https://cdn.simpleicons.org/spotify',
    nvidia:'https://cdn.simpleicons.org/nvidia', tesla:'https://cdn.simpleicons.org/tesla', mcdonalds:'https://cdn.simpleicons.org/mcdonalds',
    toyota:'https://cdn.simpleicons.org/toyota', apple:'https://cdn.simpleicons.org/apple', google:'https://cdn.simpleicons.org/google', intel:'https://cdn.simpleicons.org/intel'
  };

  let retainedScroll26 = null;
  let lastTimerSecond26 = -1;
  const scrollY26 = () => Math.max(0, window.scrollY || document.documentElement.scrollTop || 0);
  function restoreScroll26(y){
    if(!Number.isFinite(y)) return;
    retainedScroll26 = y;
    requestAnimationFrame(()=>requestAnimationFrame(()=>window.scrollTo({top:y,left:0,behavior:'instant'})));
  }
  async function stable26(work){ const y=scrollY26(); try{return await work();} finally{restoreScroll26(y);} }

  function ensureDialog26(){
    let el=document.querySelector('#action-modal26');
    if(el) return el;
    el=document.createElement('div'); el.id='action-modal26'; el.className='action-modal26 hidden';
    el.innerHTML=`<div class="action-card26" role="dialog" aria-modal="true"><div class="action-handle26"></div><h2></h2><p class="action-copy26"></p><div class="action-qty26" hidden><button type="button" data-step="-1">−</button><input inputmode="numeric" pattern="[0-9]*" autocomplete="off"><button type="button" data-step="1">+</button></div><input class="action-text26" type="text" maxlength="40" autocomplete="off" hidden><button class="action-max26" type="button" hidden>Максимум</button><div class="action-buttons26"><button class="action-cancel26" type="button">Отмена</button><button class="action-ok26" type="button">Готово</button></div><div class="action-error26" aria-live="polite"></div></div>`;
    document.body.appendChild(el); return el;
  }
  function dialog26({title,text,quantity=false,max=1,value=1,textInput=false,textValue='',ok='Готово',showMax=true}){
    const y=scrollY26(),el=ensureDialog26(),card=el.querySelector('.action-card26'),input=el.querySelector('.action-qty26 input'),textEl=el.querySelector('.action-text26'),qty=el.querySelector('.action-qty26'),maxBtn=el.querySelector('.action-max26'),err=el.querySelector('.action-error26');
    el.querySelector('h2').textContent=title||''; el.querySelector('.action-copy26').textContent=text||''; el.querySelector('.action-ok26').textContent=ok; err.textContent='';
    qty.hidden=!quantity; textEl.hidden=!textInput; maxBtn.hidden=!quantity||!showMax||max<=1;
    if(quantity){ input.value=String(Math.min(Math.max(1,Number(value)||1),max)); input.dataset.max=String(max); }
    if(textInput) textEl.value=String(textValue||'');
    el.classList.remove('hidden');
    return new Promise(resolve=>{
      let done=false;
      const finish=v=>{if(done)return;done=true;el.classList.add('hidden');cleanup();restoreScroll26(y);resolve(v)};
      const validate=()=>{const n=Number(input.value);if(!Number.isSafeInteger(n)||n<1||n>max){err.textContent=`Введите целое число от 1 до ${max}.`;return null}return n};
      const onClick=e=>{
        const step=e.target.closest('[data-step]'); if(step){const n=Math.min(max,Math.max(1,(Number(input.value)||1)+Number(step.dataset.step)));input.value=String(n);return;}
        if(e.target.closest('.action-max26')){input.value=String(max);return;}
        if(e.target.closest('.action-cancel26')||e.target===el){finish(null);return;}
        if(e.target.closest('.action-ok26')){if(textInput){const v=textEl.value.trim();if(!v){err.textContent='Введите название.';return;}return finish(v);}if(!quantity)return finish(true);const n=validate();if(n!==null)finish(n);}
      };
      const onKey=e=>{if(e.key==='Escape'){e.preventDefault();finish(null)}else if(e.key==='Enter'){e.preventDefault();if(textInput){const v=textEl.value.trim();if(!v){err.textContent='Введите название.';return;}return finish(v);}if(!quantity)return finish(true);const n=validate();if(n!==null)finish(n)}};
      const cleanup=()=>{el.removeEventListener('click',onClick);card.removeEventListener('keydown',onKey)};
      el.addEventListener('click',onClick); card.addEventListener('keydown',onKey);
      if(quantity) setTimeout(()=>input.focus({preventScroll:true}),30); else if(textInput) setTimeout(()=>{textEl.focus({preventScroll:true});textEl.select();},30); else setTimeout(()=>el.querySelector('.action-ok26').focus({preventScroll:true}),30);
    });
  }
  const confirm26=(title,text,ok='Готово')=>dialog26({title,text,ok});
  const quantity26=(title,text,max,value=1)=>dialog26({title,text,quantity:true,max,value,ok:'Готово'});
  const renameBtn26=document.querySelector('#renameBtn');
  if(renameBtn26) renameBtn26.onclick=async()=>{if(!state)return;const y=scrollY26(),name=await dialog26({title:'Название корпорации',text:'Введи новое название компании.',textInput:true,textValue:state.player.corp_name,ok:'Сохранить'});if(name===null)return;try{state=await api('/api/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});render();restoreScroll26(y);}catch(e){modal('Ошибка',e.message);restoreScroll26(y)}};

  // Preserve the current viewport when the standard success modal is dismissed.
  document.querySelector('#modalClose')?.addEventListener('click',()=>{ if(retainedScroll26!==null) restoreScroll26(retainedScroll26); },true);

  // --- Fleet: no native prompt/confirm, no dialog-suppression bug, no scroll jump. ---
  window.buyFleetVehicle25 = async function(bid,vid){
    const y=scrollY26(), b=(state.businesses||[]).find(x=>x.id===bid), v=b?.transport?.vehicles?.find(x=>x.id===vid); if(!v)return;
    const max=Math.min(Number(b.transport.available||0),Math.floor(Number(state.player.money||0)/Number(v.cost||1)));
    if(max<1){modal('Покупка','Нет свободного места в гараже или недостаточно денег.');restoreScroll26(y);return;}
    const q=await quantity26(`Купить: ${v.name}`,`Цена за 1: ${fmt(v.cost)} · свободных мест: ${b.transport.available} · доступно по балансу: ${max}`,max,1); if(q===null)return;
    try{const r=await api(`/api/fleet/${bid}/vehicle/${vid}/buy`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:q})});state=r.state;renderHeader();renderBusinesses();restoreScroll26(y);}catch(e){modal('Не удалось купить',e.message);restoreScroll26(y)}
  };
  window.sellFleetVehicle25 = async function(bid,vid){
    const y=scrollY26(), b=(state.businesses||[]).find(x=>x.id===bid), v=b?.transport?.vehicles?.find(x=>x.id===vid); if(!v?.quantity)return;
    const q=await quantity26(`Продать: ${v.name}`,`В парке: ${v.quantity} · возврат за 1: ${fmt(v.sell_price)}`,Number(v.quantity),1); if(q===null)return;
    try{const r=await api(`/api/fleet/${bid}/vehicle/${vid}/sell`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:q})});state=r.state;renderHeader();renderBusinesses();restoreScroll26(y);}catch(e){modal('Не удалось продать',e.message);restoreScroll26(y)}
  };
  window.upgradeGarage25 = async function(bid){
    const y=scrollY26(),b=(state.businesses||[]).find(x=>x.id===bid),f=b?.transport;if(!f||f.upgrading||f.maxed)return;
    if(!await confirm26('Расширение автопарка',`Расширить гараж до ${f.next_capacity} мест за ${fmt(f.next_upgrade_cost)}?`,'Начать'))return;
    try{const r=await api(`/api/fleet/${bid}/garage/upgrade`,{method:'POST'});state=r.state;renderHeader();renderBusinesses();restoreScroll26(y);}catch(e){modal('Расширение не начато',e.message);restoreScroll26(y)}
  };

  // --- Generic business actions: preserve exact viewport position. ---
  const baseBuyBusiness26=window.buyBusiness, baseUpgradeBusiness26=window.upgradeBusiness;
  if(baseBuyBusiness26) window.buyBusiness=id=>stable26(()=>baseBuyBusiness26(id));
  if(baseUpgradeBusiness26) window.upgradeBusiness=(id,uid)=>stable26(()=>baseUpgradeBusiness26(id,uid));
  window.sellBusiness=async function(id){
    const y=scrollY26(),b=(state.businesses||[]).find(x=>x.id===id);if(!b)return;
    if(!await confirm26('Продать бизнес',`Продать «${b.name}» за ${fmt(b.sell_price)}?`,'Продать'))return;
    try{const r=await api(`/api/business/${id}/sell`,{method:'POST'});state=r.state;render();restoreScroll26(y);modal('Бизнес продан',`Получено ${fmt(r.sell_price)}.`)}catch(e){modal('Ошибка',e.message);restoreScroll26(y)}
  };

  // --- Stocks and bonds: one reliable in-game quantity dialog. ---
  corporationTrade=async function(kind,id,side,all=false){
    if(corporationTradeBusy || !['buy','sell'].includes(side))return;
    corporationTradeBusy=true; const y=scrollY26();
    try{
      state=await api('/api/state');renderHeader();
      let item,owned,price;
      if(kind==='stocks'){const [quote]=await Promise.all([api(`/api/stocks/${id}`),loadBrokerage()]);item=quote;owned=Number(getHolding(id)?.quantity||0);price=Number(quote.current_price);}
      else{await loadBonds();item=bondsCache.find(x=>String(x.id)===String(id));if(!item)return;owned=Number(item.quantity||0);price=Number(item.price);}
      if(!Number.isFinite(price)||price<=0)throw new Error('Не удалось получить актуальную цену.');
      const max=Math.min(Number.MAX_SAFE_INTEGER,side==='buy'?Math.floor(Number(state.player.money||0)/price):owned);
      if(max<=0){modal('Сделка',side==='buy'?'Недостаточно свободных денег.':'У тебя нет этих бумаг.');return;}
      const qty=all?max:await quantity26(`${side==='buy'?'Купить':'Продать'} ${item.name}`,`Цена: ${fmt(price)} · максимум: ${max} шт.`,max,1); if(qty===null)return;
      if(all && !await confirm26('Подтвердить сделку',`${side==='buy'?'Купить':'Продать'} ${qty} шт. ${item.name} на ${fmt(qty*price)}?`,side==='buy'?'Купить':'Продать'))return;
      const result=await api(`/api/${kind}/${id}/${side}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:qty,expected_price:price})});
      state=result.state;renderHeader();
      try{if(kind==='stocks')await Promise.all([loadStocks(),loadBrokerage()]);else await loadBonds();if(page==='investments'){if(kind==='stocks'&&String(corporationActiveStockId)===String(id))await openStock(id,true);else await renderInvestments();}}catch(_){}
      restoreScroll26(y);modal(side==='buy'?'Бумаги куплены':'Бумаги проданы',`Количество: ${result.quantity} шт.\nСумма: ${fmt(side==='buy'?result.total_cost:result.total_income)}`);
    }catch(error){modal('Сделка не выполнена',error.message);}finally{corporationTradeBusy=false;restoreScroll26(y);}
  };
  openTrade=(id,side)=>corporationTrade('stocks',id,side); openBondTrade=(id,side)=>corporationTrade('bonds',id,side);
  window.openTrade=openTrade; window.openBondTrade=openBondTrade; window.tradeAllStock=(id,side)=>corporationTrade('stocks',id,side,true); window.tradeAllBond=(id,side)=>corporationTrade('bonds',id,side,true);

  // --- Real estate: same stable flow. ---
  buyProperty=async function(id){
    if(corporationPropertyBusy)return; corporationPropertyBusy=true; const y=scrollY26();
    try{const [fresh,catalog]=await Promise.all([api('/api/state'),api('/api/real-estate')]);state=fresh;realEstateCache=catalog.properties||[];renderHeader();const p=realEstateCache.find(x=>String(x.id)===String(id));if(!p||p.owned)return;const price=Number(p.purchase_price),money=Number(state.player.money);if(money<price){modal('Недостаточно денег',`Не хватает ${fmt(price-money)}.`);return;}if(!await confirm26('Купить недвижимость',`${p.name} · ${fmt(price)}`,'Купить'))return;const r=await api(`/api/real-estate/${id}/buy`,{method:'POST'});state=r.state;realEstateCache=r.properties;renderHeader();if(page==='realestate')openCity(p.city_id);restoreScroll26(y);modal('Недвижимость куплена',`Доход: ${fmt(realEstateCache.find(x=>x.id===id)?.rent_hour)}/ч.`)}catch(e){modal('Покупка не выполнена',e.message)}finally{corporationPropertyBusy=false;restoreScroll26(y)}
  };
  window.buyProperty=buyProperty;
  const baseUpgradeProperty26=window.upgradeProperty;
  if(baseUpgradeProperty26) window.upgradeProperty=(pid,uid)=>stable26(()=>baseUpgradeProperty26(pid,uid));
  sellProperty=async function(id){const y=scrollY26(),p=(realEstateCache||[]).find(x=>String(x.id)===String(id));if(!p?.owned)return;if(!await confirm26('Продать недвижимость',`${p.name} · ${fmt(p.sell_price)}`,'Продать'))return;try{const r=await api(`/api/real-estate/${id}/sell`,{method:'POST'});state=r.state;realEstateCache=r.properties;renderHeader();const next=realEstateCache.find(x=>String(x.id)===String(id));if(page==='realestate'&&next)openCity(next.city_id);restoreScroll26(y);modal('Недвижимость продана',`Получено ${fmt(r.sell_price)}.`)}catch(e){modal('Продажа не выполнена',e.message)}finally{restoreScroll26(y)}};
  window.sellProperty=sellProperty;

  // --- Exact countdowns. Absolute server time avoids cumulative setInterval drift. ---
  function serverNow26(){const server=Number(state?.server_time||0);if(!server)return Date.now()/1000;if(!window.__serverOffset26)window.__serverOffset26=server-Date.now()/1000;return Date.now()/1000+window.__serverOffset26;}
  function clock26(sec){sec=Math.max(0,Math.ceil(Number(sec)||0));const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60),s=sec%60;return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;}
  function tickTimers26(){
    const now=serverNow26(),whole=Math.floor(now);if(whole===lastTimerSecond26)return;lastTimerSecond26=whole;
    document.querySelectorAll('[data-fleet-until]').forEach(el=>{const until=Number(el.dataset.fleetUntil||0),left=until-now,b=el.querySelector('b');if(b)b.textContent=clock26(left);if(left<=0&&!el.dataset.completed26){el.dataset.completed26='1';const y=scrollY26();setTimeout(async()=>{try{state=await api('/api/state');renderHeader();if(page==='businesses')renderBusinesses();restoreScroll26(y);}catch(_){}},120);}});
    document.querySelectorAll('[data-tax-until]').forEach(el=>{const until=Number(el.dataset.taxUntil||0),left=until-now;el.textContent=clock26(left);if(left<=0&&!el.dataset.completed26){el.dataset.completed26='1';const y=scrollY26();setTimeout(async()=>{try{state=await api('/api/state');renderHeader();if(page==='taxes')renderTaxes();restoreScroll26(y);}catch(_){}},120);}});
    document.querySelectorAll('[data-realtime-until]').forEach(el=>{const until=Number(el.dataset.realtimeUntil||0);el.textContent=clock26(until-now);});
    document.querySelectorAll('[data-impact-at]').forEach(el=>{const until=Number(el.dataset.impactAt||0),left=until-now;el.textContent=clock26(left);if(left<=0&&!el.dataset.completed26){el.dataset.completed26='1';const y=scrollY26();setTimeout(async()=>{try{if(page==='investments'&&investmentView==='news')await renderMarketNews();restoreScroll26(y);}catch(_){}},250);}});
  }
  window.setInterval(tickTimers26,250);document.addEventListener('visibilitychange',()=>{if(!document.hidden){lastTimerSecond26=-1;tickTimers26();}});

  renderTaxes=function(){const t=state?.taxes||{},u=Number(t.unpaid||0),b=Boolean(t.blocked),until=Number(state?.server_time||Math.floor(Date.now()/1000))+Number(t.seconds_left||0);document.querySelector('#content').innerHTML=`<section class="tax-page"><article class="tax-hero ${b?'tax-blocked':''}"><div class="eyebrow">НАЛОГОВАЯ СИСТЕМА</div><h2>${gameIcon25(b?'clock':'money')} ${b?'Доход остановлен':'Налоги'}</h2><p>Налог — 5% с автоматического дохода, дивидендов, дохода по облигациям, аренды и прибыли от продажи акций.</p></article><article class="stats-card"><span>Неоплаченный налог</span><b>${fmt(u)}</b></article><article class="card tax-info">${u>0?(b?'Срок оплаты истёк. Весь пассивный доход остановлен.':`До остановки дохода: <b data-tax-until="${until}">${clock26(t.seconds_left)}</b>.`):'Задолженности нет.'}</article><button class="buy" ${u>0?'':'disabled'} onclick="payTaxes()">${u>0?`Оплатить ${fmt(u)}`:'Налогов к оплате нет'}</button></section>`;tickTimers26();};
  window.renderTaxes=renderTaxes;
  const basePayTaxes26=window.payTaxes; if(basePayTaxes26) window.payTaxes=()=>stable26(()=>basePayTaxes26());

  // Replace coarse garage text immediately after every business rerender.
  const baseRenderBusinesses26=window.renderBusinesses;
  renderBusinesses=function(){const r=baseRenderBusinesses26();tickTimers26();return r;}; window.renderBusinesses=renderBusinesses;

  // --- Real company logos on stock list/detail + restored Stocks icon. ---
  function logoImg26(id,label){const src=LOGO[String(id)]||'',fallback=String(label||id||'?').slice(0,2).toUpperCase().replace(/[<&]/g,'');return src?`<img class="company-logo26" src="${src}" alt="${String(label||id).replace(/"/g,'&quot;')}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='block'"><span class="logo-fallback26" style="display:none">${fallback}</span>`:'';}
  function enhanceLogos26(root=document){
    root.querySelectorAll('.corp-stock-row').forEach(row=>{const m=(row.getAttribute('onclick')||'').match(/openStock\(['\"]([^'\"]+)/);if(!m)return;const icon=row.querySelector('.corp-stock-icon');if(icon&&!icon.querySelector('img'))icon.innerHTML=logoImg26(m[1],m[1])||icon.innerHTML;});
    const big=root.querySelector('.corp-stock-logo-large');if(big&&corporationActiveStockId&&!big.querySelector('img'))big.innerHTML=logoImg26(corporationActiveStockId,corporationActiveStockId)||big.innerHTML;
    root.querySelectorAll('.investment-market-button').forEach(btn=>{if((btn.textContent||'').includes('Акции')){const i=btn.querySelector('.investment-market-icon');if(i)i.innerHTML=gameIcon25('chart');}});
  }
  const obs26=new MutationObserver(m=>{if(m.some(x=>x.addedNodes.length))enhanceLogos26(document)});obs26.observe(document.body,{childList:true,subtree:true});enhanceLogos26(document);
  const baseOpenStock26=window.openStock; if(baseOpenStock26){openStock=async function(...args){const r=await baseOpenStock26(...args);enhanceLogos26(document);return r};window.openStock=openStock;}

  // --- Market news: exact live reaction countdown + official company photography. ---
  renderMarketNews=async function(){
    const c=document.querySelector('#content');c.innerHTML='<div class="empty">Загружаем новости рынка…</div>';
    try{
      const d=await api('/api/market-news'); if(page!=='investments'||investmentView!=='news')return;
      const cards=(d.news||[]).map(n=>{const cls=n.sentiment==='good'?'v21-good':'v21-bad',label=n.sentiment==='good'?'ПОЗИТИВНЫЙ СИГНАЛ':'НЕГАТИВНЫЙ СИГНАЛ',reaction=n.applied?`<div class="v21-news-reaction ${cls}"><b>Изменение: ${Number(n.impact_percent)>=0?'+':''}${Number(n.impact_percent).toFixed(2)}%</b> · ${fmt(n.price_before)} → ${fmt(n.price_after)}</div>`:`<div class="v21-news-reaction ${cls}"><b>${label}</b> · реакция через <span data-impact-at="${Number(n.impact_at||0)}">${clock26(n.seconds_to_impact)}</span></div>`;return `<article class="v21-news-card"><div class="news-photo-frame25"><img class="v21-news-photo" src="${n.photo}" alt="${escapeHTML(n.company)}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='/static/news/${n.stock_id}.webp'"></div><div class="v21-news-body"><div class="v21-news-kicker"><span>CORPORATION JOURNAL · ${escapeHTML(n.symbol)}</span><span>${v21Date(n.published_at)}</span></div><h3>${escapeHTML(n.title)}</h3><p>${escapeHTML(n.article)}</p>${reaction}</div></article>`}).join('');
      c.innerHTML=`<section class="v21-news-page"><div class="v21-news-head"><div><div class="eyebrow">MARKET NEWS</div><h2>${gameIcon25('news')} Новости рынка</h2></div><button class="back-button" onclick="v21BackInvestments()">← Назад</button></div><div class="v21-news-next">Вымышленные игровые события. Таймер реакции обновляется каждую секунду.</div>${cards||'<div class="empty">Новостей пока нет.</div>'}</section>`;tickTimers26();
    }catch(e){modal('Ошибка',e.message)}
  };window.renderMarketNews=renderMarketNews;

  // --- Statistics: historical income source chosen by the admin is visible here. ---
  renderStatistics=async function(){const c=document.querySelector('#content');c.innerHTML='<div class="empty">Загружаем статистику…</div>';try{const s=await api('/api/statistics'),sources=(s.income_sources||[]).filter(x=>Number(x.amount)>0),max=Math.max(1,...sources.map(x=>Number(x.amount||0)));c.innerHTML=`<section class="stats-page"><article class="stats-card">${gameIcon25('money')}<span>Общая прибыль</span><b>${fmt(s.total_earned)}</b></article><article class="stats-card">${gameIcon25('chart')}<span>Общие расходы</span><b>${fmt(s.total_spent)}</b></article><article class="stats-card">${gameIcon25('building')}<span>Куплено бизнесов</span><b>${s.companies_bought}</b></article><article class="stats-card">${gameIcon25('home')}<span>Куплено недвижимости</span><b>${s.properties_bought}</b></article>${sources.length?`<section class="chart-card income-source26"><h2>${gameIcon25('money')} Доход по источникам</h2>${sources.map(x=>`<div class="income-row26"><div><span>${escapeHTML(x.label)}</span><b>${fmt(x.amount)}</b></div><i><em style="width:${Math.max(3,Number(x.amount)/max*100)}%"></em></i></div>`).join('')}</section>`:''}<section class="chart-card"><h2>${gameIcon25('chart')} Прибыль по дням</h2>${renderProfitChart(s.daily_profit||[])}</section></section>`;}catch(e){modal('Ошибка',e.message)}};window.renderStatistics=renderStatistics;

  // Refresh button and periodic rerenders can no longer displace the viewport.
  const refreshButton=document.querySelector('.corp-v22-refresh');if(refreshButton)refreshButton.addEventListener('pointerdown',()=>{retainedScroll26=scrollY26()},{capture:true});
  window.addEventListener('scroll',()=>{if(document.querySelector('#action-modal26:not(.hidden)'))return;retainedScroll26=scrollY26();},{passive:true});
  tickTimers26();
})();
