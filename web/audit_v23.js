/* Corporation v23: alpha audit UX-001..008. Loaded after legacy UI layers. */
function parseTradeQuantity(raw,max){
  if(typeof raw!=="string" || !/^[0-9]+$/.test(raw.trim()))return NaN;
  const qty=Number(raw.trim());
  return Number.isSafeInteger(qty)&&qty>0&&qty<=max?qty:NaN;
}
let corporationTradeBusy=false;
async function corporationTrade(kind,id,side,all=false){
  if(corporationTradeBusy || !['buy','sell'].includes(side))return;
  corporationTradeBusy=true;
  try{
    state=await api('/api/state');renderHeader();
    let item,owned,price;
    if(kind==='stocks'){
      const [quote]=await Promise.all([api(`/api/stocks/${id}`),loadBrokerage()]);
      item=quote;owned=Number(getHolding(id)?.quantity||0);price=Number(quote.current_price);
    }else{
      await loadBonds();item=bondsCache.find(x=>String(x.id)===String(id));
      if(!item)return;owned=Number(item.quantity||0);price=Number(item.price);
    }
    if(!Number.isFinite(price)||price<=0)throw new Error('Не удалось получить цену. Обнови данные.');
    const max=Math.min(Number.MAX_SAFE_INTEGER,side==='buy'?Math.floor(Number(state.player.money)/price):owned);
    if(max<=0){modal('Сделка',side==='buy'?'Недостаточно свободных денег.':'У тебя нет этих бумаг.');return;}
    const raw=all?String(max):await corpPrompt(`${side==='buy'?'Покупка':'Продажа'} ${item.name}\nЦена: ${fmt(price)}\nМаксимум: ${max} шт.\nВведите целое количество:`, '1');
    if(raw===null)return;
    const qty=parseTradeQuantity(raw,max);
    if(!Number.isSafeInteger(qty)){modal('Ошибка',`Введите целое число от 1 до ${max}. Дроби и текст недопустимы.`);return;}
    if(!await corpConfirm(`${side==='buy'?'Купить':'Продать'} ${item.name}?\nКоличество: ${qty} шт.\nЦена: ${fmt(price)}\nСумма: ${fmt(qty*price)}`))return;
    const result=await api(`/api/${kind}/${id}/${side}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:qty,expected_price:price})});
    state=result.state;renderHeader();
    // A successful trade must not be reported as failed if the following read fails.
    try{
      if(kind==='stocks')await Promise.all([loadStocks(),loadBrokerage()]);else await loadBonds();
      if(page==='investments')await renderInvestments();
    }catch(_){}
    modal(side==='buy'?'Бумаги куплены':'Бумаги проданы',`Количество: ${result.quantity} шт.\nСумма: ${fmt(side==='buy'?result.total_cost:result.total_income)}`);
  }catch(error){modal('Сделка не выполнена',error.message);}
  finally{corporationTradeBusy=false;}
}
openTrade=(id,side)=>corporationTrade('stocks',id,side);
openBondTrade=(id,side)=>corporationTrade('bonds',id,side);
window.openTrade=openTrade;window.openBondTrade=openBondTrade;
window.tradeAllStock=(id,side)=>corporationTrade('stocks',id,side,true);
window.tradeAllBond=(id,side)=>corporationTrade('bonds',id,side,true);

let corporationPropertyBusy=false;
buyProperty=async function(id){
  if(corporationPropertyBusy)return;
  corporationPropertyBusy=true;
  try{
    const [fresh,catalog]=await Promise.all([api('/api/state'),api('/api/real-estate')]);
    state=fresh;realEstateCache=catalog.properties||[];renderHeader();
    const prop=realEstateCache.find(x=>String(x.id)===String(id));
    if(!prop||prop.owned)return;
    const price=Number(prop.purchase_price),money=Number(state.player.money);
    if(money<price){modal('Недостаточно денег',`Нужно ${fmt(price)}; не хватает ${fmt(price-money)}.`);return;}
    if(!await corpConfirm(`Купить ${prop.name} за ${fmt(price)}?`))return;
    const r=await api(`/api/real-estate/${id}/buy`,{method:'POST'});
    state=r.state;realEstateCache=r.properties;renderHeader();
    if(page==='realestate')openCity(prop.city_id);
    modal('Недвижимость куплена',`Доход: ${fmt(realEstateCache.find(x=>x.id===id)?.rent_hour)}/ч.`);
  }catch(error){modal('Покупка не выполнена',error.message);}
  finally{corporationPropertyBusy=false;}
};
window.buyProperty=buyProperty;
const auditPropertyCard=renderPropertyCard;
renderPropertyCard=function(p){
  let html=auditPropertyCard(p);
  if(!p.owned && Number(state.player.money)<Number(p.purchase_price)){
    html=html.replace('Купить за '+fmt(p.purchase_price),'Нужно '+fmt(p.purchase_price)+' · не хватает '+fmt(Number(p.purchase_price)-Number(state.player.money)));
  }
  return html;
};window.renderPropertyCard=renderPropertyCard;

document.addEventListener('visibilitychange',()=>{
  if(!document.hidden&&page==='investments'&&investmentView==='news')renderMarketNews();
});
