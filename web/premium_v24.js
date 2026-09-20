/* Corporation 24 — premium interface, one source of prices and balances. */
function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
const reducedMotion=()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
function syncBuyAll(){
  if(!state)return;
  for(const btn of document.querySelectorAll('[data-buy-stock],[data-buy-bond]')){
    const id=btn.dataset.buyStock||btn.dataset.buyBond;
    const stock=Boolean(btn.dataset.buyStock);
    const item=(stock?stocksCache:bondsCache).find(x=>String(x.id)===id);
    if(!item)continue;
    const price=Number(stock?item.current_price:item.price);
    const max=price>0?Math.floor(Number(state.player.money)/price):0;
    const label=`Купить на все · ${max} шт.`;
    if(btn.textContent!==label)btn.textContent=label;
    btn.disabled=max<=0;
  }
}
const originalHeader24=renderHeader;
renderHeader=function(){originalHeader24();syncBuyAll();};
const buyObserver=new MutationObserver(syncBuyAll);
buyObserver.observe(document.querySelector('#content'),{childList:true,subtree:true});

function configureTelegram24(){
  if(!tg)return;
  const insets=()=>{
    for(const side of ['top','right','bottom','left']){
      const value=(tg.safeAreaInset?.[side]||0)+(tg.contentSafeAreaInset?.[side]||0);
      document.documentElement.style.setProperty(`--game-safe-${side}`,`${value}px`);
    }
  };
  try{tg.setHeaderColor('#0c1015');tg.setBackgroundColor('#0c1015');}catch{}
  if(tg.isVersionAtLeast?.('8.0')){
    for(const event of ['safeAreaChanged','contentSafeAreaChanged','fullscreenChanged'])tg.onEvent(event,insets);
    tg.onEvent('fullscreenFailed',()=>tg.expand());
    try{if(!tg.isFullscreen)tg.requestFullscreen();}catch{tg.expand();}
  }
  insets();
}
configureTelegram24();

let ratingRows24=[];
renderRating=async function(){
  const c=document.querySelector('#content');
  c.innerHTML='<div class="empty">Загружаем рейтинг…</div>';
  try{
    const rows=await api('/api/rating');if(page!=='rating')return;
    ratingRows24=rows;
    const mine=rows.findIndex(p=>Number(p.user_id)===Number(state.player.user_id));
    c.innerHTML=`<section class="rating-page"><div class="section-top"><div><div class="eyebrow">ТАБЛИЦА ЛИДЕРОВ</div><h2>Рейтинг корпораций</h2></div><span class="rank-count">${rows.length} компаний</span></div><div class="rank-summary">${mine>=0?`Твоё место <strong>#${mine+1}</strong>`:'Твоей компании пока нет в рейтинге'}<span>По полной капитализации</span></div><div class="grid">${rows.map((p,i)=>`<button id="rank-${i}" class="card rank-button ${i===mine?'rank-mine':''}" onclick="openPlayerProfile(${Number(p.user_id)})"><div class="rank-num">${String(i+1).padStart(2,'0')}</div><div><h3>${escapeHTML(p.corp_name)}${i===mine?'<small>ТЫ</small>':''}</h3><p>${fmt(p.capital)}</p><small>Свободно ${fmt(p.money)}</small></div></button>`).join('')}</div><div class="rank-jump"><button onclick="jumpRating24(0)" aria-label="В начало рейтинга">↑ Вверх</button><button onclick="jumpRating24(${mine})" ${mine<0?'disabled':''}>◎ Моё место</button></div></section>`;
    requestAnimationFrame(()=>jumpRating24(mine,false));
  }catch(e){modal('Рейтинг',e.message);}
};
function jumpRating24(index,smooth=true){document.querySelector(`#rank-${index}`)?.scrollIntoView({block:'center',behavior:smooth&&!reducedMotion()?'smooth':'instant'});}
window.renderRating=renderRating;window.jumpRating24=jumpRating24;

// Interactive offline atlas; preserve camera when returning from a city.
let mapView241=null,atlas241=null;
function disposeAtlas241(){if(atlas241){mapView241=atlas241.snapshot();atlas241.destroy();atlas241=null;}}
renderRealEstate=async function(){
  disposeAtlas241();const c=document.querySelector('#content');c.innerHTML='<div class="empty">Загружаем объекты…</div>';
  try{
    const d=await api('/api/real-estate');if(page!=='realestate')return;
    realEstateCache=d.properties||[];
    const cities=[...new Map(realEstateCache.map(p=>[p.city_id,p])).values()];
    c.innerHTML=`<section class="realestate-page"><div class="eyebrow">ЧАСТНЫЙ ПОРТФЕЛЬ</div><h2>Недвижимость мира</h2><p class="section-note">Найди место для следующей инвестиции.</p><div class="interactive-atlas"></div><p class="map-gesture-note">Перетаскивай карту • Приближай двумя пальцами или колёсиком<br>Нажми на метку, чтобы открыть город. Число на метке — группа городов.</p><p class="section-note map-catalog-heading">Все города</p><div class="city-selector">${cities.map(p=>`<button data-city="${p.city_id}" onclick="openCity('${p.city_id}')"><span>${escapeHTML(p.country)}</span><strong>${escapeHTML(p.city)}</strong><b>↗</b></button>`).join('')}</div><div class="realestate-summary"><span>В портфеле</span><b>${state.real_estate_count||0} объектов</b><span>Рост стоимости</span><b>+1% каждые 12 ч</b></div></section>`;
    atlas241=new CorporationAtlas(c.querySelector('.interactive-atlas'),cities,{saved:mapView241,onSelect:id=>openCity(id),onChange:view=>mapView241=view});
  }catch(e){modal('Недвижимость',e.message);}
};
const originalOpenCity241=openCity;
openCity=function(id){disposeAtlas241();originalOpenCity241(id);};
function zoomMap24(delta){if(atlas241){if(delta===0)atlas241.reset();else atlas241.zoom(atlas241.scale*(delta>0?1.5:1/1.5));}}
window.renderRealEstate=renderRealEstate;window.openCity=openCity;window.zoomMap24=zoomMap24;
// Animate actual navigation once, not every background balance update.
for(const button of document.querySelectorAll('.tab')){
  const previous=button.onclick;
  button.onclick=()=>{
    disposeAtlas241();previous();button.scrollIntoView({block:'nearest',inline:'nearest'});
    if(!reducedMotion())document.querySelector('#content').animate([{opacity:.35,transform:'translateY(6px)'},{opacity:1,transform:'translateY(0)'}],{duration:220,easing:'cubic-bezier(.2,.8,.2,1)'});
  };
}

let refreshing24=false;
async function liveRefresh24(){
  if(document.hidden||refreshing24||corporationTradeBusy)return;
  const savedScroll=window.scrollY||0;
  refreshing24=true;
  try{
    state=await api('/api/state');renderHeader();
    if(page==='investments'&&corporationActiveStockId)await openStock(corporationActiveStockId,true);
    else if(page==='taxes')await renderTaxes();
  }catch{}finally{requestAnimationFrame(()=>window.scrollTo({top:savedScroll,left:0,behavior:'instant'}));refreshing24=false;}
}
setInterval(liveRefresh24,15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)liveRefresh24();});
function businessIcon24(id){
 const paths={coffee:'M5 7h12v7a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5V7ZM17 8h2a3 3 0 0 1 0 6h-2M8 3v1M12 3v1M4 22h15',delivery:'M3 6h11v12H3ZM14 10h4l3 4v4h-7M6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',factory:'M3 21V10l6 3V8l6 4V3h4l2 18H3ZM7 17h1M12 17h1M17 17h1',it:'M3 4h18v13H3ZM8 21h8M12 17v4M9 8l-3 3 3 3M15 8l3 3-3 3',finance:'M3 9l9-6 9 6H3ZM5 11v8M10 11v8M14 11v8M19 11v8M3 22h18',conglomerate:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM3 12h18M12 3c-6 6-6 12 0 18M12 3c6 6 6 12 0 18'};
 return `<span class="business-icon24"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[id]||paths.finance}"/></svg></span>`;
}
