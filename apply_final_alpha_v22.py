from pathlib import Path
import re, shutil
from datetime import datetime

ROOT=Path.cwd(); APP=ROOT/'app.py'; WEB=ROOT/'web'; V22=WEB/'v22.js'
def die(msg): print('\n[ERROR]',msg); raise SystemExit(1)
if not APP.exists(): die('app.py не найден. Запусти из корня проекта Corporation.')
if not WEB.exists(): die('Папка web не найдена.')
stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
backup=ROOT/f'backup_before_alpha_v22_{stamp}'; backup.mkdir(exist_ok=True)
shutil.copy2(APP, backup/'app.py')
for n in ('v20.js','app.js','index.html','style.css'):
    p=WEB/n
    if p.exists(): shutil.copy2(p, backup/n)
src=APP.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global src
    if new in src: print('[OK]',label,'уже применено'); return
    if old not in src: die(f'Не найден фрагмент: {label}')
    src=src.replace(old,new,1); print('[OK]',label)

def replace_function(name,new_code):
    global src
    pat=re.compile(rf'^def {re.escape(name)}\([^\n]*\):\n(?:(?:^[ \t].*\n)|(?:^\s*\n))*', re.M)
    m=pat.search(src)
    if not m: die(f'Не найдена функция {name}()')
    src=src[:m.start()]+new_code.strip()+'\n\n\n'+src[m.end():]
    print('[OK] функция',name)

replace_once('REAL_ESTATE_DAILY_GROWTH = 0.00015', '''REAL_ESTATE_GROWTH_INTERVAL = 12 * 60 * 60
REAL_ESTATE_GROWTH_STEP = 0.01
REAL_ESTATE_DAILY_GROWTH = (1 + REAL_ESTATE_GROWTH_STEP) ** 2 - 1''','рост капитализации недвижимости')

start_marker='# === CORPORATION V20.1: REAL ESTATE BALANCE'
end_marker='# ============================================================================'
start=src.find(start_marker)
if start<0: die('Не найден блок REAL ESTATE BALANCE')
end=src.find(end_marker,start)
if end<0: die('Не найден конец блока REAL ESTATE BALANCE')
end += len(end_marker)
new_balance='''# === CORPORATION V22: FINAL ALPHA REAL ESTATE BALANCE ========================
# Недвижимость — премиальный актив для состоятельных игроков.
# Базовая доходность растёт от ~3.2%/ч до ~4.8%/ч в зависимости от стоимости.
def _rebalance_real_estate_v22():
    prices = [float(p["price"]) for p in REAL_ESTATE.values()]
    if not prices:
        return
    import math
    lo, hi = min(prices), max(prices)
    log_lo, log_hi = math.log(max(lo, 1.0)), math.log(max(hi, 1.0))
    span = max(log_hi - log_lo, 1e-9)
    for prop in REAL_ESTATE.values():
        price = float(prop["price"])
        score = (math.log(max(price, 1.0)) - log_lo) / span
        score = min(1.0, max(0.0, score))
        hourly_yield = 0.032 + 0.016 * score
        prop["base_rent_hour"] = round(price * hourly_yield, 2)
        prop["target_hourly_yield"] = hourly_yield

_rebalance_real_estate_v22()
# ============================================================================'''
src=src[:start]+new_balance+src[end:]; print('[OK] баланс недвижимости')

replace_function('_publish_market_news_conn', r'''def _publish_market_news_conn(conn, published_at):
    sentiment = "good" if random.random() < 0.5 else "bad"
    eligible = _eligible_news_stocks(conn, sentiment)
    stock_ids = eligible or [sid for sid in MARKET_NEWS_TEMPLATES if sid in STOCKS]
    last = conn.execute("SELECT stock_id,title FROM market_news ORDER BY published_at DESC,id DESC LIMIT 1").fetchone()
    last_stock_id = str(last["stock_id"]) if last else ""
    candidates = [sid for sid in stock_ids if sid != last_stock_id]
    if candidates:
        stock_ids = candidates
    stock_id = random.choice(stock_ids)
    recent_titles = {str(r["title"]) for r in conn.execute("SELECT title FROM market_news WHERE stock_id=? ORDER BY published_at DESC,id DESC LIMIT 6", (stock_id,)).fetchall()}
    templates = MARKET_NEWS_TEMPLATES[stock_id][sentiment]
    fresh_templates = [tpl for tpl in templates if tpl[0] not in recent_titles]
    template = random.choice(fresh_templates or templates)
    stock = conn.execute("SELECT current_price,min_price,max_price FROM stocks WHERE id=?", (stock_id,)).fetchone()
    current=float(stock["current_price"])
    if sentiment=="good":
        max_room=max(0.0,float(stock["max_price"])/current-1.0)
    else:
        max_room=max(0.0,1.0-float(stock["min_price"])/current)
    upper=min(MARKET_NEWS_MAX_IMPACT,max_room)
    lower=min(MARKET_NEWS_MIN_IMPACT,upper)
    impact=random.uniform(lower,upper) if upper>0 else 0.0
    if impact < MARKET_NEWS_MIN_IMPACT and eligible:
        impact=MARKET_NEWS_MIN_IMPACT
    signed=impact if sentiment=="good" else -impact
    conn.execute("INSERT INTO market_news(stock_id,sentiment,title,article,photo,published_at,impact_at,impact_percent) VALUES(?,?,?,?,?,?,?,?)", (stock_id,sentiment,template[0],template[1],MARKET_NEWS_TEMPLATES[stock_id]["photo"],int(published_at),int(published_at)+MARKET_NEWS_REACTION_DELAY,float(signed)))''')

replace_function('property_capitalization_from_row', r'''def property_capitalization_from_row(row, now=None):
    if not row:
        return 0.0
    now = int(now or time.time())
    purchase_price = float(row["purchase_price"])
    elapsed = max(0, now - int(row["purchased_at"]))
    growth_steps = int(elapsed // REAL_ESTATE_GROWTH_INTERVAL)
    market_value = purchase_price * ((1 + REAL_ESTATE_GROWTH_STEP) ** growth_steps)
    upgrades_value = 0.0
    for key, cfg in REAL_ESTATE_UPGRADES.items():
        if int(row[key] or 0) > 0:
            upgrades_value += purchase_price * float(cfg["cost_rate"])
    return round(market_value + upgrades_value, 2)''')

replace_function('property_payload', r'''def property_payload(uid):
    now = int(time.time())
    with closing(db()) as conn:
        owned_rows = {r["property_id"]: r for r in conn.execute("SELECT * FROM real_estate_holdings WHERE user_id=?", (uid,)).fetchall()}
    result = []
    for pid, prop in REAL_ESTATE.items():
        row = owned_rows.get(pid)
        owned = row is not None
        if owned:
            purchase_price=float(row["purchase_price"])
            elapsed=max(0,now-int(row["purchased_at"]))
            growth_steps=int(elapsed//REAL_ESTATE_GROWTH_INTERVAL)
            current_value=purchase_price*((1+REAL_ESTATE_GROWTH_STEP)**growth_steps)
            rent=prop["base_rent_hour"]*property_upgrade_multiplier(row)
            upgrades={key:bool(int(row[key] or 0)) for key in REAL_ESTATE_UPGRADES}
            next_growth_in=REAL_ESTATE_GROWTH_INTERVAL-(elapsed%REAL_ESTATE_GROWTH_INTERVAL)
        else:
            purchase_price=float(prop["price"]); current_value=float(prop["price"])
            rent=float(prop["base_rent_hour"])
            upgrades={key:False for key in REAL_ESTATE_UPGRADES}
            growth_steps=0; next_growth_in=REAL_ESTATE_GROWTH_INTERVAL
        upgrade_info=[]
        for key,cfg in REAL_ESTATE_UPGRADES.items():
            upgrade_info.append({"id":key,"name":cfg["name"],"owned":upgrades[key],"cost":round(purchase_price*cfg["cost_rate"],2),"income_bonus_percent":round(cfg["income_bonus"]*100)})
        hourly_yield_percent=(rent/purchase_price*100) if purchase_price>0 else 0
        annual_yield_percent=hourly_yield_percent*8760
        capitalization=property_capitalization_from_row(row,now) if owned else float(prop["price"])
        result.append({"id":pid,**prop,"owned":owned,"purchase_price":round(purchase_price,2),"current_value":round(current_value,2),"capitalization":round(capitalization,2),"sell_price":round(capitalization,2) if owned else 0,"rent_hour":round(rent,2),"hourly_yield_percent":round(hourly_yield_percent,3),"annual_yield_percent":round(annual_yield_percent,2),"growth_12h_percent":round(REAL_ESTATE_GROWTH_STEP*100,2),"growth_steps":growth_steps,"next_growth_in_seconds":int(next_growth_in),"upgrades":upgrade_info})
    return result''')

old='''@api.get("/api/real-estate")
def real_estate(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return {"properties": property_payload(uid), "daily_growth_percent": round(REAL_ESTATE_DAILY_GROWTH * 100, 3)}'''
new='''@api.get("/api/real-estate")
def real_estate(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):
    uid = auth(x_telegram_init_data, x_user_id); sync_passive_income(uid); return {"properties": property_payload(uid), "growth_12h_percent": round(REAL_ESTATE_GROWTH_STEP * 100, 2), "growth_interval_seconds": REAL_ESTATE_GROWTH_INTERVAL}'''
replace_once(old,new,'API недвижимости')

replace_function('index', r'''def index():
    path = os.path.join(WEB_DIR, "index.html")
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    scripts = ['<script src="/static/v20.js?v=210"></script>','<script src="/static/v22.js?v=220"></script>']
    for tag in scripts:
        if tag not in html:
            html = html.replace("</body>", tag + "\n</body>")
    return HTMLResponse(html, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0","Pragma":"no-cache","Expires":"0"})''')

src=src.replace('"version": "v21.1"','"version": "v22-final-alpha"')
APP.write_text(src,encoding='utf-8')

V22.write_text(r'''(() => {
  if(!document.getElementById('corporation-v22-style')){
    const s=document.createElement('style'); s.id='corporation-v22-style';
    s.textContent=`.corp-v22-refresh{position:fixed;top:calc(10px + env(safe-area-inset-top));right:12px;width:38px;height:38px;border-radius:50%;border:1px solid rgba(255,255,255,.16);background:rgba(18,18,20,.88);color:#f1c94f;z-index:1400;display:grid;place-items:center;font-size:20px;font-weight:900;box-shadow:0 10px 28px rgba(0,0,0,.32);backdrop-filter:blur(12px)}.corp-v22-refresh:active{transform:scale(.94)}.corp-v22-refresh.loading{animation:v22spin .7s linear infinite}@keyframes v22spin{to{transform:rotate(360deg)}}.corp-v22-news-livebar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;margin:0 0 12px;border-radius:14px;background:linear-gradient(135deg,rgba(241,201,79,.10),rgba(255,255,255,.025));border:1px solid rgba(241,201,79,.20);font-size:12px}.corp-v22-live-label{display:flex;align-items:center;gap:7px;font-weight:900}.corp-v22-live-dot{width:8px;height:8px;border-radius:50%;background:#ef4545;animation:v22pulse 1.7s infinite}@keyframes v22pulse{70%{box-shadow:0 0 0 7px rgba(239,69,69,0)}}.corp-v22-news-time{opacity:.62;font-weight:700}`; document.head.appendChild(s);
  }
  function refresh(){if(document.querySelector('.corp-v22-refresh'))return;const b=document.createElement('button');b.className='corp-v22-refresh';b.type='button';b.title='Обновить баланс, статистику, рейтинг и котировки';b.textContent='↻';b.onclick=()=>{b.classList.add('loading');b.disabled=true;const u=new URL(location.href);u.searchParams.set('_refresh',Date.now());location.replace(u)};document.body.appendChild(b)}
  function news(){const c=document.querySelector('#content');if(!c)return;const t=(c.innerText||'').toLowerCase();if(!(t.includes('новост')&&(t.includes('рын')||t.includes('акци'))))return;if(c.querySelector('.corp-v22-news-livebar'))return;const x=document.createElement('div');x.className='corp-v22-news-livebar';x.innerHTML='<span class="corp-v22-live-label"><i class="corp-v22-live-dot"></i> LIVE · РЫНОК</span><span class="corp-v22-news-time">лента активна</span>';c.prepend(x)}
  refresh(); news(); const o=new MutationObserver(()=>{refresh();news()});o.observe(document.documentElement,{subtree:true,childList:true});setInterval(()=>{const e=document.querySelector('.corp-v22-news-time');if(e)e.textContent='лента активна · '+new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})},15000);
})();''',encoding='utf-8')
print('\n=== CORPORATION v22 FINAL ALPHA ===')
print('Обновление применено. Backup:',backup.name)
print('База данных/Railway Volume не затрагиваются.')
