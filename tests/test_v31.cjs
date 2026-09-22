const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const base=path.join(__dirname,'../web');
(async()=>{
 let calls=0,fail=false,renderFail=false,resolvePurchase,button,notice,tabClicks=0;
 const overlay={classList:{add(v){assert.equal(v,'hidden')}}};
 const content={style:{minHeight:''},getBoundingClientRect:()=>({height:900})};
 const body={append(b){button=b}};
 const nodes={'#modal':overlay,'#modalText':body,'#content':content,'.tab[data-page="businesses"]':{click(){tabClicks++}}};
 const ctx={window:{scrollY:240,scrollTo(){}},document:{querySelector:s=>nodes[s],createElement:()=>({})},state:{business_catalog:[{id:'coffee',name:'Кофейня'}]},businessView28:'catalog',page:'businesses',actionBusy28:false,console:{error(){}},encodeURIComponent,
  modal(title,text){notice={title,text};button=null},async render(){if(renderFail)throw Error('render')},
  api:async()=>{calls++;if(fail)throw Error('Недостаточно денег');await new Promise(r=>resolvePurchase=r);return {business_catalog:[{id:'coffee',name:'Кофейня'}],businesses:[{id:'coffee:1',owned:true}]}}};
 vm.createContext(ctx);
 const stable=fs.readFileSync(path.join(base,'instances_v28.js'),'utf8').match(/async function stableAction28\(fn\)\{[\s\S]*?\n\}/)[0];vm.runInContext(stable,ctx);
 vm.runInContext(fs.readFileSync(path.join(base,'v31.js'),'utf8'),ctx);
 const purchase=ctx.window.buyBusiness('coffee');await ctx.window.buyBusiness('coffee');assert.equal(calls,1,'duplicate click blocked');assert.equal(notice,undefined,'no success before server response');
 resolvePurchase();await purchase;
 assert.equal(notice.title,'Бизнес куплен');assert(notice.text.includes('Кофейня'));assert(notice.text.includes('Мои бизнесы'));assert.equal(ctx.actionBusy28,false);
 button.onclick();assert.equal(ctx.businessView28,'mine');assert.equal(tabClicks,1);
 fail=true;await ctx.window.buyBusiness('coffee');assert.equal(notice.title,'Покупка не выполнена');assert.equal(button,null);assert.equal(ctx.actionBusy28,false);
 fail=false;renderFail=true;const p2=ctx.window.buyBusiness('coffee');resolvePurchase();await p2;assert.equal(notice.title,'Бизнес куплен','render failure does not imply transaction failure');
 // Execute the actual atlas wheel callback with and without Ctrl.
 const map=fs.readFileSync(path.join(base,'interactive_map.js'),'utf8');
 const callback=map.match(/listen\(this.viewport,'wheel',(e=>\{.*?\}),\{passive:false\}\);/)[1];
 for(const ctrlKey of [false,true]){
  let prevented=false,zoomed=false;
  const wheelCtx={Math,scale:2,local:()=>({x:100,y:100}),zoom(){zoomed=true}};
  const invoke=vm.runInNewContext('(function(){return '+callback+'})',{}).call(wheelCtx);
  invoke({ctrlKey,deltaY:-80,preventDefault(){prevented=true}});
  assert.equal(prevented,ctrlKey);assert.equal(zoomed,ctrlKey);
 }
 console.log('PASS: purchase acknowledgement, failed purchase, duplicate click, rendering failure, my-business navigation, normal wheel passthrough and Ctrl-wheel map zoom.');
})().catch(e=>{console.error(e);process.exit(1)});
