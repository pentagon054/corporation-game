/* Run with CORP_JSDOM=/path/to/jsdom node tests/test_frontend.cjs;
   separate test server: DB_PATH=/tmp/corp-ui.db ALLOW_DEV_AUTH=1 uvicorn app:api --port 8765 */
const {JSDOM}=require(process.env.CORP_JSDOM||'jsdom');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../web');
const origin='http://127.0.0.1:8765';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const dom=new JSDOM(fs.readFileSync(root+'/index.html','utf8'),{url:origin,runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,ctx=dom.getInternalVMContext(),errors=[],posts=[];
 w.scrollTo=()=>{};
 const observers=[],NativeObserver=w.MutationObserver;
 w.MutationObserver=class extends NativeObserver{constructor(cb){super(cb);observers.push(this)}};
 w.fetch=async(url,opts)=>{if(opts?.method==='POST')posts.push({url,body:opts.body});return fetch(new URL(url,origin),opts)};
 let raw='1',confirmed=false;
 w.prompt=()=>raw;w.confirm=()=>confirmed;
 w.addEventListener('error',e=>errors.push(e.message));
 const evaluate=s=>vm.runInContext(s,ctx);
 for(const file of ['app.js','v22_1.js','v20.js','v22.js','v22_performance.js','audit_v23.js'])new vm.Script(fs.readFileSync(root+'/'+file,'utf8'),{filename:file}).runInContext(ctx);
 async function settled(test){for(let i=0;i<100;i++){if(test())return;await delay(20)}throw new Error('Timeout waiting for UI');}
 await settled(()=>w.document.querySelector('.business-card'));
 assert.equal(w.document.querySelector('.balance-label').textContent,'СВОБОДНЫЕ ДЕНЬГИ');
 // Navigate with the actual menu handlers.
 w.document.querySelector('[data-page="investments"]').click();
 await settled(()=>w.document.querySelector('.v21-news-entry'));
 await evaluate("openInvestmentStocks()");await evaluate("openStock('tesla')");
 assert(w.document.querySelector('.corp-stock-page'));
 w.document.querySelector('[data-page="investments"]').click();
 await settled(()=>w.document.querySelector('.investment-market-menu'));
 assert(w.document.querySelector('.v21-news-entry'));
 await evaluate("openInvestmentStocks()");await evaluate("openStock('tesla')");
 await evaluate("corporationToggleStockChart('tesla')");
 w.document.querySelector('#corpV221Refresh').click();
 await settled(()=>w.document.querySelector('#corpV221Refresh').disabled===false);
 assert(w.document.querySelector('.corp-stock-page'));
 assert.equal(evaluate('corporationActiveStockId'),'tesla');
 assert.equal(evaluate('corporationStockViewMode'),'candles');
 assert(w.document.querySelector('.quote-period').textContent.includes('предыдущей'));
 // Actual trade handlers, native dialog returns simulated by adapter.
 for(const kind of ['stocks','bonds']){
  const fn=kind==='stocks'?"openTrade('tesla'":"openBondTrade('ofz_ru'";
  raw='1';confirmed=true;await evaluate(fn+",'buy')");
  for(const side of ['buy','sell']){
   for(const value of ['1.5','1abc','-1','0','','1,5','1e2','9007199254740992',null]){
    raw=value;const before=posts.length;await evaluate(fn+`,'${side}')`);assert.equal(posts.length,before,`${kind}/${side}/${value}`);
   }
   raw='1';confirmed=false;let before=posts.length;await evaluate(fn+`,'${side}')`);assert.equal(posts.length,before);
  }
  raw='1';confirmed=true;const before=posts.length;
  await Promise.all([evaluate(fn+",'buy')"),evaluate(fn+",'buy')")]);
  assert.equal(posts.length,before+1,'double click must send one POST');
  assert.equal(JSON.parse(posts.at(-1).body).quantity,1);
 }
 // Maximum valid quantity uses the same validator and exactly one request.
 confirmed=true;let maxBefore=posts.length;
 await evaluate("tradeAllBond('ofz_ru','buy')");assert.equal(posts.length,maxBefore+1);
 maxBefore=posts.length;await evaluate("tradeAllBond('ofz_ru','sell')");assert.equal(posts.length,maxBefore+1);
 // Property rejects before asking for confirmation.
 let confirms=0;w.confirm=()=>{confirms++;return true};
 await evaluate("buyProperty('nonexistent')");
 const catalog=await fetch(origin+'/api/real-estate',{headers:{'X-User-Id':'999001'}}).then(x=>x.json());
 const expensive=catalog.properties.reduce((a,b)=>a.purchase_price>b.purchase_price?a:b);
 const before=posts.length;await evaluate(`buyProperty('${expensive.id}')`);
 assert.equal(confirms,0);assert.equal(posts.length,before);
 // Advance the clock without waiting fifty seconds: countdown must use elapsed time.
 await evaluate('openInvestmentNews()');
 const span=w.document.querySelector('[data-news-at]');assert(span);
 const parse=t=>t.split(':').reduce((a,v)=>60*a+Number(v),0);
 const first=parse(span.textContent),realNow=w.Date.now;
 w.Date.now=()=>realNow()+50000;
 await delay(1100);
 const second=parse(span.textContent);assert(first-second>=50&&first-second<=52,`${first} -> ${second}`);
 w.Date.now=realNow;
 await evaluate('v21BackInvestments()');assert(w.document.querySelector('.v21-news-entry'));
 assert.deepEqual(errors,[]);
 observers.forEach(o=>o.disconnect());dom.window.close();
 console.log('PASS: navigation, detail refresh/candles, 36 invalid trade cases, cancellation, double click, property precheck, elapsed news countdown.');
})().catch(e=>{console.error(e);process.exit(1)});
