/* PLAYWRIGHT_PATH=/path/to/playwright CHROMIUM_PATH=/path/to/chromium node tests/test_instances_v28.cjs */
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const assert=require('node:assert/strict');
const {spawn,execFileSync}=require('node:child_process');
const path=require('node:path'),fs=require('node:fs'),os=require('node:os');
(async()=>{
const root=path.resolve(__dirname,'..'),temp=fs.mkdtempSync(path.join(os.tmpdir(),'corp28-ui-'));
const env={...process.env,APP_ENV:'test',ALLOW_DEV_AUTH:'1',BOT_TOKEN:'test',DB_PATH:path.join(temp,'test.db')};
const server=spawn('python3',['-c',"import app,uvicorn; app.update_stock_market=lambda:None; uvicorn.run(app.api,host='127.0.0.1',port=8765,log_level='error')"],{cwd:root,env,stdio:['ignore','pipe','pipe']});
let browser;
try{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-zygote','--single-process']});
 const p=await browser.newPage({viewport:{width:390,height:844}}),errors=[];p.on('pageerror',e=>{errors.push(e.message);console.error('PAGE:',e.message)});p.on('console',m=>{if(m.type()==='error')console.error('CONSOLE:',m.text())});
 const base='http://127.0.0.1:8765';
 for(let i=0;i<50;i++){try{const r=await p.request.get(base+'/api/state',{headers:{'X-User-Id':'999001'}});if(r.ok())break;}catch{}await new Promise(r=>setTimeout(r,100));}
 execFileSync('python3',['-c',"import os,sqlite3; c=sqlite3.connect(os.environ['DB_PATH']); c.execute('UPDATE players SET money=100000000'); c.commit()"],{env});
 const api=async(url,body)=>{const r=await p.request.post(base+url,{headers:{'X-User-Id':'999001'},...(body?{data:body}:{})});assert(r.ok(),await r.text());return r.json();};
 for(const kind of ['coffee','coffee','taxi','taxi','logistics','logistics'])await api('/api/business/'+kind+'/buy');
 await p.route('https://**/*',r=>r.fulfill({status:200,contentType:'text/javascript',body:''}));
 await p.goto(base);await p.waitForSelector('.business-tabs28').catch(async e=>{console.error((await p.locator('body').innerText()).slice(0,1500));throw e});
 assert(await p.locator('.balance').isVisible());
 for(const width of [320,390,768,1280]){
  await p.setViewportSize({width,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no horizontal overflow');
 }
 await p.setViewportSize({width:390,height:844});
 await p.getByRole('tab',{name:/Мои бизнесы/}).click();assert.equal(await p.locator('.business-card').count(),6);
 for(const kind of ['taxi','logistics']){
  const card=p.locator(`[data-business-key="${kind}"]`),buy=card.locator('.vehicle-row25').first().getByRole('button',{name:'Купить',exact:true});
  for(let i=0;i<3;i++){
   await buy.click();const y=await p.evaluate(()=>scrollY);
   await p.evaluate(kind=>{window.savedFleetNode=document.querySelector(`[data-business-key="${kind}"] .vehicle-row25`);},kind);
   await p.getByRole('button',{name:'Подтвердить',exact:true}).click();
   await p.waitForFunction(()=>!actionBusy28);
   assert(Math.abs(await p.evaluate(()=>scrollY)-y)<2,'fleet scroll stays fixed');
   assert(await p.evaluate(kind=>savedFleetNode===document.querySelector(`[data-business-key="${kind}"] .vehicle-row25`),kind),'fleet DOM retained');
  }
  await buy.click();const y=await p.evaluate(()=>scrollY);await p.getByRole('button',{name:'Отмена',exact:true}).click();await p.waitForFunction(()=>!actionBusy28);assert.equal(await p.evaluate(()=>scrollY),y);
 }
 await p.locator('[data-page="investments"]').click();await p.waitForSelector('.v21-news-entry');assert(!(await p.locator('.balance').isVisible()));assert(!(await p.locator('.hero').isVisible()));
 await p.evaluate(async()=>{await openInvestmentStocks();await openStock('apple');});await p.waitForSelector('.corp-stock-page');
 let posts=0;p.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/api/stocks/'))posts++;});
 await p.getByRole('button',{name:'Купить',exact:true}).click();await p.waitForSelector('.trade-slider28');
 await p.locator('.trade-slider28').evaluate(el=>{el.value='3';el.dispatchEvent(new Event('input',{bubbles:true}));});
 assert.equal(await p.locator('#quantity25').inputValue(),'3');assert.equal(await p.locator('[data-trade-count]').innerText(),'3 шт.');assert.equal(posts,0);
 const expected=await p.evaluate(()=>fmt(stocksCache.find(s=>s.id==='apple').current_price*3));assert.equal(await p.locator('[data-trade-total]').innerText(),expected);
 await p.locator('#quantity25').fill('1.5');assert(await p.getByRole('button',{name:'Подтвердить',exact:true}).isDisabled());
 await p.locator('#quantity25').fill('3');await p.getByRole('button',{name:'Подтвердить',exact:true}).click();await p.waitForFunction(()=>!actionBusy28);assert.equal(posts,1);
 await p.locator('#modalClose').click();
 await p.getByRole('button',{name:'Продать',exact:true}).click();await p.waitForSelector('.trade-slider28');assert.equal(await p.locator('.trade-slider28').getAttribute('max'),'3');
 await p.locator('.trade-slider28').evaluate(el=>{el.value='2';el.dispatchEvent(new Event('input',{bubbles:true}));});assert.equal(posts,1);
 await p.getByRole('button',{name:'Отмена',exact:true}).click();await p.waitForFunction(()=>!actionBusy28);assert.equal(posts,1);
 for(const tab of ['realestate','taxes','statistics','rating']){await p.locator(`[data-page="${tab}"]`).click();assert(!(await p.locator('.balance').isVisible()));await p.waitForTimeout(150);}
 await p.locator('[data-page="businesses"]').click();await p.waitForSelector('.business-tabs28');assert(await p.locator('.balance').isVisible());
 await p.screenshot({path:path.join(temp,'businesses.png'),fullPage:false});
 assert.deepEqual(errors,[]);console.log('PASS: four widths, independent business cards, 3 repeated purchases in each fleet, DOM identity, scroll/cancel, stock slider totals, invalid quantities, one POST only after confirmation, header navigation. Screenshot: '+temp+'/businesses.png');
}finally{await browser?.close();server.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
