/* Corporation v29: business slots, bond/fleet sliders, refined rating. */
(function(){
  function slotStatus29(){return state?.business_slots||{slots:10,used:0,available:10,next_cost:100000,seconds_left:0,can_expand_now:true,max_slots:100};}

  const renderBusinessesBase29=window.renderBusinesses;
  window.renderBusinesses=renderBusinesses=function(){
    renderBusinessesBase29();
    if(!state||page!=='businesses')return;
    const section=document.querySelector('.business-page25');
    const tabs=section?.querySelector('.business-tabs28');
    if(!section||!tabs)return;
    const s=slotStatus29();
    const full=Number(s.available)<=0;
    const cooling=Number(s.seconds_left)>0;
    const maxed=Number(s.slots)>=Number(s.max_slots||100);
    const panel=document.createElement('section');
    panel.className='business-slots29';
    if(cooling){panel.dataset.liveUntil=String(s.can_expand_at||0);panel.dataset.liveReload='businesses';}
    panel.innerHTML=`<div class="slot-copy29"><div class="slot-kicker29">ЛИМИТ БИЗНЕСОВ</div><div class="slot-title29"><strong>${fmtNumber(s.used)} / ${fmtNumber(s.slots)}</strong><span>слотов занято</span></div><div class="slot-track29"><i style="width:${Math.min(100,Number(s.used||0)/Math.max(1,Number(s.slots||1))*100)}%"></i></div><p>${maxed?'Достигнут максимальный лимит слотов.':cooling?`Следующее расширение через <b data-live-value>${duration25(s.seconds_left)}</b>.`:`Добавь ещё 1 слот за ${fmt(s.next_cost)}. После покупки следующее расширение будет доступно через 1 час.`}</p></div><button type="button" class="slot-expand29" ${maxed||cooling||Number(state.player.money)<Number(s.next_cost)?'disabled':''} onclick="expandBusinessSlot29()">${maxed?'Максимум':cooling?'Ожидание':`+1 слот · ${fmt(s.next_cost)}`}</button>`;
    tabs.before(panel);
    if(full&&businessView28==='catalog'){
      section.querySelectorAll('.business-card25 .buy').forEach(btn=>{btn.disabled=true;btn.textContent=`Лимит ${s.used}/${s.slots} · расширь слот`;});
    }
    tickLiveTimers25();
  };

  window.expandBusinessSlot29=async function(){
    const s=slotStatus29();
    if(Number(s.seconds_left)>0||Number(s.slots)>=Number(s.max_slots||100))return;
    if(Number(state.player.money)<Number(s.next_cost)){modal('Расширение лимита',`Для нового слота нужно ${fmt(s.next_cost)}.`);return;}
    if(!await corpConfirm(`Расширить лимит бизнесов с ${s.slots} до ${Number(s.slots)+1} за ${fmt(s.next_cost)}?\n\nСледующий слот можно будет открыть через 1 час.`))return;
    await stableAction28(async()=>{
      try{
        const r=await api('/api/business-slots/expand',{method:'POST'});
        state=r.state;syncServerClock25(true);renderHeader();renderBusinesses();
        modal('Лимит расширен',`Теперь можно держать до ${r.slots} бизнесов одновременно.`);
      }catch(e){modal('Расширение не выполнено',e.message);}
    });
  };

  window.openBondTrade=openBondTrade=async function(id,side,all=false){
    if(!['buy','sell'].includes(side)||corporationTradeBusy)return;
    corporationTradeBusy=true;
    try{
      await stableAction28(async()=>{
        try{
          state=await api('/api/state');renderHeader();
          await loadBonds();
          const b=bondsCache.find(x=>String(x.id)===String(id));if(!b)return;
          const price=Number(b.price),owned=Number(b.quantity||0);
          const max=Math.min(Number.MAX_SAFE_INTEGER,side==='buy'?Math.floor(Number(state.player.money)/price):owned);
          if(max<1){modal('Облигации',side==='buy'?'Недостаточно средств.':'У тебя нет этих облигаций.');return;}
          const q=await quantityDialog25({title:`${side==='buy'?'Покупка':'Продажа'} ${b.name}`,subtitle:`Цена одной облигации: ${fmt(price)}`,max,value:all?max:1,price,side:'buy'});
          if(q===null)return;
          const r=await api(`/api/bonds/${id}/${side}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:q,expected_price:price})});
          state=r.state;bondsCache=r.bonds||[];renderHeader();
          if(page==='investments')await renderInvestments();
          modal(side==='buy'?'Облигации куплены':'Облигации проданы',`Количество: ${fmtNumber(q)} шт.\nСумма: ${fmt(side==='buy'?r.total_cost:r.total_income)}`);
        }catch(e){modal('Сделка не выполнена',e.message);}
      });
    }finally{corporationTradeBusy=false;}
  };
  window.tradeAllBond=tradeAllBond=(id,side)=>openBondTrade(id,side,true);

  window.buyFleetVehicle25=buyFleetVehicle25=async function(bid,vid){
    await stableAction28(async()=>{
      const b=state?.businesses?.find(x=>x.id===bid),v=b?.transport?.vehicles?.find(x=>x.id===vid);if(!v)return;
      const max=Math.min(Number(b.transport.available||0),Math.floor(Number(state.player.money||0)/Number(v.cost||1)),100);
      if(max<1){modal('Покупка','Недостаточно денег или свободных мест.');return;}
      const q=await quantityDialog25({title:`Купить: ${v.name}`,subtitle:`${fmt(v.cost)} за машину · свободных мест ${b.transport.available}`,max,price:Number(v.cost),side:'buy'});
      if(q===null)return;
      try{
        const r=await api(`/api/fleet/${bid}/vehicle/${vid}/buy`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quantity:q})});
        state=r.state;syncServerClock25(true);renderHeader();renderBusinesses();tickLiveTimers25();
        modal('Машины куплены',`Количество: ${fmtNumber(q)} шт.\nСумма: ${fmt(r.total_cost)}`);
      }catch(e){modal('Не удалось купить',e.message);}
    });
  };

  const renderRatingBase29=window.renderRating;
  window.renderRating=renderRating=async function(){
    await renderRatingBase29();
    if(page!=='rating')return;
    document.querySelectorAll('.rating-page .rank-button').forEach((row,i)=>{
      row.dataset.place=String(i+1);
      if(i<3)row.classList.add(`rank-top${i+1}-29`);
    });
  };

  // Re-render the current start page once so the slot panel appears immediately.
  if(state&&page==='businesses')renderBusinesses();
})();
