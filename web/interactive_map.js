/* Corporation 25 atlas: city anchors share one transformed plane with the map. */
class CorporationAtlas {
  constructor(root,cities,{onSelect,saved,onChange}={}){
    this.root=root;this.cities=cities;this.onSelect=onSelect;this.onChange=onChange;
    this.scale=saved?.scale||1;this.tx=0;this.ty=0;this.width=0;this.height=0;
    this.points=new Map();this.abort=new AbortController();this.frame=0;this.moved=false;
    root.innerHTML='<div class="interactive-map-viewport" tabindex="0" role="group" aria-label="Интерактивная карта. Города закреплены точками. Стрелки перемещают карту, плюс и минус меняют масштаб."><div class="interactive-map-scene"><img class="interactive-map-land" src="/static/world.svg" alt="" draggable="false"><div class="interactive-map-markers"></div></div></div><div class="interactive-map-tools"><button type="button" data-map-action="out" aria-label="Уменьшить карту">−</button><button type="button" data-map-action="reset" aria-label="Показать весь мир">◎</button><button type="button" data-map-action="in" aria-label="Увеличить карту">+</button></div><span class="interactive-map-scale" aria-live="off"></span><div class="interactive-map-picker" hidden></div>';
    this.viewport=root.querySelector('.interactive-map-viewport');this.scene=root.querySelector('.interactive-map-scene');this.markers=root.querySelector('.interactive-map-markers');this.picker=root.querySelector('.interactive-map-picker');
    this.buildMarkers();
    const listen=(el,type,fn,opts={})=>el.addEventListener(type,fn,{...opts,signal:this.abort.signal});
    listen(this.viewport,'pointerdown',e=>this.down(e));listen(this.viewport,'pointermove',e=>this.move(e));
    for(const type of ['pointerup','pointercancel','lostpointercapture'])listen(this.viewport,type,e=>this.up(e));
    listen(this.viewport,'wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();const p=this.local(e);this.zoom(this.scale*Math.exp(-Math.max(-100,Math.min(100,e.deltaY))*.006),p.x,p.y);},{passive:false});
    listen(this.viewport,'dblclick',e=>{e.preventDefault();if(e.target.closest('button'))return;const p=this.local(e);this.zoom(this.scale*1.7,p.x,p.y);});
    listen(this.viewport,'keydown',e=>{if(e.target!==this.viewport)return;const moves={ArrowLeft:[55,0],ArrowRight:[-55,0],ArrowUp:[0,55],ArrowDown:[0,-55]};if(moves[e.key]){e.preventDefault();this.tx+=moves[e.key][0];this.ty+=moves[e.key][1];this.closePicker();this.draw();}else if(['+','=','-','Home'].includes(e.key)){e.preventDefault();if(e.key==='Home')this.reset();else this.zoom(this.scale*(e.key==='-'?1/1.5:1.5));}});
    listen(root,'click',e=>{const action=e.target.closest('[data-map-action]')?.dataset.mapAction;if(action==='reset')this.reset();else if(action)this.zoom(this.scale*(action==='in'?1.5:1/1.5));});
    this.resize(saved);this.resizeObserver=new ResizeObserver(()=>this.resize(this.snapshot()));this.resizeObserver.observe(this.viewport);
  }
  buildMarkers(){
    this.markers.replaceChildren();
    for(const city of this.cities){
      const button=document.createElement('button');button.type='button';button.className='interactive-map-marker';button.dataset.city=city.city_id;
      button.style.left=((Number(city.lng)+180)/360*100)+'%';button.style.top=((90-Number(city.lat))/180*100)+'%';button.setAttribute('aria-label','Открыть '+city.city);button.title=city.city;
      button.innerHTML='<span class="map-pin"><i></i></span><span class="map-pin-label"></span>';button.querySelector('.map-pin-label').textContent=city.city;
      button.addEventListener('click',e=>{e.stopPropagation();if(this.moved&&e.detail!==0)return;const near=this.nearby(city);near.length>1?this.showPicker(near,button):this.onSelect(city.city_id);});this.markers.append(button);
    }
  }
  nearby(city){const o=this.project(city);return this.cities.filter(c=>{const p=this.project(c);return Math.hypot(p.x-o.x,p.y-o.y)<54;});}
  project(city){return{x:this.tx+(Number(city.lng)+180)/360*this.width*this.scale,y:this.ty+(90-Number(city.lat))/180*(this.width/2)*this.scale};}
  local(e){const r=this.viewport.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
  snapshot(){return{scale:this.scale,centerX:this.width?(this.width/2-this.tx)/(this.width*this.scale):.5,centerY:this.width?(this.height/2-this.ty)/(this.width*.5*this.scale):.5};}
  resize(saved){const w=this.viewport.clientWidth,h=this.viewport.clientHeight;if(!w||!h)return;this.width=w;this.height=h;this.tx=w/2-(saved?.centerX??.5)*w*this.scale;this.ty=h/2-(saved?.centerY??.5)*(w/2)*this.scale;this.draw();}
  clamp(){this.scale=Math.min(6,Math.max(1,this.scale));const w=this.width*this.scale,h=this.width/2*this.scale;this.tx=w<=this.width?(this.width-w)/2:Math.max(this.width-w,Math.min(0,this.tx));this.ty=h<=this.height?(this.height-h)/2:Math.max(this.height-h,Math.min(0,this.ty));}
  zoom(scale,x=this.width/2,y=this.height/2){const next=Math.max(1,Math.min(6,scale)),ratio=next/this.scale;this.tx=x-(x-this.tx)*ratio;this.ty=y-(y-this.ty)*ratio;this.scale=next;this.closePicker();this.draw();}
  reset(){this.scale=1;this.tx=0;this.ty=(this.height-this.width/2)/2;this.closePicker();this.draw();}
  down(e){
    if(e.button>0)return;
    if(!this.points.size){this.moved=false;this.travel=0;}
    this.closePicker();
    const marker=e.target.closest('.interactive-map-marker');
    if(!marker)this.viewport.focus({preventScroll:true});
    this.points.set(e.pointerId,this.local(e));
    // Capture on the marker itself so a stationary tap still opens that city.
    (marker||this.viewport).setPointerCapture(e.pointerId);
    if(this.points.size>1)this.moved=true;
    this.viewport.classList.add('dragging');
  }
  move(e){
    if(!this.points.has(e.pointerId))return;
    const before=[...this.points.values()],old=this.points.get(e.pointerId),next=this.local(e);
    this.travel+=Math.hypot(next.x-old.x,next.y-old.y);
    if(this.travel>6)this.moved=true;
    this.points.set(e.pointerId,next);
    const after=[...this.points.values()];
    if(before.length>=2){
      const midpoint=a=>({x:(a[0].x+a[1].x)/2,y:(a[0].y+a[1].y)/2}),distance=a=>Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y),b=midpoint(before),a=midpoint(after),d=distance(before),s=Math.min(6,Math.max(1,this.scale*(d>1?distance(after)/d:1))),ratio=s/this.scale;
      this.tx=a.x-(b.x-this.tx)*ratio;this.ty=a.y-(b.y-this.ty)*ratio;this.scale=s;
    }else{this.tx+=next.x-old.x;this.ty+=next.y-old.y;}
    this.clamp();this.queueDraw();
  }
  up(e){
    if(!this.points.has(e.pointerId))return;
    if(e.type==='pointercancel'||e.type==='lostpointercapture')this.moved=true;
    this.points.delete(e.pointerId);
    if(!this.points.size)this.viewport.classList.remove('dragging');
    // Retain suppression through the synthetic click; reset at the next gesture.
  }
  queueDraw(){if(!this.frame)this.frame=requestAnimationFrame(()=>{this.frame=0;this.draw();});}
  closePicker(){this.picker.hidden=true;}
  draw(){this.clamp();this.scene.style.width=(this.width*this.scale)+'px';this.scene.style.height=(this.width/2*this.scale)+'px';this.scene.style.setProperty('--inverse-scale','1');this.scene.style.transform=`translate3d(${Math.round(this.tx)}px,${Math.round(this.ty)}px,0)`;this.scene.classList.toggle('detailed',this.scale>=2.25);this.root.querySelector('.interactive-map-scale').textContent=this.scale.toFixed(1)+'×';this.root.querySelector('[data-map-action="out"]').disabled=this.scale<=1;this.root.querySelector('[data-map-action="in"]').disabled=this.scale>=6;this.onChange?.(this.snapshot());}
  showPicker(cities,trigger){this.picker.replaceChildren();const title=document.createElement('strong');title.textContent='Города рядом';this.picker.append(title);for(const city of cities){const b=document.createElement('button');b.type='button';b.dataset.clusterCity=city.city_id;b.textContent=city.city+' →';b.onclick=()=>this.onSelect(city.city_id);this.picker.append(b);}const close=document.createElement('button');close.type='button';close.className='map-picker-close';close.textContent='Закрыть';close.onclick=()=>{this.closePicker();trigger.focus();};this.picker.append(close);this.picker.hidden=false;this.picker.querySelector('button')?.focus({preventScroll:true});}
  destroy(){cancelAnimationFrame(this.frame);this.abort.abort();this.resizeObserver.disconnect();this.points.clear();}
}
window.CorporationAtlas=CorporationAtlas;
