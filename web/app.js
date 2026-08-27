const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); try { tg.setHeaderColor("bg_color"); tg.setBackgroundColor("bg_color"); } catch {} }
const DEV_ID = 999001;
let state = null;
let page = "businesses";
let stocksCache = [];
let brokerageCache = null;
let bondsCache = [];
let realEstateCache = [];
let worldMap = null;

function fmt(n) { return Number(n || 0).toLocaleString("ru-RU", {maximumFractionDigits: 2}) + " ₽"; }
function fmtNumber(n) { return Number(n || 0).toLocaleString("ru-RU", {maximumFractionDigits: 2}); }
function fmtPercent(n) { const v=Number(n||0); return (v>0?"+":"")+v.toFixed(2)+"%"; }
async function api(url, options={}) {
  const headers={...(options.headers||{})};
  if (tg?.initData) headers["X-Telegram-Init-Data"]=tg.initData; else headers["X-User-Id"]=String(DEV_ID);
  const res=await fetch(url,{...options,headers,cache:"no-store"});
  if(!res.ok){let d;try{d=await res.json()}catch{d={detail:"Ошибка сервера"}}throw new Error(d.detail||"Ошибка")}
  return res.json();
}
function modal(title,text){document.querySelector("#modalTitle").textContent=title;document.querySelector("#modalText").innerHTML=String(text).replace(/\n/g,"<br>");document.querySelector("#modal").classList.remove("hidden")}
document.querySelector("#modalClose").onclick=()=>document.querySelector("#modal").classList.add("hidden");
function businessCount(){return (state?.businesses||[]).filter(x=>Number(x.level)>0).length}
function renderHeader(){if(!state)return;document.querySelector("#corpName").textContent=state.player.corp_name;document.querySelector("#money").textContent=fmt(state.player.money);document.querySelector("#income").textContent=fmt(state.hourly_income)+"/ч";document.querySelector("#businessCount").textContent=businessCount();document.querySelector("#propertyCount").textContent=state.real_estate_count||0}

function renderBusinesses(){
  const html=(state.businesses||[]).map(b=>{
    const owned=Boolean(b.owned||Number(b.level)>0);
    const canBuy=Number(state.player.money)>=Number(b.purchase_cost||b.next_cost||0);
    return `<article class="card business-card">
      <div class="business-head">
        <div><h3>${b.name}</h3><p>${b.desc}</p></div>
        ${owned?`<b class="owned-badge">✅ Куплено</b>`:`<b>Новый</b>`}
      </div>
      <div class="business-income-box">
        <span>${owned?"Текущий доход":"После покупки"}</span>
        <b>${fmt(owned?b.current_income:b.income_after_purchase)}/ч</b>
      </div>
      ${owned?`
        <div class="business-upgrade-title">ПРОКАЧКА БИЗНЕСА</div>
        <div class="upgrade-grid">
          ${(b.upgrades||[]).map(u=>`
            <button class="upgrade-btn ${u.owned?"owned":""}" ${u.owned?"disabled":""}
              onclick="upgradeBusiness('${b.id}','${u.id}')">
              <b>${u.name}</b>
              <span>${u.owned?"Установлено":`+${u.income_bonus_percent}% к доходу · ${fmt(u.cost)}`}</span>
            </button>`).join("")}
        </div>
        <button class="sell-business" onclick="sellBusiness('${b.id}')">Продать за ${fmt(b.sell_price)}</button>
        <div class="business-capitalization">Капитализация: ${fmt(b.capitalization)} · продажа 30%</div>
      `:`
        <button class="buy" ${canBuy?"":"disabled"} onclick="buyBusiness('${b.id}')">
          Купить за ${fmt(b.purchase_cost||b.next_cost)}
        </button>
      `}
    </article>`;
  }).join("");
  document.querySelector("#content").innerHTML=`<div class="grid">${html}</div>`;
}

function renderProfitChart(data){if(!data?.length)return `<div class="empty">Пока нет прибыли.</div>`;const max=Math.max(...data.map(x=>Number(x.earned||0)),1);return `<div class="profit-chart">${data.map(x=>{const h=Math.max(6,Math.round(Number(x.earned||0)/max*100));const date=String(x.day||"").split("-").slice(1).join(".");return `<div class="chart-column"><div class="chart-value">${fmt(x.earned)}</div><div class="chart-bar" style="height:${h}%"></div><div class="chart-date">${date}</div></div>`}).join("")}</div>`}
async function renderStatistics(){const c=document.querySelector("#content");c.innerHTML=`<div class="empty">Загружаем статистику...</div>`;try{const s=await api("/api/statistics");c.innerHTML=`<section class="stats-page"><article class="stats-card"><span>💰 Общая прибыль</span><b>${fmt(s.total_earned)}</b></article><article class="stats-card"><span>💸 Общие расходы</span><b>${fmt(s.total_spent)}</b></article><article class="stats-card"><span>🏢 Куплено бизнесов</span><b>${s.companies_bought}</b></article><article class="stats-card"><span>🏠 Куплено недвижимости</span><b>${s.properties_bought}</b></article><section class="chart-card"><h2>📊 Прибыль по дням</h2>${renderProfitChart(s.daily_profit||[])}</section></section>`}catch(e){modal("Ошибка",e.message)}}
async function renderRating(){const c=document.querySelector("#content");c.innerHTML=`<div class="empty">Загружаем рейтинг...</div>`;try{const rows=await api("/api/rating");c.innerHTML=`<div class="grid">${rows.map((p,i)=>`<button class="card rank-button" onclick="openPlayerProfile(${p.user_id})"><div class="rank-num">#${i+1}</div><div><h3>${p.corp_name}</h3><p>💰 ${fmt(p.money)}</p></div></button>`).join("")}</div>`}catch(e){modal("Ошибка",e.message)}}
async function openPlayerProfile(id){const c=document.querySelector("#content");c.innerHTML=`<div class="empty">Загружаем профиль...</div>`;try{const p=await api(`/api/player/${id}`);const businesses=p.businesses?.length?p.businesses.map(b=>`<article class="profile-business"><div><h3>${b.name}</h3><p>${b.description}</p></div><b>ур. ${b.level}</b></article>`).join(""):`<div class="empty">Бизнесов пока нет.</div>`;c.innerHTML=`<section class="profile-page"><button class="back-button" onclick="backToRating()">← Назад к рейтингу</button><article class="profile-header"><div class="eyebrow">ПРОФИЛЬ ИГРОКА</div><h2>${p.player.corp_name}</h2><p>💰 Капитал: ${fmt(p.player.money)}</p><p>📈 Автодоход: ${fmt(p.hourly_income)}/ч</p></article><section class="profile-stats"><div><span>💰 Общая прибыль</span><b>${fmt(p.stats.total_earned)}</b></div><div><span>🏢 Бизнесы</span><b>${p.stats.companies_bought}</b></div><div><span>🏠 Недвижимость</span><b>${p.properties_bought}</b></div></section><section class="profile-businesses"><h2>🏢 Бизнесы</h2>${businesses}</section></section>`}catch(e){modal("Ошибка",e.message)}}
function backToRating(){page="rating";updateActiveTab();renderRating()}

async function loadStocks(){stocksCache=await api("/api/stocks");return stocksCache}
async function loadBrokerage(){brokerageCache=await api("/api/brokerage-account");return brokerageCache}
async function loadBonds(){const data=await api("/api/bonds");bondsCache=data.bonds||[];return bondsCache}
function getHolding(id){return (brokerageCache?.holdings||[]).find(x=>String(x.stock_id)===String(id))||null}
function stockChange(s){return Number(s.change_percent??0)}
function renderStockMiniChart(history){if(!history?.length)return `<div class="stock-chart-empty">История цены пока формируется</div>`;const prices=history.map(x=>Number(x.price||0)),min=Math.min(...prices),max=Math.max(...prices),range=max-min||1,w=360,h=120,labelW=78,plotW=w-labelW-8,top=8,ph=h-16,yFor=p=>top+ph-((p-min)/range*ph);const pts=prices.map((p,i)=>`${prices.length===1?plotW/2:i/(prices.length-1)*plotW},${yFor(p)}`).join(" "),cur=prices.at(-1),cy=yFor(cur),ly=Math.min(h-25,Math.max(3,cy-12));return `<div class="stock-chart"><svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><line x1="0" y1="${cy}" x2="${plotW}" y2="${cy}" class="stock-current-line"/><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${plotW}" cy="${cy}" r="4" class="stock-current-dot"/><rect x="${plotW+5}" y="${ly}" width="${labelW}" height="24" rx="4" class="stock-current-label-bg"/><text x="${plotW+11}" y="${ly+16}" class="stock-current-label">${fmtNumber(cur)} ₽</text></svg></div>`}
async function renderInvestments(){
  const c=document.querySelector("#content");
  c.innerHTML=`<div class="empty">Загружаем инвестиции...</div>`;
  try{
    const [stocks,broker,bonds]=await Promise.all([loadStocks(),loadBrokerage(),loadBonds()]);
    stocksCache=stocks; brokerageCache=broker; bondsCache=bonds;
    const profit=Number(broker.total_profit||0);
    const bondIncome=(bondsCache||[]).reduce((sum,b)=>sum+Number(b.income_hour||0),0);
    c.innerHTML=`<section class="investment-page">
      <article class="investment-summary">
        <div class="eyebrow">МОЙ БРОКЕРСКИЙ СЧЁТ</div>
        <h2>${fmt(broker.total_current_value)}</h2>
        <div class="investment-profit ${profit>=0?"positive":"negative"}">${profit>=0?"▲":"▼"} ${fmt(Math.abs(profit))} (${fmtPercent(broker.total_profit_percent)})</div>
        <div class="investment-summary-grid">
          <div><span>Дивиденды акций</span><b>${fmt(broker.dividend_hour)}/ч</b></div>
          <div><span>Доход облигаций</span><b>${fmt(bondIncome)}/ч</b></div>
        </div>
      </article>
      <div class="investment-section-title"><div><div class="eyebrow">ФОНДОВЫЙ РЫНОК</div><h2>📈 Акции</h2></div><button class="refresh-market" onclick="refreshInvestments()">↻</button></div>
      <div class="grid">${stocks.map(renderStockCard).join("")}</div>
      ${renderHoldings()}
      <div class="investment-section-title bond-section-title"><div><div class="eyebrow">ФИКСИРОВАННЫЙ ДОХОД</div><h2>🏦 Облигации</h2></div></div>
      <div class="grid">${bondsCache.map(renderBondCard).join("")}</div>
    </section>`;
  }catch(e){modal("Инвестиции",e.message)}
}
function renderStockCard(s){
  const h=getHolding(s.id),owned=Number(h?.quantity||0),change=stockChange(s);
  return `<article class="card stock-card">
    <div class="stock-header">
      <div><div class="stock-symbol">${s.symbol}</div><h3>${s.name}</h3></div>
      <div class="stock-price-block"><b class="stock-price">${fmt(s.current_price)}</b><span class="stock-change ${change>=0?"positive":"negative"}">${change>=0?"▲":"▼"} ${Math.abs(change).toFixed(2)}%</span></div>
    </div>
    <p>${s.description||""}</p>
    <div class="dividend-badge">💸 Дивиденды: ${s.dividend_rate_percent}% в час</div>
    <button class="stock-history-button" onclick="openStock('${s.id}')">📊 Открыть график</button>
    <div class="stock-position"><span>У тебя:</span><b>${owned} шт.</b></div>
    <div class="stock-actions"><button class="buy" onclick="openTrade('${s.id}','buy')">Купить</button><button class="stock-sell" ${owned>0?"":"disabled"} onclick="openTrade('${s.id}','sell')">Продать</button></div>
  </article>`;
}

function renderHoldings(){if(!brokerageCache?.holdings?.length)return `<article class="card empty">У тебя пока нет акций.</article>`;return `<section class="holdings-section"><h2>💼 Портфель</h2><div class="grid">${brokerageCache.holdings.map(h=>`<article class="card"><div class="business-head"><div><div class="stock-symbol">${h.symbol}</div><h3>${h.name}</h3></div><b>${h.quantity} шт.</b></div><div class="holding-row"><span>Стоимость</span><b>${fmt(h.current_value)}</b></div><div class="holding-row"><span>Дивиденды</span><b>${fmt(h.dividend_hour)}/ч</b></div><div class="holding-profit ${h.profit>=0?"positive":"negative"}">${h.profit>=0?"▲ Прибыль":"▼ Убыток"} ${fmt(Math.abs(h.profit))} (${fmtPercent(h.profit_percent)})</div></article>`).join("")}</div></section>`}
async function openStock(id){try{const s=await api(`/api/stocks/${id}`),h=getHolding(id),change=stockChange(s);document.querySelector("#modalTitle").textContent=`${s.symbol} — ${s.name}`;document.querySelector("#modalText").innerHTML=`<div class="stock-detail-price">${fmt(s.current_price)}</div><div class="${change>=0?"positive":"negative"}">${change>=0?"▲":"▼"} ${Math.abs(change).toFixed(2)}%</div><div class="dividend-badge">💸 ${s.dividend_rate_percent}% дивидендов в час</div>${renderStockMiniChart(s.history||[])}<p>У тебя: ${h?.quantity||0} шт.</p>`;document.querySelector("#modal").classList.remove("hidden")}catch(e){modal("Ошибка",e.message)}}
async function refreshInvestments(){state=await api("/api/state");renderHeader();await renderInvestments()}
async function openTrade(id,side){const s=stocksCache.find(x=>x.id===id);if(!s)return;const h=getHolding(id),owned=Number(h?.quantity||0),price=Number(s.current_price),max=side==="buy"?Math.floor(Number(state.player.money)/price):owned;if(max<=0){modal("Сделка","Недостаточно средств или акций.");return}const raw=prompt(`${side==="buy"?"Покупка":"Продажа"} ${s.name}\nЦена: ${fmt(price)}\nМаксимум: ${max} шт.\nВведите количество:`,"1");if(raw===null)return;const qty=parseInt(raw,10);if(!Number.isInteger(qty)||qty<=0||qty>max){modal("Ошибка",`Введите целое число от 1 до ${max}.`);return}try{const r=await api(`/api/stocks/${id}/${side}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({quantity:qty})});state=r.state;renderHeader();await renderInvestments();modal(side==="buy"?"Акции куплены":"Акции проданы",side==="sell"&&r.realized_profit>0?`Прибыль сделки: ${fmt(r.realized_profit)}\nНалог с прибыли: ${fmt(r.profit_tax)}`:`Сумма сделки: ${fmt(side==="buy"?r.total_cost:r.total_income)}`)}catch(e){modal("Сделка не выполнена",e.message)}}

function renderBondCard(b){
  const owned=Number(b.quantity||0);
  return `<article class="card bond-card">
    <div class="business-head"><div><div class="stock-symbol">${b.symbol}</div><h3>${b.name}</h3><p>${b.description}</p></div><b>${fmt(b.price)}</b></div>
    <div class="bond-yield">💰 Доходность: <b>${b.yield_rate_percent}% в час</b></div>
    <div class="holding-row"><span>У тебя</span><b>${owned} шт.</b></div>
    <div class="holding-row"><span>Доход</span><b>${fmt(b.income_hour)}/ч</b></div>
    <div class="stock-actions"><button class="buy" onclick="openBondTrade('${b.id}','buy')">Купить</button><button class="stock-sell" ${owned>0?"":"disabled"} onclick="openBondTrade('${b.id}','sell')">Продать</button></div>
  </article>`;
}
async function openBondTrade(id,side){
  const b=bondsCache.find(x=>x.id===id); if(!b)return;
  const price=Number(b.price||0), owned=Number(b.quantity||0);
  const max=side==="buy"?Math.floor(Number(state.player.money||0)/price):owned;
  if(max<=0){modal("Облигации",side==="buy"?"Недостаточно денег для покупки.":"У тебя нет этих облигаций.");return}
  const raw=prompt(`${side==="buy"?"Покупка":"Продажа"} ${b.symbol}
Цена: ${fmt(price)}
Доходность: ${b.yield_rate_percent}%/ч
Максимум: ${max} шт.
Введите количество:`,"1");
  if(raw===null)return;
  const qty=parseInt(raw,10);
  if(!Number.isInteger(qty)||qty<=0||qty>max){modal("Ошибка",`Введите целое число от 1 до ${max}.`);return}
  try{
    const r=await api(`/api/bonds/${id}/${side}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({quantity:qty})});
    state=r.state; bondsCache=r.bonds||await loadBonds(); renderHeader(); await renderInvestments();
    modal(side==="buy"?"Облигации куплены":"Облигации проданы",`Количество: ${qty} шт.
Сумма: ${fmt(side==="buy"?r.total_cost:r.total_income)}`);
  }catch(e){modal("Операция не выполнена",e.message)}
}

function formatTaxTime(sec){const t=Math.max(0,Number(sec||0)),h=Math.floor(t/3600),m=Math.floor((t%3600)/60);return `${h} ч ${m} мин`}
function renderTaxes(){const t=state?.taxes||{},u=Number(t.unpaid||0),b=Boolean(t.blocked);document.querySelector("#content").innerHTML=`<section class="tax-page"><article class="tax-hero ${b?"tax-blocked":""}"><div class="eyebrow">НАЛОГОВАЯ СИСТЕМА</div><h2>${b?"⛔ Доход остановлен":"🧾 Налоги"}</h2><p>Налог — 5% с автоматического дохода, дивидендов, дохода по облигациям, аренды и прибыли от продажи акций.</p></article><article class="stats-card"><span>Неоплаченный налог</span><b>${fmt(u)}</b></article><article class="card tax-info">${u>0?(b?"Срок оплаты истёк. Весь пассивный доход остановлен.":`До остановки дохода: <b>${formatTaxTime(t.seconds_left)}</b>.`):"Задолженности нет."}</article><button class="buy" ${u>0?"":"disabled"} onclick="payTaxes()">${u>0?`Оплатить ${fmt(u)}`:"Налогов к оплате нет"}</button></section>`}
async function payTaxes(){try{const r=await api("/api/taxes/pay",{method:"POST"});state=r.state;renderHeader();renderTaxes();modal("Налог оплачен",`Оплачено ${fmt(r.paid)}.`)}catch(e){modal("Не удалось оплатить",e.message)}}

async function renderRealEstate(){const c=document.querySelector("#content");c.innerHTML=`<div class="empty">Загружаем карту...</div>`;try{const d=await api("/api/real-estate");realEstateCache=d.properties||[];c.innerHTML=`<section class="realestate-page"><div><div class="eyebrow">МИРОВАЯ НЕДВИЖИМОСТЬ</div><h2>🌍 Карта мира</h2><p class="section-note">Приближай карту и нажимай на маркеры городов.</p></div><div id="worldMap" class="world-map"></div><div class="realestate-summary"><span>🏠 Куплено объектов</span><b>${state.real_estate_count||0}</b><span>📈 Рост цены</span><b>+0,5% в сутки</b></div></section>`;setTimeout(initWorldMap,0)}catch(e){modal("Недвижимость",e.message)}}
function initWorldMap(){
  if(worldMap){worldMap.remove();worldMap=null}
  if(!window.L)return modal("Карта","Не удалось загрузить карту.");

  worldMap=L.map("worldMap",{
    worldCopyJump:true,
    minZoom:2,
    maxZoom:18,
    zoomControl:false,
    attributionControl:false
  }).setView([30,15],2);

  L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
    {
      subdomains:"abcd",
      maxZoom:20
    }
  ).addTo(worldMap);

  const controls=L.control({position:"topright"});
  controls.onAdd=()=>{
    const box=L.DomUtil.create("div","game-map-controls");
    box.innerHTML=`<button type="button" data-map-zoom="in">＋</button><button type="button" data-map-zoom="out">−</button>`;
    L.DomEvent.disableClickPropagation(box);
    box.querySelector('[data-map-zoom="in"]').onclick=()=>worldMap.zoomIn();
    box.querySelector('[data-map-zoom="out"]').onclick=()=>worldMap.zoomOut();
    return box;
  };
  controls.addTo(worldMap);

  const credits=L.control({position:"bottomright"});
  credits.onAdd=()=>{
    const el=L.DomUtil.create("div","game-map-credits");
    el.innerHTML='© OpenStreetMap · © CARTO';
    return el;
  };
  credits.addTo(worldMap);

  const seen=new Set();
  realEstateCache.forEach(p=>{
    if(seen.has(p.city_id))return;
    seen.add(p.city_id);
    const icon=L.divIcon({
      className:"game-city-marker-wrap",
      html:`<div class="game-city-marker"><span></span></div><div class="game-city-name">${p.city}</div>`,
      iconSize:[120,48],
      iconAnchor:[60,22]
    });
    L.marker([p.lat,p.lng],{icon})
      .addTo(worldMap)
      .on("click",()=>openCity(p.city_id));
  });

  setTimeout(()=>worldMap.invalidateSize(),150);
}
function openCity(cityId){const props=realEstateCache.filter(p=>p.city_id===cityId);if(!props.length)return;const city=props[0].city;document.querySelector("#content").innerHTML=`<section class="realestate-page"><button class="back-button" onclick="renderRealEstate()">← Назад к карте</button><div class="eyebrow">${props[0].country}</div><h2>🏙 ${city}</h2><div class="grid">${props.map(renderPropertyCard).join("")}</div></section>`}
function propertyFallbackImage(p){
  const city=String(p.city||"Corporation").replace(/[<>&"']/g,"");
  const title=String(p.name||"Недвижимость").replace(/[<>&"']/g,"");
  const isHouse=p.property_type==="house";
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" viewBox="0 0 1200 700"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#10251d"/><stop offset="1" stop-color="#244f3c"/></linearGradient></defs><rect width="1200" height="700" fill="url(#g)"/><circle cx="960" cy="120" r="210" fill="#4ecb8120"/><rect x="145" y="185" width="910" height="360" rx="28" fill="#0b1512" stroke="#66d694" stroke-opacity=".35" stroke-width="4"/><text x="600" y="340" text-anchor="middle" font-family="Arial,sans-serif" font-size="118">${isHouse?"🏡":"🏙️"}</text><text x="600" y="430" text-anchor="middle" fill="#eef8f1" font-family="Arial,sans-serif" font-size="46" font-weight="700">${city}</text><text x="600" y="485" text-anchor="middle" fill="#9ac8aa" font-family="Arial,sans-serif" font-size="30">${title}</text><text x="600" y="620" text-anchor="middle" fill="#78b78f" font-family="Arial,sans-serif" font-size="22">Corporation · изображение временно недоступно</text></svg>`;
  return "data:image/svg+xml;charset=UTF-8,"+encodeURIComponent(svg);
}
function renderPropertyCard(p){
  const segmentNames={economy:"Эконом",business:"Бизнес",vip:"VIP"};
  const typeNames={apartment:"Квартира",house:"Дом"};
  return `<article class="card property-card">
    <div class="property-image-wrap">
      <img src="${p.photo}" alt="${p.name}" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src=propertyFallbackImage(p)">
      <div class="property-badges"><span class="segment-${p.segment||"economy"}">${segmentNames[p.segment]||"Эконом"}</span><span>${typeNames[p.property_type]||""}</span></div>
    </div>
    <div class="property-body">
      <div class="business-head"><div><h3>${p.name}</h3><p>${p.description}</p></div>${p.owned?"<b>✅ Куплено</b>":""}</div>
      <div class="property-metrics"><div><span>${p.owned?"Текущая стоимость":"Цена"}</span><b>${fmt(p.current_value)}</b></div><div><span>Аренда</span><b>${fmt(p.rent_hour)}/ч</b></div></div>
      ${p.owned?`<div class="property-growth">📈 Стоимость растёт на 0,5% в сутки от цены покупки</div><div class="upgrade-grid">${p.upgrades.map(u=>`<button class="upgrade-btn ${u.owned?"owned":""}" ${u.owned?"disabled":""} onclick="upgradeProperty('${p.id}','${u.id}')"><b>${u.name}</b><span>${u.owned?"Установлено":`+${u.income_bonus_percent}% к аренде · ${fmt(u.cost)}`}</span></button>`).join("")}</div>`:`<button class="buy" onclick="buyProperty('${p.id}')">Купить за ${fmt(p.purchase_price)}</button>`}
    </div>
  </article>`;
}

async function buyProperty(id){if(!confirm("Купить эту недвижимость?"))return;try{const r=await api(`/api/real-estate/${id}/buy`,{method:"POST"});state=r.state;realEstateCache=r.properties;renderHeader();const p=realEstateCache.find(x=>x.id===id);openCity(p.city_id);modal("Недвижимость куплена",`Теперь она приносит ${fmt(p.rent_hour)}/ч автоматически.`)}catch(e){modal("Покупка не выполнена",e.message)}}
async function upgradeProperty(pid,uid){try{const r=await api(`/api/real-estate/${pid}/upgrade/${uid}`,{method:"POST"});state=r.state;realEstateCache=r.properties;renderHeader();const p=realEstateCache.find(x=>x.id===pid);openCity(p.city_id);modal("Улучшение установлено",`Новая аренда: ${fmt(p.rent_hour)}/ч.`)}catch(e){modal("Улучшение не выполнено",e.message)}}

function render(){renderHeader();if(page==="businesses")return renderBusinesses();if(page==="investments")return renderInvestments();if(page==="realestate")return renderRealEstate();if(page==="taxes")return renderTaxes();if(page==="statistics")return renderStatistics();if(page==="rating")return renderRating()}
function updateActiveTab(){document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.page===page))}
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{page=b.dataset.page;updateActiveTab();render()});
window.buyBusiness=async id=>{try{state=await api(`/api/business/${id}/buy`,{method:"POST"});render()}catch(e){modal("Не удалось",e.message)}};
window.upgradeBusiness=async(id,upgradeId)=>{try{state=await api(`/api/business/${id}/upgrade/${upgradeId}`,{method:"POST"});render();modal("Бизнес прокачан","Доход бизнеса увеличен.")}catch(e){modal("Прокачка не выполнена",e.message)}};
window.sellBusiness=async id=>{const b=(state.businesses||[]).find(x=>x.id===id);if(!b||!confirm(`Продать ${b.name} за ${fmt(b.sell_price)}?`))return;try{const r=await api(`/api/business/${id}/sell`,{method:"POST"});state=r.state;render();modal("Бизнес продан",`Получено ${fmt(r.sell_price)}.`)}catch(e){modal("Ошибка",e.message)}};
document.querySelector("#renameBtn").onclick=async()=>{if(!state)return;const name=prompt("Новое название корпорации:",state.player.corp_name);if(!name)return;try{state=await api("/api/rename",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});render()}catch(e){modal("Ошибка",e.message)}};
Object.assign(window,{openPlayerProfile,backToRating,openStock,openTrade,openBondTrade,refreshInvestments,payTaxes,renderRealEstate,openCity,buyProperty,upgradeProperty});
async function refresh(){try{state=await api("/api/state");updateActiveTab();render()}catch(e){console.error(e);modal("Ошибка запуска",e.message)}}
refresh();
setInterval(async()=>{try{state=await api("/api/state");renderHeader();if(page==="taxes")renderTaxes()}catch{}},60000);
