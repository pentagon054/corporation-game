/* Corporation v28: persistent instances and stable transactional UI. */
let businessView28='catalog';
let actionBusy28=false;

// Update attributes and text in place: vehicles/buttons that have not changed
// retain their DOM identity, focus, and scroll anchoring.
function patchNode28(old,next){
  if(old.nodeType!==next.nodeType||old.nodeName!==next.nodeName){old.replaceWith(next.cloneNode(true));return;}
  if(old.nodeType===Node.TEXT_NODE){if(old.nodeValue!==next.nodeValue)old.nodeValue=next.nodeValue;return;}
  if(old.nodeType!==Node.ELEMENT_NODE)return;
  for(const a of [...old.attributes])if(!next.hasAttribute(a.name))old.removeAttribute(a.name);
  for(const a of next.attributes)if(old.getAttribute(a.name)!==a.value)old.setAttribute(a.name,a.value);
  const desired=[...next.childNodes];
  for(let i=0;i<desired.length;i++){
    const n=desired[i],key=n.nodeType===1?n.getAttribute('data-business-key'):null;
    let current=old.childNodes[i];
    if(key&&current?.getAttribute?.('data-business-key')!==key){
      const found=[...old.children].find(x=>x.getAttribute('data-business-key')===key);
      if(found)old.insertBefore(found,current||null);else old.insertBefore(n.cloneNode(true),current||null);
      current=old.childNodes[i];
    }
    if(current)patchNode28(current,n);else old.append(n.cloneNode(true));
  }
  while(old.childNodes.length>desired.length)old.lastChild.remove();
}
function setBusinessView28(view){
  businessView28=view==='mine'?'mine':'catalog';renderBusinesses();
}
renderBusinesses=function(){
  if(!state||page!=='businesses')return;
  const counts={},owned=(state.businesses||[]).filter(b=>b.owned).map(b=>{
    const type=b.type_id||b.id;counts[type]=(counts[type]||0)+1;
    return {...b,instance_label:counts[type]};
  });
  const items=businessView28==='mine'?owned:(state.business_catalog||[]);
  const html=`<section class="business-page25"><div class="section-top"><div><div class="eyebrow">ОПЕРАЦИОННЫЕ АКТИВЫ</div><h2>Бизнесы</h2></div></div><div class="business-tabs28" role="tablist" aria-label="Бизнесы"><button role="tab" aria-selected="${businessView28==='catalog'}" onclick="setBusinessView28('catalog')">Открыть бизнес</button><button role="tab" aria-selected="${businessView28==='mine'}" onclick="setBusinessView28('mine')">Мои бизнесы · ${owned.length}</button></div><div class="grid">${items.map(businessCard28).join('')||'<div class="empty">У тебя пока нет бизнесов. Открой первый в соседнем разделе.</div>'}</div></section>`;
  const c=document.querySelector('#content'),template=document.createElement('template');template.innerHTML=html;
  if(c.firstElementChild?.classList.contains('business-page25'))patchNode28(c.firstElementChild,template.content.firstElementChild);
  else c.replaceChildren(template.content);
  tickLiveTimers25();
};
window.renderBusinesses=renderBusinesses;

const headerBase28=renderHeader;
renderHeader=function(){
  headerBase28();
  document.body.classList.toggle('secondary-page28',page!=='businesses');
};window.renderHeader=renderHeader;

// One modal lifecycle for stocks and fleets; closing/cancelling always releases
// the action lock. No automatic focus that could scroll the WebView to an input.
quantityDialog25=function({title,subtitle,max,value=1,price=null,side='buy',average=0}){
  return new Promise(resolve=>{
    const overlay=document.querySelector('#modal'),body=document.querySelector('#modalText'),close=document.querySelector('#modalClose');
    max=Math.min(Number.MAX_SAFE_INTEGER,Math.floor(max));
    if(max<1){resolve(null);return;}
    document.querySelector('#modalTitle').textContent=title;
    body.innerHTML=`<div class="quantity-dialog25"><p>${escapeHTML(subtitle)}</p><div class="quantity-step25"><button type="button" data-q="minus" aria-label="Уменьшить">−</button><input id="quantity25" type="text" inputmode="numeric" pattern="[0-9]*" aria-label="Количество"><button type="button" data-q="plus" aria-label="Увеличить">+</button></div>${price!==null?`<input class="trade-slider28" type="range" min="1" max="${max}" step="1" aria-label="Количество акций"><div class="trade-summary28" aria-live="polite"><span data-trade-count></span><strong data-trade-total></strong><small data-trade-tax></small></div>`:''}<div class="quantity-max25">Максимум: <b>${fmtNumber(max)}</b></div><div class="quantity-actions25"><button type="button" data-q="cancel">Отмена</button><button type="button" data-q="ok">Подтвердить</button></div></div>`;
    const input=body.querySelector('#quantity25'),range=body.querySelector('input[type=range]'),ok=body.querySelector('[data-q=ok]');
    const update=q=>{
      const valid=Number.isSafeInteger(q)&&q>=1&&q<=max;ok.disabled=!valid;
      if(!range)return;
      if(valid)range.value=String(q);
      body.querySelector('[data-trade-count]').textContent=valid?`${fmtNumber(q)} шт.`:`Введи целое число от 1 до ${fmtNumber(max)}`;
      body.querySelector('[data-trade-total]').textContent=valid?fmt(q*price):'—';
      const tax=valid&&side==='sell'?Math.round(Math.max(0,(price-average)*q)*.05*100)/100:0;
      body.querySelector('[data-trade-tax]').textContent=side==='sell'?`До удержания налога. Налог с прибыли: ≈ ${fmt(tax)}.`:'По указанной цене. При изменении котировки потребуется новая сделка.';
    };
    input.value=String(Math.max(1,Math.min(max,value)));update(Number(input.value));
    input.oninput=()=>update(parseTradeQuantity(input.value,max));
    if(range)range.oninput=()=>{input.value=range.value;update(Number(range.value));};
    let finished=false;
    const finish=v=>{if(finished)return;finished=true;overlay.classList.add('hidden');close.style.display='';body.onclick=null;overlay.removeEventListener('click',backdrop);document.removeEventListener('keydown',key);resolve(v);};
    const backdrop=e=>{if(e.target===overlay)finish(null);};
    const key=e=>{if(e.key==='Escape')finish(null);};
    overlay.addEventListener('click',backdrop);document.addEventListener('keydown',key);
    body.onclick=e=>{
      const a=e.target.closest('[data-q]')?.dataset.q;
      if(a==='cancel')finish(null);
      if(a==='ok'){const q=parseTradeQuantity(input.value,max);if(Number.isSafeInteger(q))finish(q);}
      if(a==='minus'||a==='plus'){input.value=String(Math.max(1,Math.min(max,(parseTradeQuantity(input.value,max)||1)+(a==='plus'?1:-1))));update(Number(input.value));}
    };
    close.style.display='none';overlay.classList.remove('hidden');
  });
};

// Reserve the current document height while a transaction awaits fresh data.
// Restore synchronously, before painting, and leave navigation free to move on.
async function stableAction28(fn){
  if(actionBusy28)return;
  actionBusy28=true;
  const c=document.querySelector('#content'),y=window.scrollY,origin=page,min=c.style.minHeight;
  c.style.minHeight=c.getBoundingClientRect().height+'px';
  try{return await fn();}finally{
    c.style.minHeight=min;
    if(page===origin)window.scrollTo({top:y,left:0,behavior:'instant'});
    actionBusy28=false;
  }
}
for(const name of ['buyBusiness','upgradeBusiness','sellBusiness','buyFleetVehicle25','sellFleetVehicle25','upgradeGarage25','buyProperty','upgradeProperty','sellProperty','payTaxes','openBondTrade','tradeAllBond']){
  const old=window[name];if(typeof old!=='function')continue;
  window[name]=(...args)=>stableAction28(()=>old(...args));
}

openTrade=async function(id,side,all=false){
  if(!['buy','sell'].includes(side)||corporationTradeBusy||actionBusy28)return;
  corporationTradeBusy=true;
  try{await stableAction28(async()=>{
    const s=stocksCache.find(x=>String(x.id)===String(id));if(!s)return;
    const h=getHolding(id),price=Number(s.current_price),owned=Number(h?.quantity||0);
    if(!Number.isFinite(price)||price<=0){modal('Сделка','Обнови котировки.');return;}
    const max=Math.min(Number.MAX_SAFE_INTEGER,side==='buy'?Math.floor(Number(state.player.money)/price):owned);
    if(max<1){modal('Сделка',side==='buy'?'Недостаточно средств.':'Нет акций для продажи.');return;}
    const q=await quantityDialog25({title:`${side==='buy'?'Покупка':'Продажа'} ${s.name}`,subtitle:`Цена одной акции: ${fmt(price)}`,max,value:all?max:1,price,side,average:Number(h?.avg_buy_price||0)});
    if(q===null)return;
    let r;
    try{r=await api(`/api/stocks/${id}/${side}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:q,expected_price:price})});}
    catch(e){modal('Сделка не выполнена',e.message);return;}
    state=r.state;renderHeader();
    try{
      if(page==='investments'){
        if(corporationActiveStockId===String(id)){
          const overview=await api('/api/investments-overview');
          stocksCache=overview.stocks;brokerageCache=overview.brokerage;bondsCache=overview.bonds;
          await openStock(id,true);
        }
        else await renderInvestments();
      }
    }catch{} // A refresh failure must not suggest repeating a completed purchase.
    modal(side==='buy'?'Акции куплены':'Акции проданы',`Количество: ${q} шт.\nСумма сделки: ${fmt(side==='buy'?r.total_cost:r.total_income)}${side==='sell'?`\nНалог с прибыли: ${fmt(r.profit_tax||0)}`:''}`);
  });}finally{corporationTradeBusy=false;}
};
window.openTrade=openTrade;window.tradeAllStock=(id,side)=>openTrade(id,side,true);

// Background refresh cannot replace state while a confirmation is open.
const liveRefreshBase28=liveRefresh24;
liveRefresh24=async function(){if(actionBusy28||!document.querySelector('#modal').classList.contains('hidden'))return;return liveRefreshBase28();};

function renderStableContent28(container,html){
  const template=document.createElement('template');template.innerHTML=html;
  if(container.childNodes.length===1&&template.content.childNodes.length===1&&container.firstElementChild?.className===template.content.firstElementChild?.className){
    patchNode28(container.firstChild,template.content.firstChild);
  }else container.replaceChildren(template.content);
}
if(state){renderHeader();if(page==='businesses')renderBusinesses();}
