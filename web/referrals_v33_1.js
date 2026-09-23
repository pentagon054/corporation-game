/* Corporation v33.1: visible referral program UI. */
(function(){
  'use strict';
  const VERSION='331';
  let returnPage='businesses';

  function money(v){return Number(v||0).toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽'}
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}

  async function copyLink(text){
    try{
      await navigator.clipboard.writeText(text);
      modal('Ссылка скопирована','Отправь её другу. Бонус сработает после 200 000 ₽ капитализации и 5 активных дней.');
    }catch(_){
      await corpPrompt('Скопируй реферальную ссылку:',text,'Реферальная ссылка');
    }
  }

  function friendCard(f,r){
    const done=!!f.rewarded;
    const cap=Math.min(100,Number(f.capital_progress||0));
    const days=Math.min(100,Number(f.active_days_progress||0));
    const daysLeft=Math.max(0,Number(r.active_days_target||5)-Number(f.active_days||0));
    let statusText='В ПРОГРЕССЕ';
    if(done)statusText='БОНУС ПОЛУЧЕН';
    else if(f.blocked)statusText='ЗАБЛОКИРОВАН';
    return `<article class="ref-friend33 ${done?'done':''}">
      <div class="ref-friend-head33"><div><h3>${esc(f.name)}</h3><b>${money(f.capital)}</b></div><span>${statusText}</span></div>
      <div class="ref-progress-label33"><span>Капитализация</span><b>${money(f.capital)} / ${money(r.capital_target)} · ${Math.floor(cap)}%</b></div>
      <div class="ref-track33"><i style="width:${cap}%"></i></div>
      <div class="ref-progress-label33"><span>Активные дни</span><b>${Math.min(Number(f.active_days||0),Number(r.active_days_target||5))} / ${r.active_days_target}</b></div>
      <div class="ref-track33 days"><i style="width:${days}%"></i></div>
      <div class="ref-remain33">${done
        ?`Ты получил ${money(r.inviter_reward)}, друг — ${money(r.invitee_reward)}.`
        :Number(f.remaining_capital||0)>0
          ?`До бонуса ${money(f.remaining_capital)} · ещё ${daysLeft} дн. активности`
          :`Капитал выполнен · ещё ${daysLeft} дн. активности`}</div>
    </article>`;
  }

  function referralEntryMarkup(compact=false){
    return `<span class="ref-entry-icon331">🎁</span><span class="ref-entry-copy331"><b>Реферальная программа</b><small>${compact?'Приглашай друзей и получай бонусы':'20 000 ₽ за активного друга · другу 10 000 ₽'}</small></span><strong>Открыть →</strong>`;
  }

  function installHeaderButton(){
    if(document.getElementById('refTopButton331'))return;
    const rename=document.getElementById('renameBtn');
    if(!rename)return;
    const btn=document.createElement('button');
    btn.id='refTopButton331';
    btn.type='button';
    btn.className='icon ref-top-button331';
    btn.setAttribute('aria-label','Реферальная программа');
    btn.title='Реферальная программа';
    btn.textContent='🎁';
    btn.onclick=()=>openReferrals331();
    rename.parentNode.insertBefore(btn,rename);
  }

  function insertMainEntry(){
    if(page!=='businesses')return;
    const section=document.querySelector('.business-page25')||document.querySelector('#content');
    if(!section||section.querySelector('.ref-entry-main331'))return;
    const entry=document.createElement('button');
    entry.type='button';
    entry.className='ref-entry33 ref-entry-main331';
    entry.onclick=()=>openReferrals331('businesses');
    entry.innerHTML=referralEntryMarkup(false);
    const slots=section.querySelector('.business-slots29');
    const tabs=section.querySelector('.business-tabs28');
    if(slots)slots.after(entry);
    else if(tabs)tabs.before(entry);
    else section.prepend(entry);
  }

  function insertRatingEntry(){
    if(page!=='rating')return;
    const pageEl=document.querySelector('.rating-page')||document.querySelector('#content');
    if(!pageEl||pageEl.querySelector('.ref-entry-rating331'))return;
    const entry=document.createElement('button');
    entry.type='button';
    entry.className='ref-entry33 ref-entry-rating331';
    entry.onclick=()=>openReferrals331('rating');
    entry.innerHTML=referralEntryMarkup(true);
    const summary=pageEl.querySelector('.rank-summary');
    if(summary)summary.after(entry);else pageEl.prepend(entry);
  }

  window.openReferrals331=async function(origin){
    if(origin==='businesses'||origin==='rating')returnPage=origin;
    else if(page==='businesses'||page==='rating')returnPage=page;
    page='referrals';
    if(typeof updateActiveTab==='function')updateActiveTab();
    if(typeof removeRankDock25==='function')removeRankDock25();
    const c=document.querySelector('#content');
    if(!c)return;
    c.innerHTML='<div class="empty">Загружаем реферальную программу…</div>';
    try{
      const d=await api('/api/referrals');
      if(page!=='referrals')return;
      const r=d.rules;
      const share='https://t.me/share/url?url='+encodeURIComponent(d.referral_link)+'&text='+encodeURIComponent(`Залетай в Corporation. Построй свою корпорацию и забери бонус ${money(r.invitee_reward)} после ${money(r.capital_target)} капитализации и ${r.active_days_target} активных дней.`);
      c.innerHTML=`<section class="ref-page33">
        <button class="back-button" type="button" onclick="closeReferrals331()">← Назад</button>
        <article class="ref-hero33">
          <div class="eyebrow">РЕФЕРАЛЬНАЯ ПРОГРАММА</div>
          <h2>Стройте корпорации вместе</h2>
          <p>Друг достигает <b>${money(r.capital_target)}</b> капитализации и играет минимум <b>${r.active_days_target} активных дней</b>.</p>
          <div class="ref-rewards33"><div><span>Друг получает</span><b>+${money(r.invitee_reward)}</b></div><div><span>Ты получаешь</span><b>+${money(r.inviter_reward)}</b></div></div>
          <div class="ref-link33"><span>${esc(d.referral_link)}</span><button type="button" onclick="copyReferral331()">Копировать</button></div>
          <button class="ref-share33" type="button" onclick="shareReferral331()">Пригласить друга</button>
        </article>
        <div class="ref-summary33"><div><span>Приглашено</span><b>${d.friends_count}</b></div><div><span>Бонусов</span><b>${d.rewarded_count}</b></div><div><span>Заработано</span><b>${money(d.total_inviter_rewards)}</b></div></div>
        ${d.bound_to?`<div class="ref-bound331">Твой пригласивший закреплён за тобой до конца сезона.</div>`:''}
        <div class="ref-rules33">Реферал закрепляется за пригласившим навсегда в рамках сезона. Один Telegram ID может быть приглашён только один раз. Самоприглашение запрещено.</div>
        <section class="ref-friends33"><div class="section-top"><div><div class="eyebrow">МОИ ДРУЗЬЯ</div><h2>Прогресс до бонуса</h2></div></div>${d.friends.length?d.friends.map(f=>friendCard(f,r)).join(''):'<div class="empty">Пока никого. Отправь свою ссылку другу — его прогресс появится здесь.</div>'}</section>
      </section>`;
      window.__refData331=d;
      window.__refShare331=share;
    }catch(e){
      modal('Реферальная программа',e && e.message ? e.message : 'Не удалось загрузить реферальную программу.');
      closeReferrals331();
    }
  };

  window.closeReferrals331=function(){
    page=returnPage||'businesses';
    if(typeof updateActiveTab==='function')updateActiveTab();
    if(typeof render==='function')render();
  };

  window.copyReferral331=()=>window.__refData331&&copyLink(window.__refData331.referral_link);
  window.shareReferral331=()=>{
    if(!window.__refShare331)return;
    try{
      if(tg&&typeof tg.openTelegramLink==='function')tg.openTelegramLink(window.__refShare331);
      else location.href=window.__refShare331;
    }catch(_){location.href=window.__refShare331;}
  };

  function wrapRenderers(){
    const businessBase=window.renderBusinesses;
    if(typeof businessBase==='function'&&!businessBase.__ref331){
      const wrapped=function(){
        const result=businessBase.apply(this,arguments);
        Promise.resolve(result).finally(()=>setTimeout(insertMainEntry,0));
        return result;
      };
      wrapped.__ref331=true;
      window.renderBusinesses=renderBusinesses=wrapped;
    }

    const ratingBase=window.renderRating;
    if(typeof ratingBase==='function'&&!ratingBase.__ref331){
      const wrapped=async function(){
        const result=await ratingBase.apply(this,arguments);
        if(page==='rating')insertRatingEntry();
        return result;
      };
      wrapped.__ref331=true;
      window.renderRating=renderRating=wrapped;
    }
  }

  async function bindFromLink(){
    const params=new URLSearchParams(location.search);
    let raw=params.get('ref');
    if(!raw&&tg&&tg.initDataUnsafe&&tg.initDataUnsafe.start_param){
      const sp=String(tg.initDataUnsafe.start_param||'');
      if(/^ref_[0-9]+$/.test(sp))raw=sp.slice(4);
    }
    if(!raw||!/^[0-9]+$/.test(raw))return;
    const inviter=Number(raw);
    if(!Number.isSafeInteger(inviter)||inviter<=0)return;
    try{
      const r=await api('/api/referrals/bind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inviter_id:inviter})});
      params.delete('ref');
      history.replaceState(null,'',location.pathname+(params.toString()?'?'+params.toString():'')+location.hash);
      if(!r.already_bound)modal('Реферал закреплён','Пригласивший закреплён за тобой до конца сезона. Достигни 200 000 ₽ капитализации и 5 активных дней — ты получишь 10 000 ₽.');
    }catch(e){
      if(!/уже закреплён/i.test((e&&e.message)||''))modal('Реферальная ссылка',(e&&e.message)||'Не удалось закрепить пригласившего.');
    }
  }

  installHeaderButton();
  wrapRenderers();
  setTimeout(()=>{installHeaderButton();insertMainEntry();insertRatingEntry();bindFromLink();},0);
  window.__CORPORATION_REFERRALS_VERSION__=VERSION;
})();
