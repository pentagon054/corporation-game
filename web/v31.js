/* Corporation v31: acknowledge only a completed business purchase. */
(function(){
  function showBusinessPurchased31(name){
    modal('Бизнес куплен',`Ты купил бизнес «${name}». Посмотреть его и прокачать можно в разделе «Мои бизнесы» на главной странице.`);
    const button=document.createElement('button');
    button.type='button';button.className='business-purchased-link31';
    button.textContent='Перейти в мои бизнесы';
    button.onclick=()=>{
      document.querySelector('#modal').classList.add('hidden');
      businessView28='mine';
      document.querySelector('.tab[data-page="businesses"]').click();
      window.scrollTo({top:0,left:0,behavior:'instant'});
    };
    document.querySelector('#modalText').append(button);
  }
  window.buyBusiness=async function(id){
    return stableAction28(async()=>{
      const name=(state.business_catalog||[]).find(b=>String(b.id)===String(id))?.name||'Новый бизнес';
      let purchasedState;
      try{purchasedState=await api(`/api/business/${encodeURIComponent(id)}/buy`,{method:'POST'});}
      catch(error){modal('Покупка не выполнена',error.message);return;}
      state=purchasedState;
      // A rendering error must never suggest that a completed purchase failed.
      try{await render();}catch(error){console.error('Business purchase UI refresh failed',error);}
      showBusinessPurchased31(name);
    });
  };
})();
