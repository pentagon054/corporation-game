/* Corporation v33: referral program UI. */
(function(){
  'use strict';
  function money33(v){return Number(v||0).toLocaleString('ru-RU',{maximumFractionDigits:0})+' ₽'}
  function esc33(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  async function copy33(text){try{await navigator.clipboard.writeText(text);modal('Ссылка скопирована','Отправь её другу. Бонус сработает после 200 000 ₽ капитализации и 5 активных дней.')}catch(_){await corpPrompt('Скопируй реферальную ссылку:',text,'Реферальная ссылка')}}
  function friend33(f,r){
    const done=f.rewarded,cap=Math.min(100,Number(f.capital_progress||0)),days=Math.min(100,Number(f.active_days_progress||0));
    return `<article class="ref-friend33 ${done?'done':''}"><div class="ref-friend-head33"><div><h3>${esc33(f.name)}</h3><b>${money33(f.capital)}</b></div><span>${done?'БОНУС ПОЛУЧЕН':f.blocked?'ЗАБЛОКИРОВАН':'В ПРОГРЕССЕ'}</span></div><div class="ref-progress-label33"><span>Капитализация</span><b>${money33(f.capital)} / ${money33(r.capital_target)} · ${Math.floor(cap)}%</b></div><div class="ref-track33"><i style="width:${cap}%"></i></div><div class="ref-progress-label33"><span>Активные дни</span><b>${Math.min(f.active_days,r.active_days_target)} / ${r.active_days_target}</b></div><div class="ref-track33 days"><i style="width:${days}%"></i></div><div class="ref-remain33">${done?`Ты получил ${money33(r.inviter_reward)}, друг — ${money33(r.invitee_reward)}.`:f.remaining_capital>0?`До бонуса ${money33(f.remaining_capital)} · ещё ${Math.max(0,r.active_days_target-f.active_days)} дн. активности`:`Капитал выполнен · ещё ${Math.max(0,r.active_days_target-f.active_days)} дн. активности`}</div></article>`;
  }
  window.openReferrals33=async function(){
    const c=document.querySelector('#content');if(typeof removeRankDock25==='function')removeRankDock25();c.innerHTML='<div class="empty">Загружаем реферальную программу…</div>';
    try{
      const d=await api('/api/referrals'),r=d.rules,share='https://t.me/share/url?url='+encodeURIComponent(d.referral_link)+'&text='+encodeURIComponent(`Залетай в Corporation. Построй свою корпорацию и забери бонус ${money33(r.invitee_reward)} после ${money33(r.capital_target)} капитализации и ${r.active_days_target} активных дней.`);
      window.__refReturnPage33=page==='rating'?'rating':(window.__refReturnPage33||page||'rating');
      c.innerHTML=`<section class="ref-page33"><button class="back-button" onclick="backFromReferrals33()">← Назад</button><article class="ref-hero33"><div class="eyebrow">РЕФЕРАЛЬНАЯ ПРОГРАММА</div><h2>Стройте корпорации вместе</h2><p>Друг достигает <b>${money33(r.capital_target)}</b> капитализации и играет минимум <b>${r.active_days_target} активных дней</b>.</p><div class="ref-rewards33"><div><span>Друг получает</span><b>+${money33(r.invitee_reward)}</b></div><div><span>Ты получаешь</span><b>+${money33(r.inviter_reward)}</b></div></div><div class="ref-link33"><span>${esc33(d.referral_link)}</span><button onclick="copyReferral33()">Копировать</button></div><button class="ref-share33" onclick="shareReferral33()">Пригласить друга</button></article><div class="ref-summary33"><div><span>Приглашено</span><b>${d.friends_count}</b></div><div><span>Бонусов</span><b>${d.rewarded_count}</b></div><div><span>Заработано</span><b>${money33(d.total_inviter_rewards)}</b></div></div><div class="ref-rules33">Реферал закрепляется за пригласившим навсегда в рамках сезона. Один Telegram ID может быть приглашён только один раз. Самоприглашение запрещено.</div><section class="ref-friends33"><div class="section-top"><div><div class="eyebrow">МОИ ДРУЗЬЯ</div><h2>Прогресс до бонуса</h2></div></div>${d.friends.length?d.friends.map(f=>friend33(f,r)).join(''):'<div class="empty">Пока никого. Отправь свою ссылку другу — его прогресс появится здесь.</div>'}</section></section>`;
      window.__refData33=d;window.__refShare33=share;
    }catch(e){modal('Реферальная программа',e.message)}
  };
  window.copyReferral33=()=>window.__refData33&&copy33(window.__refData33.referral_link);
  window.shareReferral33=()=>{if(!window.__refShare33)return;try{if(tg?.openTelegramLink)tg.openTelegramLink(window.__refShare33);else location.href=window.__refShare33}catch(_){location.href=window.__refShare33}};
  window.backFromReferrals33=()=>{const prev=window.__refReturnPage33||'rating'; if(prev==='rating') return renderRating(); if(prev==='statistics'){page='statistics'; return renderStatistics();} if(prev==='taxes'){page='taxes'; return renderTaxes();} if(prev==='realestate'){page='realestate'; return renderRealEstate();} if(prev==='investments'){page='investments'; return renderInvestments();} page='businesses'; return renderBusinesses();};
  const baseRating33=window.renderRating;
  window.renderRating=renderRating=async function(){
    await baseRating33();if(page!=='rating')return;
    const pageEl=document.querySelector('.rating-page');if(!pageEl||pageEl.querySelector('.ref-entry33'))return;
    const entry=document.createElement('button');entry.type='button';entry.className='ref-entry33';entry.onclick=openReferrals33;entry.innerHTML='<span><b>🎁 Реферальная программа</b><small>20 000 ₽ за активного друга · другу 10 000 ₽</small></span><strong>Открыть →</strong>';
    const summary=pageEl.querySelector('.rank-summary');if(summary)summary.after(entry);else pageEl.prepend(entry);
  };
  async function bindFromLink33(){
    const params=new URLSearchParams(location.search),raw=params.get('ref');if(!raw||!/^[0-9]+$/.test(raw))return;
    const inviter=Number(raw);if(!Number.isSafeInteger(inviter)||inviter<=0)return;
    try{const r=await api('/api/referrals/bind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({inviter_id:inviter})});params.delete('ref');history.replaceState(null,'',location.pathname+(params.toString()?'?'+params.toString():'')+location.hash);if(!r.already_bound)modal('Реферал закреплён','Пригласивший закреплён за тобой до конца сезона. Достигни 200 000 ₽ капитализации и 5 активных дней — ты получишь 10 000 ₽.')}
    catch(e){if(!/уже закреплён/i.test(e.message||''))modal('Реферальная ссылка',e.message)}
  }
  setTimeout(bindFromLink33,0);
})();
