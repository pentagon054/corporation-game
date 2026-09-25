/* Corporation v34.3: race-safe unified in-game dialogs. */
(function(){
  'use strict';

  let active=null;
  let hideTimer=null;
  let sequence=0;

  function ensure(){
    let root=document.getElementById('corpDialog33');
    if(root)return root;
    root=document.createElement('div');root.id='corpDialog33';root.className='corp-dialog33 hidden';
    root.innerHTML=`<div class="corp-dialog-card33" role="dialog" aria-modal="true"><div class="corp-dialog-glow33"></div><div class="corp-dialog-brand33">CORPORATION</div><h2 id="corpDialogTitle33">Подтверждение</h2><div id="corpDialogText33" class="corp-dialog-text33"></div><input id="corpDialogInput33" class="corp-dialog-input33" autocomplete="off" hidden><div class="corp-dialog-actions33"><button id="corpDialogCancel33" class="corp-dialog-cancel33" type="button">Отмена</button><button id="corpDialogOk33" class="corp-dialog-ok33" type="button">Подтвердить</button></div></div>`;
    document.body.appendChild(root);return root;
  }

  function cancelHide(){
    if(hideTimer!==null){clearTimeout(hideTimer);hideTimer=null;}
  }

  function clearHandlers(root){
    const field=root.querySelector('#corpDialogInput33');
    const okBtn=root.querySelector('#corpDialogOk33');
    const cancelBtn=root.querySelector('#corpDialogCancel33');
    if(okBtn)okBtn.onclick=null;
    if(cancelBtn)cancelBtn.onclick=null;
    if(field)field.onkeydown=null;
    root.onclick=null;
    document.onkeydown=null;
  }

  function settlePrevious(){
    if(!active)return;
    const previous=active;
    active=null;
    previous.resolve(null);
  }

  function close(value){
    if(!active)return;
    const current=active;
    active=null;
    const root=ensure();
    clearHandlers(root);
    cancelHide();
    root.classList.remove('visible');
    root.classList.add('leaving');

    hideTimer=setTimeout(()=>{
      hideTimer=null;
      // A newer dialog may already be open. Never let an old close timer hide it.
      if(active)return;
      root.classList.add('hidden');
      root.classList.remove('leaving','visible');
    },160);

    current.resolve(value);
  }

  function ask({title='Подтверждение',text='',input=false,value='',ok='Подтвердить',cancel='Отмена',cancelable=true}={}){
    const root=ensure();

    // If a stale/previous dialog is still logically active, settle it immediately.
    // Do not start another hide animation: that timer could hide the new dialog.
    cancelHide();
    settlePrevious();
    clearHandlers(root);

    const token=++sequence;
    const titleEl=root.querySelector('#corpDialogTitle33');
    const textEl=root.querySelector('#corpDialogText33');
    const field=root.querySelector('#corpDialogInput33');
    const okBtn=root.querySelector('#corpDialogOk33');
    const cancelBtn=root.querySelector('#corpDialogCancel33');

    titleEl.textContent=title;
    textEl.textContent=String(text??'');
    field.hidden=!input;
    field.value=input?String(value??''):'';
    okBtn.textContent=ok;
    cancelBtn.textContent=cancel;
    cancelBtn.hidden=!cancelable;

    root.classList.remove('hidden','leaving');

    return new Promise(resolve=>{
      active={resolve,token};

      requestAnimationFrame(()=>{
        if(active?.token===token)root.classList.add('visible');
      });

      okBtn.onclick=()=>{
        if(active?.token!==token)return;
        close(input?field.value:true);
      };
      cancelBtn.onclick=()=>{
        if(active?.token!==token)return;
        close(input?null:false);
      };
      root.onclick=e=>{
        if(active?.token===token&&e.target===root&&cancelable)close(input?null:false);
      };
      field.onkeydown=e=>{
        if(active?.token!==token)return;
        if(e.key==='Enter'){
          e.preventDefault();close(field.value);
        }else if(e.key==='Escape'&&cancelable){
          e.preventDefault();close(null);
        }
      };
      document.onkeydown=e=>{
        if(active?.token===token&&e.key==='Escape'&&cancelable&&!input){
          e.preventDefault();close(false);
        }
      };

      setTimeout(()=>{
        if(active?.token!==token)return;
        try{(input?field:okBtn).focus({preventScroll:true});}catch(_){ }
      },30);
    });
  }

  window.corpConfirm=(text,title='Подтверждение')=>ask({title,text,input:false,ok:'Подтвердить',cancel:'Отмена'});
  window.corpPrompt=(text,value='',title='Введите значение')=>ask({title,text,input:true,value,ok:'Готово',cancel:'Отмена'});
  window.corpAlert=(text,title='Сообщение')=>ask({title,text,input:false,ok:'Готово',cancelable:false});
})();
