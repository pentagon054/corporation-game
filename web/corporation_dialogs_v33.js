/* Corporation v33: unified in-game dialogs replacing browser/Telegram-native popups. */
(function(){
  'use strict';
  let active=null;
  function ensure(){
    let root=document.getElementById('corpDialog33');
    if(root)return root;
    root=document.createElement('div');root.id='corpDialog33';root.className='corp-dialog33 hidden';
    root.innerHTML=`<div class="corp-dialog-card33" role="dialog" aria-modal="true"><div class="corp-dialog-glow33"></div><div class="corp-dialog-brand33">CORPORATION</div><h2 id="corpDialogTitle33">Подтверждение</h2><div id="corpDialogText33" class="corp-dialog-text33"></div><input id="corpDialogInput33" class="corp-dialog-input33" autocomplete="off" hidden><div class="corp-dialog-actions33"><button id="corpDialogCancel33" class="corp-dialog-cancel33" type="button">Отмена</button><button id="corpDialogOk33" class="corp-dialog-ok33" type="button">Подтвердить</button></div></div>`;
    document.body.appendChild(root);return root;
  }
  function close(value){
    const root=ensure();root.classList.add('leaving');
    setTimeout(()=>{root.classList.add('hidden');root.classList.remove('leaving');},160);
    const done=active;active=null;if(done)done(value);
  }
  function ask({title='Подтверждение',text='',input=false,value='',ok='Подтвердить',cancel='Отмена',cancelable=true}={}){
    if(active)close(null);
    const root=ensure(),titleEl=root.querySelector('#corpDialogTitle33'),textEl=root.querySelector('#corpDialogText33'),field=root.querySelector('#corpDialogInput33'),okBtn=root.querySelector('#corpDialogOk33'),cancelBtn=root.querySelector('#corpDialogCancel33');
    titleEl.textContent=title;textEl.textContent=String(text??'');field.hidden=!input;field.value=input?String(value??''):'';okBtn.textContent=ok;cancelBtn.textContent=cancel;cancelBtn.hidden=!cancelable;
    root.classList.remove('hidden','leaving');requestAnimationFrame(()=>root.classList.add('visible'));
    return new Promise(resolve=>{
      active=resolve;
      okBtn.onclick=()=>close(input?field.value:true);
      cancelBtn.onclick=()=>close(input?null:false);
      root.onclick=e=>{if(e.target===root&&cancelable)close(input?null:false)};
      field.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();close(field.value)}else if(e.key==='Escape'&&cancelable){e.preventDefault();close(null)}};
      document.onkeydown=e=>{if(e.key==='Escape'&&cancelable&&!input){e.preventDefault();close(false)}};
      setTimeout(()=>{(input?field:okBtn).focus({preventScroll:true})},30);
    });
  }
  window.corpConfirm=(text,title='Подтверждение')=>ask({title,text,input:false,ok:'Подтвердить',cancel:'Отмена'});
  window.corpPrompt=(text,value='',title='Введите значение')=>ask({title,text,input:true,value,ok:'Готово',cancel:'Отмена'});
  window.corpAlert=(text,title='Сообщение')=>ask({title,text,input:false,ok:'Готово',cancelable:false});
})();
