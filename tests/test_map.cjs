/* Run with a local UI server at MAP_ORIGIN (default http://127.0.0.1:8765).
   npm install playwright; npx playwright install chromium */
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox','--disable-gpu']});
 const page=await browser.newPage({viewport:{width:390,height:844},hasTouch:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=path.resolve(__dirname,'../web');
 // Standalone UI fixture uses actual local map code and asset, no external services.
 await page.route('http://atlas.test/**',async route=>{
   const u=new URL(route.request().url());
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:18px;background:#0c1015;color:white;font-family:Arial}button{cursor:pointer}</style><link rel="stylesheet" href="/interactive_map.css"><div id="map" class="interactive-atlas"></div><script src="/interactive_map.js"></script>'});
   const name=u.pathname==='/static/world.svg'?'world.svg':u.pathname.slice(1);
   await route.fulfill({path:path.join(base,name),contentType:name.endsWith('.js')?'text/javascript; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'image/svg+xml'});
 });
 await page.goto('http://atlas.test/');
 await page.evaluate(()=>{
  window.selected=[];
  window.cities=[{city_id:'london',city:'Лондон',lat:51.5074,lng:-.1278},{city_id:'paris',city:'Париж',lat:48.8566,lng:2.3522},{city_id:'barcelona',city:'Барселона',lat:41.3851,lng:2.1734},{city_id:'moscow',city:'Москва',lat:55.7558,lng:37.6173},{city_id:'egorlyk',city:'Егорлык',lat:45.5853,lng:41.865},{city_id:'newyork',city:'Нью-Йорк',lat:40.7128,lng:-74.006}];
  window.atlas=new CorporationAtlas(document.querySelector('#map'),cities,{onSelect:id=>selected.push(id)});
 });
 await page.locator('[data-city="london"]').click();await page.locator('[data-cluster-city="london"]').click();
 assert.equal(await page.evaluate(()=>selected.at(-1)),'london');
 await page.locator('.map-picker-close').click();
 await page.locator('[data-city="paris"]').click();await page.locator('[data-cluster-city="paris"]').click();
 assert.equal(await page.evaluate(()=>selected.at(-1)),'paris');await page.locator('.map-picker-close').click();
 for(let i=0;i<3;i++)await page.locator('[data-map-action="in"]').click();
 const londonAnchor=await page.locator('[data-city="london"]').evaluate(e=>({left:e.style.left,top:e.style.top}));
 const before=await page.evaluate(()=>atlas.snapshot());
 const box=await page.locator('.interactive-map-viewport').boundingBox();
 await page.mouse.move(box.x+70,box.y+220);await page.mouse.down();await page.mouse.move(box.x+130,box.y+240,{steps:8});await page.mouse.up();
 const after=await page.evaluate(()=>atlas.snapshot());assert.notEqual(before.centerX,after.centerX);
 assert.deepEqual(await page.locator('[data-city="london"]').evaluate(e=>({left:e.style.left,top:e.style.top})),londonAnchor,'city coordinate stays fixed on the map plane');
 const scale=after.scale;await page.mouse.wheel(0,-100);assert(await page.evaluate(()=>atlas.scale)>scale);
 // Real Chromium touch events: two-pointer pinch changes scale, then one-finger pan.
 const cdp=await page.context().newCDPSession(page);const x=box.x+170,y=box.y+190;
 const point=(id,x,y)=>({id,x,y,radiusX:2,radiusY:2,force:1});
 const oldScale=await page.evaluate(()=>atlas.scale);
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point(1,x-20,y),point(2,x+20,y)]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[point(1,x-60,y),point(2,x+60,y)]});
 await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 assert(await page.evaluate(()=>atlas.scale)>oldScale);
 assert.equal(await page.evaluate(()=>selected.length),2,'drag/pinch must not open a city');
 const saved=await page.evaluate(()=>atlas.snapshot());
 await page.evaluate(s=>{atlas.destroy();atlas=new CorporationAtlas(document.querySelector('#map'),cities,{saved:s,onSelect:id=>selected.push(id)});},saved);
 const restored=await page.evaluate(()=>atlas.snapshot());assert(Math.abs(restored.centerX-saved.centerX)<.001);assert.equal(restored.scale,saved.scale);
 await page.locator('[data-map-action="reset"]').click();assert.equal(await page.evaluate(()=>atlas.scale),1);
 for(const width of [320,390,768]){
  await page.setViewportSize({width,height:844});await page.evaluate(()=>atlas.resize(atlas.snapshot()));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const rects=await page.locator('.interactive-map-marker').evaluateAll(es=>es.map(e=>{let r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height};}));
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
   const a=rects[i],b=rects[j];assert(a.x+a.w<=b.x||b.x+b.w<=a.x||a.y+a.h<=b.y||b.y+b.h<=a.y,'marker hit areas overlap');
  }
 }
 await page.setViewportSize({width:390,height:844});await page.locator('[data-map-action="reset"]').click();
 await page.locator('.interactive-map-viewport').focus();await page.keyboard.press('+');assert(await page.evaluate(()=>atlas.scale)>1);await page.keyboard.press('Home');assert.equal(await page.evaluate(()=>atlas.scale),1);
 await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 if(process.env.MAP_SCREENSHOT)await page.screenshot({path:process.env.MAP_SCREENSHOT});
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS: cluster city selection, mouse drag, wheel, Chromium touch pinch, no accidental navigation, camera restoration, 3 widths, no overlapping targets, keyboard.');
})().catch(e=>{console.error(e);process.exit(1)});
