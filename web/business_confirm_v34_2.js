/* Corporation v34.2: explicit confirmation before buying a business or business upgrade. */
(function(){
  'use strict';

  let decisionBusy342=false;
  const buyBusinessBase342=window.buyBusiness;
  const upgradeBusinessBase342=window.upgradeBusiness;

  function findBusiness342(id){
    const key=String(id);
    const owned=(state?.businesses||[]).find(b=>String(b.id)===key);
    if(owned)return owned;
    return (state?.business_catalog||[]).find(b=>String(b.id)===key)||null;
  }

  function cleanUpgradeName342(value){
    return String(value||'Улучшение').replace(/^[^\p{L}\p{N}]+/u,'').trim()||'Улучшение';
  }

  window.buyBusiness=async function(id){
    if(decisionBusy342||typeof buyBusinessBase342!=='function')return;
    const business=findBusiness342(id);
    if(!business)return buyBusinessBase342.call(this,id);

    const cost=Number(business.purchase_cost||business.base_cost||0);
    const income=Number(business.income_after_purchase||business.base_income||0);
    const text=[
      `Купить бизнес «${business.name||'Новый бизнес'}»?`,
      `Стоимость: ${fmt(cost)}.`,
      income>0?`Доход после покупки: ${fmt(income)}/ч.`:''
    ].filter(Boolean).join('\n');

    decisionBusy342=true;
    try{
      const confirmed=await corpConfirm(text,'Покупка бизнеса');
      if(!confirmed)return;
      return await buyBusinessBase342.call(this,id);
    }finally{
      decisionBusy342=false;
    }
  };

  window.upgradeBusiness=async function(id,upgradeId){
    if(decisionBusy342||typeof upgradeBusinessBase342!=='function')return;
    const business=findBusiness342(id);
    const upgrade=(business?.upgrades||[]).find(u=>String(u.id)===String(upgradeId));
    if(!business||!upgrade)return upgradeBusinessBase342.call(this,id,upgradeId);
    if(upgrade.owned)return;

    const cost=Number(upgrade.cost||0);
    const bonus=Number(upgrade.income_bonus_percent||0);
    const delta=Number(upgrade.income_delta||0);
    const effect=delta>0
      ? `Доход: +${bonus}% (${fmt(delta)}/ч).`
      : (bonus>0?`Доход: +${bonus}%.`: '');
    const text=[
      `Установить улучшение «${cleanUpgradeName342(upgrade.name)}» для бизнеса «${business.name||'Бизнес'}»?`,
      `Стоимость: ${fmt(cost)}.`,
      effect
    ].filter(Boolean).join('\n');

    decisionBusy342=true;
    try{
      const confirmed=await corpConfirm(text,'Улучшение бизнеса');
      if(!confirmed)return;
      return await upgradeBusinessBase342.call(this,id,upgradeId);
    }finally{
      decisionBusy342=false;
    }
  };
})();
