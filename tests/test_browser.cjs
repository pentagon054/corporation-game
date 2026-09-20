/* npm install playwright; npx playwright install chromium
   APP_ENV=test ALLOW_DEV_AUTH=1 DB_PATH=/tmp/corp24-ui.db uvicorn app:api --port 8765
   NODE_PATH=... CHROMIUM_PATH=... node tests/test_browser.cjs */
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const assert=require('node:assert/strict');
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
const p=await browser.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.route('https://telegram.org/**',r=>r.fulfill({contentType:'text/javascript',body:''}));
await p.goto('http://127.0.0.1:8765');await p.waitForSelector('.business-card');
for(const width of [320,390,768,1280]){
 await p.setViewportSize({width,height:844});
 const sizes=await p.locator('.tabs .tab').evaluateAll(es=>es.map(e=>{let r=e.getBoundingClientRect();return {y:r.y,x:r.x,right:r.right}}));
 assert(Math.max(...sizes.map(s=>s.y))-Math.min(...sizes.map(s=>s.y))<2,'single nav row');
 assert(sizes[0].x>=0&&sizes.at(-1).right<=width,'all tabs fit');
 assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no horizontal overflow');
}
await p.setViewportSize({width:320,height:568});
await p.locator('[data-page="realestate"]').click();await p.waitForSelector('.city-selector');
for(const city of ['london','paris','barcelona']){
 for(let i=0;i<2;i++){
  await p.locator(`[data-city="${city}"]`).click();await p.waitForSelector('.property-card');
  assert((await p.locator('#content h2').innerText()).includes({london:'Лондон',paris:'Париж',barcelona:'Барселона'}[city]));
  await p.locator('.back-button').click();await p.waitForSelector('.city-selector');
 }
}
for(const level of [1,1,0]){await p.evaluate(d=>zoomMap24(d),level);assert(await p.locator('[data-city="london"]').isVisible());}
await p.locator('[data-page="investments"]').click();await p.waitForSelector('.v21-news-entry');
await p.evaluate(()=>openInvestmentBonds());await p.waitForSelector('[data-buy-bond]');
for(const balance of [999,1000,2819.78,3502.90,0]){
 await p.evaluate(b=>{state.player.money=b;renderHeader();},balance);
 const max=await p.locator('[data-buy-bond="ofz_ru"]').innerText();assert(max.includes(String(Math.floor(balance/1000))));
}
await p.evaluate(()=>openInvestmentStocks());await p.evaluate(()=>openStock('apple'));await p.waitForSelector('.corp-stock-page');
await p.evaluate(()=>corporationToggleStockChart('apple'));
await p.locator('[data-page="investments"]').click();await p.waitForSelector('.v21-news-entry');
await p.locator('.v21-news-entry').click();await p.waitForSelector('.v21-news-page');assert.equal(await p.locator('[data-news-at]').count(),0);
// OHLC buckets respect time, not point counts, and include the previous close.
assert.deepEqual(await p.evaluate(()=>corporationBuildCandles([{created_at:60,price:100},{created_at:120,price:110},{created_at:299,price:90},{created_at:300,price:120}],5)),[
 {created_at:0,open:100,close:90,high:110,low:90},{created_at:300,open:90,close:120,high:120,low:90}]);
await p.locator('[data-page="rating"]').click();await p.waitForSelector('.rank-mine');
const mine=await p.locator('.rank-mine').boundingBox();assert(mine.y>=0&&mine.y<568,'opens at own rank');
await p.locator('.rank-jump button').first().click();await p.locator('.rank-jump button').last().click();
await p.evaluate(()=>modal('test','<img src=x onerror=alert(1)>'));assert.equal(await p.locator('#modalText img').count(),0);
await p.locator('#modalClose').click();
assert.deepEqual(errors,[]);await browser.close();console.log('PASS: 4 widths, single nav row, map cities/zoom, buy-all thresholds, stock/news navigation, OHLC, rank focus, XSS text rendering.');
})().catch(e=>{console.error(e);process.exit(1)});
