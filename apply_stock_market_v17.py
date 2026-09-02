from pathlib import Path
from datetime import datetime
import re, shutil, sys

ROOT=Path(__file__).resolve().parent
JS=ROOT/"web"/"app.js"
CSS=ROOT/"web"/"style.css"
INDEX=ROOT/"web"/"index.html"
BOT=ROOT/"bot.py"

for p in (JS,CSS,INDEX):
    if not p.exists():
        raise RuntimeError(f"Не найден {p}. Запусти файл из корня проекта.")

def backup(p):
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    dst=p.with_name(p.name+f".backup_v17_{stamp}")
    shutil.copy2(p,dst)

def strip_block(text,a,b):
    while a in text and b in text:
        i=text.index(a); j=text.index(b,i)+len(b)
        text=text[:i]+text[j:]
    return text

JS_BLOCK=r"""
/* === CORPORATION_STOCK_MARKET_V17 === */
let corporationStockViewMode="line";
let corporationStockReturnScroll=0;
let corporationActiveStockId=null;

function corporationBuildCandles(history,size=5){
  const points=(history||[]).map(x=>({price:Number(x.price||0),created_at:Number(x.created_at||0)})).filter(x=>Number.isFinite(x.price));
  const out=[];
  for(let i=0;i<points.length;i+=size){
    const c=points.slice(i,i+size);
    if(!c.length)continue;
    const p=c.map(x=>x.price);
    out.push({open:p[0],close:p[p.length-1],high:Math.max(...p),low:Math.min(...p),created_at:c[c.length-1].created_at});
  }
  return out;
}

function corporationRenderChart(history,mode=corporationStockViewMode){
  const rows=(history||[]).map(x=>({price:Number(x.price||0),created_at:Number(x.created_at||0)})).filter(x=>Number.isFinite(x.price));
  if(rows.length<2)return `<div class="corp-stock-chart-empty">История цены пока формируется</div>`;

  const prices=rows.map(x=>x.price), visibleMax=Math.max(...prices), visibleMin=Math.min(...prices);
  const spread=Math.max(visibleMax-visibleMin,Math.max(visibleMax,1)*0.004), pad=spread*.12;
  const chartMin=visibleMin-pad, chartMax=visibleMax+pad, range=chartMax-chartMin||1;
  const W=820,H=390,L=56,R=105,T=20,B=38,PW=W-L-R,PH=H-T-B;
  const y=p=>T+PH-((p-chartMin)/range)*PH;
  const x=(i,n)=>L+(n<=1?PW/2:(i/(n-1))*PW);

  const maxY=y(visibleMax),minY=y(visibleMin),last=prices.at(-1),lastY=y(last);

  let series="";
  if(mode==="candles"){
    const candles=corporationBuildCandles(rows,5),slot=PW/Math.max(candles.length,1),bw=Math.max(4,Math.min(15,slot*.52));
    series=candles.map((c,i)=>{
      const cx=L+(i+.5)*slot,yo=y(c.open),yc=y(c.close),yh=y(c.high),yl=y(c.low),up=c.close>=c.open;
      return `<line x1="${cx}" y1="${yh}" x2="${cx}" y2="${yl}" class="corp-candle-wick ${up?"up":"down"}"/>
      <rect x="${cx-bw/2}" y="${Math.min(yo,yc)}" width="${bw}" height="${Math.max(2,Math.abs(yc-yo))}" rx="2" class="corp-candle-body ${up?"up":"down"}"/>`;
    }).join("");
  }else{
    const pts=prices.map((p,i)=>`${x(i,prices.length)},${y(p)}`).join(" ");
    series=`<polygon points="${L},${T+PH} ${pts} ${L+PW},${T+PH}" class="corp-stock-area"/>
    <polyline points="${pts}" class="corp-stock-line"/>`;
  }

  const guideVals=[chartMax-pad*.25,visibleMax-(visibleMax-visibleMin)*.33,visibleMin+(visibleMax-visibleMin)*.33,chartMin+pad*.25];
  const guides=guideVals.map(v=>`<line x1="${L}" y1="${y(v)}" x2="${L+PW}" y2="${y(v)}" class="corp-chart-grid"/>
  <text x="${L-7}" y="${y(v)+4}" text-anchor="end" class="corp-chart-axis">${fmtNumber(v)}</text>`).join("");

  const labels=[];
  const count=Math.min(5,rows.length);
  for(let k=0;k<count;k++){
    const idx=Math.round(k*(rows.length-1)/(count-1));
    const ts=rows[idx]?.created_at;
    let label="";
    if(ts)label=new Date(ts*1000).toLocaleTimeString("ru-RU",{hour:"2-digit",minute:"2-digit"});
    labels.push(`<text x="${x(idx,rows.length)}" y="${H-7}" text-anchor="${k===0?"start":k===count-1?"end":"middle"}" class="corp-chart-time">${label}</text>`);
  }

  return `<div class="corp-stock-chart"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    ${guides}
    <line x1="${L}" y1="${maxY}" x2="${L+PW}" y2="${maxY}" class="corp-extreme-line"/>
    <text x="${L+PW+8}" y="${maxY+4}" class="corp-extreme-label">MAX ${fmtNumber(visibleMax)}</text>
    <line x1="${L}" y1="${minY}" x2="${L+PW}" y2="${minY}" class="corp-extreme-line"/>
    <text x="${L+PW+8}" y="${minY+4}" class="corp-extreme-label">MIN ${fmtNumber(visibleMin)}</text>
    ${series}
    <line x1="${L}" y1="${lastY}" x2="${L+PW}" y2="${lastY}" class="corp-current-price-line"/>
    <circle cx="${L+PW}" cy="${lastY}" r="4" class="corp-current-dot"/>
    ${labels.join("")}
  </svg></div>`;
}

renderStockMiniChart=function(history){return corporationRenderChart(history,"line")};

renderStockCard=function(stock){
  const change=Number(stock.change_percent||0),owned=Number(getHolding(stock.id)?.quantity||0);
  return `<button class="corp-stock-row" type="button" onclick="openStock('${stock.id}')">
    <div class="corp-stock-icon">${String(stock.symbol||stock.name||"?").slice(0,2).toUpperCase()}</div>
    <div class="corp-stock-name"><strong>${stock.name}</strong><span>${owned>0?`В портфеле · ${owned} шт.`:"Доступно"}</span></div>
    <div class="corp-stock-quote"><strong>${fmt(stock.current_price)}</strong><span class="${change>=0?"positive":"negative"}">${change>=0?"+":"−"} ${Math.abs(change).toFixed(2)}%</span></div>
    <span class="corp-stock-arrow">›</span>
  </button>`;
};

openStock=async function(id,keepScroll=false){
  const c=document.querySelector("#content");
  if(!keepScroll)corporationStockReturnScroll=window.scrollY||0;
  corporationActiveStockId=String(id);
  c.innerHTML=`<div class="empty">Загружаем акцию...</div>`;
  try{
    const s=await api(`/api/stocks/${id}`),h=getHolding(id),owned=Number(h?.quantity||0),change=Number(s.change_percent||0);
    stocksCache=stocksCache.map(x=>String(x.id)===String(s.id)?{...x,...s}:x);
    c.innerHTML=`<section class="corp-stock-page">
      <div class="corp-stock-page-top"><button class="corp-stock-back" onclick="corporationCloseStock()">←</button></div>
      <div class="corp-stock-company">
        <div class="corp-stock-logo-large">${String(s.symbol||s.name||"?").slice(0,2).toUpperCase()}</div>
        <div class="corp-stock-symbol">${s.symbol||""}</div><h2>${s.name}</h2>
      </div>
      <article class="corp-stock-chart-card">
        <div class="corp-stock-chart-head">
          <div><span>Текущая цена</span><strong>${fmt(s.current_price)}</strong><small class="${change>=0?"positive":"negative"}">${change>=0?"+":"−"} ${Math.abs(change).toFixed(2)}%</small></div>
          <button class="corp-chart-switch" onclick="corporationToggleStockChart('${s.id}')">${corporationStockViewMode==="candles"?"〽 Линия":"🕯 Свечи"}</button>
        </div>
        ${corporationRenderChart(s.history||[],corporationStockViewMode)}
        <div class="corp-extreme-note">MAX и MIN — максимум и минимум видимой истории графика.</div>
      </article>
      <button class="corp-stock-buy-main" onclick="openTrade('${s.id}','buy')">Купить акции</button>
      ${owned>0?`<button class="corp-stock-sell-main" onclick="openTrade('${s.id}','sell')">Продать акции · ${owned} шт.</button>`:""}
      <section class="corp-stock-info">
        <h2>Сведения</h2>
        <div class="corp-stock-info-row"><span>Стоимость одной акции</span><strong>${fmt(s.current_price)}</strong></div>
        <div class="corp-stock-info-row"><span>В портфеле</span><strong>${owned} шт.</strong></div>
        <div class="corp-stock-info-row"><span>Дивиденды</span><strong>${Number(s.dividend_rate_percent||0).toFixed(2)}% / ч</strong></div>
        <div class="corp-stock-description"><span>О компании</span><p>${s.description||"Описание компании пока отсутствует."}</p></div>
      </section>
    </section>`;
    window.scrollTo({top:0,left:0,behavior:"auto"});
  }catch(e){corporationActiveStockId=null;modal("Ошибка",e.message);await renderInvestments()}
};

corporationToggleStockChart=async function(id){
  corporationStockViewMode=corporationStockViewMode==="line"?"candles":"line";
  await openStock(id,true);
};

corporationCloseStock=async function(){
  corporationActiveStockId=null;
  await renderInvestments();
  requestAnimationFrame(()=>window.scrollTo({top:corporationStockReturnScroll,left:0,behavior:"auto"}));
};

openTrade=async function(id,side){
  const s=stocksCache.find(x=>String(x.id)===String(id));if(!s)return;
  const h=getHolding(id),owned=Number(h?.quantity||0),price=Number(s.current_price||0);
  const max=side==="buy"?Math.floor(Number(state.player.money||0)/price):owned;
  if(max<=0){modal("Сделка",side==="buy"?"Недостаточно средств для покупки.":"У тебя нет этих акций.");return}
  const raw=prompt(`${side==="buy"?"Покупка":"Продажа"} ${s.name}\nЦена: ${fmt(price)}\nМаксимум: ${max} шт.\nВведите количество:`,"1");
  if(raw===null)return;
  const qty=parseInt(raw,10);
  if(!Number.isInteger(qty)||qty<=0||qty>max){modal("Ошибка",`Введите целое число от 1 до ${max}.`);return}
  try{
    const r=await api(`/api/stocks/${id}/${side}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({quantity:qty})});
    state=r.state;renderHeader();await Promise.all([loadStocks(),loadBrokerage()]);
    if(corporationActiveStockId===String(id))await openStock(id,true);else await renderInvestments();
    modal(side==="buy"?"Акции куплены":"Акции проданы",side==="sell"&&Number(r.realized_profit)>0?`Прибыль сделки: ${fmt(r.realized_profit)}\nНалог с прибыли: ${fmt(r.profit_tax)}`:`Сумма сделки: ${fmt(side==="buy"?r.total_cost:r.total_income)}`);
  }catch(e){modal("Сделка не выполнена",e.message)}
};

window.openStock=openStock;
window.openTrade=openTrade;
window.corporationToggleStockChart=corporationToggleStockChart;
window.corporationCloseStock=corporationCloseStock;
/* === /CORPORATION_STOCK_MARKET_V17 === */
"""

CSS_BLOCK=r"""
/* === CORPORATION_STOCK_MARKET_V17 === */
.investment-page>.grid:has(.corp-stock-row){display:grid;gap:0;border:1px solid var(--line);border-radius:22px;overflow:hidden;background:var(--card)}
.corp-stock-row{width:100%;min-height:80px;display:grid;grid-template-columns:46px minmax(0,1fr) auto 14px;gap:11px;align-items:center;padding:13px 13px;border:0;border-bottom:1px solid var(--line);border-radius:0;background:transparent;text-align:left;color:var(--text)}
.corp-stock-row:last-child{border-bottom:0}.corp-stock-row:active{background:rgba(255,255,255,.035);transform:none}
.corp-stock-icon{width:44px;height:44px;display:flex;align-items:center;justify-content:center;border-radius:50%;border:1px solid rgba(230,190,80,.28);background:linear-gradient(145deg,rgba(216,174,67,.15),rgba(255,255,255,.025));color:#e7c96d;font-size:12px;font-weight:900}
.corp-stock-name{min-width:0;display:grid;gap:4px}.corp-stock-name strong{overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:16px}.corp-stock-name span{color:var(--hint);font-size:12px}
.corp-stock-quote{min-width:92px;display:grid;gap:5px;text-align:right}.corp-stock-quote strong{font-size:16px;white-space:nowrap}.corp-stock-quote span{font-size:11px;white-space:nowrap}.corp-stock-arrow{color:var(--hint);font-size:23px;font-weight:400}
.corp-stock-page{display:grid;gap:15px;padding-bottom:22px}.corp-stock-page-top{display:flex;min-height:42px}.corp-stock-back{width:42px;height:42px;padding:0;border:1px solid var(--line);border-radius:50%;background:var(--card);color:var(--text);font-size:23px}
.corp-stock-company{text-align:center;padding:8px 0 0}.corp-stock-logo-large{width:82px;height:82px;margin:0 auto 10px;display:flex;align-items:center;justify-content:center;border-radius:24px;border:1px solid rgba(230,190,80,.28);background:linear-gradient(145deg,rgba(212,171,61,.14),rgba(255,255,255,.025));color:#e6c96d;font-size:22px;font-weight:900}.corp-stock-symbol{color:var(--hint);font-size:11px;font-weight:900;letter-spacing:1.4px}.corp-stock-company h2{margin:6px 0 0;font-size:28px}
.corp-stock-chart-card{padding:15px 12px 11px;border:1px solid var(--line);border-radius:20px;background:var(--card)}.corp-stock-chart-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:7px}.corp-stock-chart-head>div{display:grid;gap:4px}.corp-stock-chart-head span{color:var(--hint);font-size:11px}.corp-stock-chart-head strong{font-size:24px}.corp-stock-chart-head small{font-size:12px;font-weight:800}
.corp-chart-switch{flex-shrink:0;padding:9px 11px;border:1px solid rgba(226,190,78,.25);border-radius:12px;background:rgba(226,190,78,.08);color:#e5c86f;font-size:12px}
.corp-stock-chart{width:100%;height:270px;overflow:hidden;color:#d6b756}.corp-stock-chart svg{width:100%;height:100%;display:block}.corp-chart-grid{stroke:rgba(255,255,255,.08);stroke-width:1;vector-effect:non-scaling-stroke}.corp-chart-axis,.corp-chart-time{fill:rgba(255,255,255,.42);font-size:10px}.corp-stock-area{fill:rgba(213,181,82,.055)}.corp-stock-line{fill:none;stroke:#d7b958;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.corp-extreme-line{stroke:rgba(229,203,121,.34);stroke-width:1;stroke-dasharray:6 7;vector-effect:non-scaling-stroke}.corp-extreme-label{fill:rgba(229,203,121,.66);font-size:9px;font-weight:800}.corp-current-price-line{stroke:rgba(255,255,255,.16);stroke-width:1;stroke-dasharray:3 5;vector-effect:non-scaling-stroke}.corp-current-dot{fill:#e0bf5b}
.corp-candle-wick{stroke-width:1.25;vector-effect:non-scaling-stroke}.corp-candle-body{vector-effect:non-scaling-stroke}.corp-candle-wick.up{stroke:#35c759}.corp-candle-body.up{stroke:#35c759;fill:#35c759}.corp-candle-wick.down{stroke:#ff5a52}.corp-candle-body.down{stroke:#ff5a52;fill:#ff5a52}.corp-stock-chart-empty{height:235px;display:flex;align-items:center;justify-content:center;color:var(--hint)}.corp-extreme-note{margin-top:3px;color:var(--hint);font-size:10px}
.corp-stock-buy-main,.corp-stock-sell-main{width:100%;min-height:54px;border-radius:17px;padding:15px;font-size:16px}.corp-stock-buy-main{border:1px solid rgba(230,194,84,.45);background:linear-gradient(135deg,#d4b04f,#f0d476);color:#17130a}.corp-stock-sell-main{border:1px solid rgba(255,90,82,.28);background:rgba(255,90,82,.06);color:#ff7b75}
.corp-stock-info{padding:18px;border:1px solid var(--line);border-radius:20px;background:var(--card)}.corp-stock-info h2{margin:0 0 15px;font-size:22px}.corp-stock-info-row{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-top:1px solid var(--line)}.corp-stock-info-row span{color:var(--hint);font-size:13px}.corp-stock-info-row strong{text-align:right;font-size:14px}.corp-stock-description{padding-top:14px;border-top:1px solid var(--line)}.corp-stock-description span{color:var(--hint);font-size:12px}.corp-stock-description p{margin:7px 0 0;color:var(--text);font-size:13px;line-height:1.55}
@media(max-width:420px){.corp-stock-row{grid-template-columns:40px minmax(0,1fr) auto 11px;gap:8px;padding:12px 9px;min-height:72px}.corp-stock-icon{width:39px;height:39px;font-size:10px}.corp-stock-name strong{font-size:14px}.corp-stock-quote{min-width:80px}.corp-stock-quote strong{font-size:14px}.corp-stock-quote span{font-size:10px}.corp-stock-chart{height:235px}.corp-stock-chart-head strong{font-size:21px}}
/* === /CORPORATION_STOCK_MARKET_V17 === */
"""

def main():
    for p in (JS,CSS,INDEX):
        backup(p)
    if BOT.exists(): backup(BOT)

    js=JS.read_text(encoding="utf-8")
    js=strip_block(js,"/* === CORPORATION_STOCK_MARKET_V17 === */","/* === /CORPORATION_STOCK_MARKET_V17 === */")
    js=js.rstrip()+"\n\n"+JS_BLOCK.strip()+"\n"
    JS.write_text(js,encoding="utf-8")

    css=CSS.read_text(encoding="utf-8")
    css=strip_block(css,"/* === CORPORATION_STOCK_MARKET_V17 === */","/* === /CORPORATION_STOCK_MARKET_V17 === */")
    css=css.rstrip()+"\n\n"+CSS_BLOCK.strip()+"\n"
    CSS.write_text(css,encoding="utf-8")

    idx=INDEX.read_text(encoding="utf-8")
    idx=re.sub(r'(/static/app\.js\?v=)[^"\']+',r'\g<1>17.1',idx)
    idx=re.sub(r'(/static/style\.css\?v=)[^"\']+',r'\g<1>17.1',idx)
    if "/static/app.js?v=" not in idx: idx=idx.replace("/static/app.js","/static/app.js?v=17.1",1)
    if "/static/style.css?v=" not in idx: idx=idx.replace("/static/style.css","/static/style.css?v=17.1",1)
    INDEX.write_text(idx,encoding="utf-8")

    if BOT.exists():
        b=BOT.read_text(encoding="utf-8")
        b,n=re.subn(r'WEBAPP_VERSION\s*=\s*["\'][^"\']+["\']','WEBAPP_VERSION = "171"',b,count=1)
        if n: BOT.write_text(b,encoding="utf-8")

    final=JS.read_text(encoding="utf-8")
    needed=["CORPORATION_STOCK_MARKET_V17","renderStockCard=function(stock)","openStock=async function","corporationBuildCandles","corp-extreme-line"]
    miss=[x for x in needed if x not in final]
    if miss: raise RuntimeError("Проверка не пройдена: "+", ".join(miss))

    print("Corporation v17 установлен успешно.")
    print("Список акций, отдельная страница, свечи, MAX/MIN: ГОТОВО.")
    print("Cache version: 17.1; bot WebApp version: 171.")
    print("app.py и corporation.db не изменялись.")

if __name__=="__main__":
    try: main()
    except Exception as e:
        print("ОШИБКА:",e)
        sys.exit(1)
