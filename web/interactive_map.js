/* Offline map interaction. Coordinates use the equirectangular world.svg projection. */
class CorporationAtlas {
  constructor(root,cities,{onSelect,saved,onChange}={}){
    this.root=root;this.cities=cities;this.onSelect=onSelect;this.onChange=onChange;
    this.scale=saved?.scale||1;this.tx=0;this.ty=0;this.width=0;this.height=0;
    this.points=new Map();this.abort=new AbortController();this.frame=0;
    root.innerHTML='<div class="interactive-map-viewport" tabindex="0" role="group" aria-label="Интерактивная карта. Стрелки — перемещение, плюс и минус — масштаб, Home — весь мир."><img class="interactive-map-land" src="/static/world.svg" alt="" draggable="false"><div class="interactive-map-markers"></div></div><div class="interactive-map-tools"><button type="button" data-map-action="out" aria-label="Уменьшить карту">−</button><button type="button" data-map-action="reset" aria-label="Показать весь мир">◎</button><button type="button" data-map-action="in" aria-label="Увеличить карту">+</button></div><span class="interactive-map-scale" aria-live="off"></span><div class="interactive-map-picker" hidden></div>';
    this.viewport=root.querySelector('.interactive-map-viewport');this.land=root.querySelector('.interactive-map-land');this.markers=root.querySelector('.interactive-map-markers');this.picker=root.querySelector('.interactive-map-picker');
    const listen=(el,type,fn,opts={})=>el.addEventListener(type,fn,{...opts,signal:this.abort.signal});
    listen(this.viewport,'pointerdown',e=>this.down(e));
    listen(this.viewport,'pointermove',e=>this.move(e));
    for(const type of ['pointerup','pointercancel','lostpointercapture'])listen(this.viewport,type,e=>this.up(e));
    listen(this.viewport,'wheel',e=>{e.preventDefault();const p=this.local(e);this.zoom(this.scale*Math.exp(-Math.max(-100,Math.min(100,e.deltaY))*.006),p.x,p.y);},{passive:false});
    listen(this.viewport,'dblclick',e=>{if(e.target.closest('button'))return;const p=this.local(e);this.zoom(this.scale*1.7,p.x,p.y);});
    listen(this.viewport,'keydown',e=>{
      if(e.target!==this.viewport)return;
      const moves={ArrowLeft:[55,0],ArrowRight:[-55,0],ArrowUp:[0,55],ArrowDown:[0,-55]};
      if(moves[e.key]){e.preventDefault();this.tx+=moves[e.key][0];this.ty+=moves[e.key][1];this.closePicker();this.draw();}
      else if(['+','=','-','Home'].includes(e.key)){e.preventDefault();if(e.key==='Home')this.reset();else this.zoom(this.scale*(e.key==='-'?1/1.5:1.5));}
    });
    listen(root,'click',e=>{
      const action=e.target.closest('[data-map-action]')?.dataset.mapAction;
      if(action==='reset')this.reset();else if(action)this.zoom(this.scale*(action==='in'?1.5:1/1.5));
    });
    this.resize(saved);
    this.resizeObserver=new ResizeObserver(()=>this.resize(this.snapshot()));this.resizeObserver.observe(this.viewport);
  }
  local(e){const r=this.viewport.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
  snapshot(){return{scale:this.scale,centerX:this.width?(this.width/2-this.tx)/(this.width*this.scale):.5,centerY:this.width?(this.height/2-this.ty)/(this.width*.5*this.scale):.5};}
  resize(saved){
    const w=this.viewport.clientWidth,h=this.viewport.clientHeight;if(!w||!h)return;
    this.width=w;this.height=h;
    this.tx=w/2-(saved?.centerX??.5)*w*this.scale;
    this.ty=h/2-(saved?.centerY??.5)*(w/2)*this.scale;
    this.draw();
  }
  clamp(){
    this.scale=Math.min(32,Math.max(1,this.scale));
    const w=this.width*this.scale,h=w/2;
    this.tx=w<=this.width?(this.width-w)/2:Math.max(this.width-w,Math.min(0,this.tx));
    this.ty=h<=this.height?(this.height-h)/2:Math.max(this.height-h,Math.min(0,this.ty));
  }
  zoom(scale,x=this.width/2,y=this.height/2){
    const next=Math.max(1,Math.min(32,scale)),ratio=next/this.scale;
    this.tx=x-(x-this.tx)*ratio;this.ty=y-(y-this.ty)*ratio;this.scale=next;this.closePicker();this.draw();
  }
  reset(){this.scale=1;this.tx=0;this.ty=(this.height-this.width/2)/2;this.closePicker();this.draw();}
  down(e){
    if(e.target.closest('button')||e.button>0)return;
    this.closePicker();this.viewport.focus({preventScroll:true});
    this.points.set(e.pointerId,this.local(e));this.viewport.setPointerCapture(e.pointerId);this.viewport.classList.add('dragging');
  }
  move(e){
    if(!this.points.has(e.pointerId))return;
    const before=[...this.points.values()];const old=this.points.get(e.pointerId),next=this.local(e);this.points.set(e.pointerId,next);
    const after=[...this.points.values()];
    if(before.length>=2){
      const midpoint=a=>({x:(a[0].x+a[1].x)/2,y:(a[0].y+a[1].y)/2});
      const distance=a=>Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y);
      const b=midpoint(before),a=midpoint(after),d=distance(before);
      const s=Math.min(32,Math.max(1,this.scale*(d>1?distance(after)/d:1))),ratio=s/this.scale;
      this.tx=a.x-(b.x-this.tx)*ratio;this.ty=a.y-(b.y-this.ty)*ratio;this.scale=s;
    }else{this.tx+=next.x-old.x;this.ty+=next.y-old.y;}
    this.queueDraw();
  }
  up(e){this.points.delete(e.pointerId);if(!this.points.size)this.viewport.classList.remove('dragging');}
  queueDraw(){if(!this.frame)this.frame=requestAnimationFrame(()=>{this.frame=0;this.draw();});}
  closePicker(){this.picker.hidden=true;}
  draw(){
    this.clamp();
    this.land.style.width=this.width+'px';this.land.style.height=this.width/2+'px';
    this.land.style.transform=`translate(${this.tx}px,${this.ty}px) scale(${this.scale})`;
    const projected=this.cities.map(city=>({city,x:this.tx+(Number(city.lng)+180)/360*this.width*this.scale,y:this.ty+(90-Number(city.lat))/180*(this.width/2)*this.scale}));
    // Union nearby hit areas. Even a group spanning several cities has one target.
    const groups=projected.map(p=>[p]);let merged=true;
    while(merged){merged=false;outer:for(let i=0;i<groups.length;i++)for(let j=i+1;j<groups.length;j++){
      if(groups[i].some(a=>groups[j].some(b=>Math.abs(a.x-b.x)<64&&Math.abs(a.y-b.y)<66))){groups[i].push(...groups[j]);groups.splice(j,1);merged=true;break outer;}
    }}
    const focusKey=document.activeElement?.dataset?.mapKey;
    this.markers.replaceChildren();
    for(const group of groups){
      const visible=group.filter(p=>p.x>=22&&p.x<=this.width-22&&p.y>=22&&p.y<=this.height-36);if(!visible.length)continue;
      const x=visible.reduce((v,p)=>v+p.x,0)/visible.length,y=visible.reduce((v,p)=>v+p.y,0)/visible.length;
      const button=document.createElement('button');button.type='button';button.className='interactive-map-marker';
      button.dataset.mapKey=group.map(p=>p.city.city_id).sort().join(',');button.style.left=x+'px';button.style.top=y+'px';
      const names=group.map(p=>p.city.city).join(', ');button.setAttribute('aria-label',group.length>1?'Выбрать город: '+names:'Открыть '+names);button.title=names;
      const pin=document.createElement('span');pin.className='map-pin';pin.textContent=group.length>1?String(group.length):'◆';
      const label=document.createElement('span');label.className='map-pin-label';label.textContent=group.length>1?'Выбрать город':group[0].city.city;
      button.append(pin,label);button.addEventListener('click',()=>group.length>1?this.showPicker(group,button):this.onSelect(group[0].city.city_id));
      this.markers.append(button);if(focusKey===button.dataset.mapKey)button.focus({preventScroll:true});
    }
    this.root.querySelector('.interactive-map-scale').textContent=this.scale.toFixed(1)+'×';
    this.root.querySelector('[data-map-action="out"]').disabled=this.scale<=1;
    this.root.querySelector('[data-map-action="in"]').disabled=this.scale>=32;
    this.onChange?.(this.snapshot());
  }
  showPicker(group,trigger){
    this.picker.replaceChildren();const title=document.createElement('strong');title.textContent='Выбери город';this.picker.append(title);
    for(const p of group){const b=document.createElement('button');b.type='button';b.textContent=p.city.city+' →';b.dataset.clusterCity=p.city.city_id;b.onclick=()=>this.onSelect(p.city.city_id);this.picker.append(b);}
    const close=document.createElement('button');close.type='button';close.className='map-picker-close';close.textContent='Закрыть';close.onclick=()=>{this.closePicker();trigger.focus();};this.picker.append(close);
    this.picker.hidden=false;this.picker.querySelector('button')?.focus({preventScroll:true});
    this.picker.onkeydown=e=>{if(e.key==='Escape'){e.stopPropagation();close.click();}};
  }
  destroy(){cancelAnimationFrame(this.frame);this.abort.abort();this.resizeObserver.disconnect();this.points.clear();}
}
window.CorporationAtlas=CorporationAtlas;
