"""Persistent, chronological simulated market. All trades use these actual prices."""
import json
import random


def initialize(conn, now):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS market_patterns(stock_id TEXT PRIMARY KEY, started_at INTEGER NOT NULL, points TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS market_clock(id INTEGER PRIMARY KEY, next_pattern_at INTEGER NOT NULL);
    ''')
    conn.execute('INSERT OR IGNORE INTO market_clock VALUES(1,?)', ((now//3600+1)*3600,))


def pattern_points(price, floor, ceiling, kind, rng=random):
    # A bullish head-and-shoulders is the INVERSE formation.
    amplitude=min(price*.12, (price-floor)*.8)
    if kind=='inverse_head_shoulders':
        anchors=[price,price-amplitude*.55,price,price-amplitude,price,price-amplitude*.55,price]
    else:
        top=price+min(price*.05,(ceiling-price)*.12)
        anchors=[price,top,price+(top-price)*.2,top,price+(top-price)*.5,top,price+(top-price)*.8,top]
    target=min(ceiling,anchors[-1]*rng.uniform(1.25,1.40))
    anchors += [target]
    points=[]
    for a,b in zip(anchors,anchors[1:]):
        for step in range(1,6):
            points.append(round(a+(b-a)*step/5,2))
    return points


def advance(conn, now, configs, publish, interval=50*60, rng=random):
    # Bound recovery after long downtime. No invented historical news or windfall backlog.
    cutoff=now-12*3600
    conn.execute('UPDATE stocks SET last_update=? WHERE last_update<?',(cutoff,cutoff))
    conn.execute('DELETE FROM market_patterns WHERE started_at<?',(cutoff,))
    conn.execute('UPDATE market_clock SET next_pattern_at=? WHERE next_pattern_at<?',((now//3600+1)*3600,cutoff))
    conn.execute('UPDATE market_news_state SET next_news_at=? WHERE next_news_at<?',(now,cutoff))
    stocks={r['id']:dict(r) for r in conn.execute('SELECT * FROM stocks') if r['id'] in configs}
    patterns={r['stock_id']:(r['started_at'],json.loads(r['points'])) for r in conn.execute('SELECT * FROM market_patterns')}
    next_news=conn.execute('SELECT next_news_at FROM market_news_state WHERE id=1').fetchone()[0]
    # Shorten any schedule persisted by older releases (previously up to 105 min).
    # Avoid publishing backdated news after an outage or during a frozen season.
    last_news=conn.execute('SELECT MAX(published_at) FROM market_news').fetchone()[0]
    if last_news is not None and next_news>last_news+90*60:
        next_news=max(now, last_news+90*60)
    next_pattern=conn.execute('SELECT next_pattern_at FROM market_clock WHERE id=1').fetchone()[0]
    pending=[dict(r) for r in conn.execute('SELECT * FROM market_news WHERE applied_at=0 ORDER BY impact_at,id')]
    while stocks:
        tick=min(s['last_update']+60 for s in stocks.values())
        impact=min((max(cutoff,n['impact_at']) for n in pending),default=now+1)
        at=min(tick,next_news,next_pattern,impact)
        if at>now:break
        for sid,s in stocks.items():
            if s['last_update']+60>at:continue
            cfg=configs[sid];price=s['current_price'];floor=cfg['min_price'];ceiling=cfg['max_price']
            active=patterns.get(sid)
            if active:
                index=max(0,(at-active[0])//60-1)
                if index<len(active[1]):new=active[1][index]
                else:
                    patterns.pop(sid,None);conn.execute('DELETE FROM market_patterns WHERE stock_id=?',(sid,));active=None
            if not active:
                direction=1 if s['trend']=='up' else -1
                drift=direction*cfg['drift']+(((floor+ceiling)/2-price)/(ceiling-floor))*.006
                new=price*(1+rng.gauss(drift,cfg['volatility']))
            new=round(min(ceiling,max(floor,new)),2)
            trend='up' if new>=price else 'down'
            s.update(current_price=new,last_update=at,trend=trend)
            conn.execute('UPDATE stocks SET current_price=?,last_update=?,trend=? WHERE id=?',(new,at,trend,sid))
            conn.execute('INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)',(sid,new,at))
        if at==next_pattern:
            # Exactly one lottery for the whole market per hour; survives restart.
            if rng.random()<.05:
                eligible=[sid for sid,s in stocks.items() if sid not in patterns and s['current_price']*1.30<=configs[sid]['max_price'] and s['current_price']>configs[sid]['min_price']*1.06]
                if eligible:
                    sid=rng.choice(eligible);s=stocks[sid];cfg=configs[sid]
                    kind=rng.choice(['inverse_head_shoulders','ascending_triangle'])
                    pts=pattern_points(s['current_price'],cfg['min_price'],cfg['max_price'],kind,rng)
                    patterns[sid]=(at,pts)
                    conn.execute('INSERT OR REPLACE INTO market_patterns VALUES(?,?,?)',(sid,at,json.dumps(pts)))
            next_pattern+=3600
        if at==next_news:
            publish(conn,at)
            pending.append(dict(conn.execute('SELECT * FROM market_news ORDER BY id DESC LIMIT 1').fetchone()))
            next_news=at+interval+rng.randint(0,40*60)
        for n in list(pending):
            if max(cutoff,n['impact_at'])>at:continue
            sid=n['stock_id'];s=stocks.get(sid)
            if s:
                before=s['current_price'];cfg=configs[sid]
                after=round(min(cfg['max_price'],max(cfg['min_price'],before*(1+n['impact_percent']))),2)
                pct=after/before-1
                s['current_price']=after
                conn.execute('UPDATE stocks SET current_price=? WHERE id=?',(after,sid))
                conn.execute('INSERT INTO stock_history(stock_id,price,created_at) VALUES(?,?,?)',(sid,after,at))
                conn.execute('UPDATE market_news SET impact_percent=?,price_before=?,price_after=?,applied_at=? WHERE id=?',(pct,before,after,at,n['id']))
                # News is a real shock: invalidate a formation instead of snapping price back.
                patterns.pop(sid,None);conn.execute('DELETE FROM market_patterns WHERE stock_id=?',(sid,))
            else:conn.execute('UPDATE market_news SET applied_at=? WHERE id=?',(at,n['id']))
            pending.remove(n)
    conn.execute('UPDATE market_clock SET next_pattern_at=? WHERE id=1',(next_pattern,))
    conn.execute('UPDATE market_news_state SET next_news_at=? WHERE id=1',(next_news,))
    # Keep 720 observations PER stock, not 720 interleaved global IDs.
    for sid in stocks:
        conn.execute('DELETE FROM stock_history WHERE stock_id=? AND id NOT IN (SELECT id FROM stock_history WHERE stock_id=? ORDER BY created_at DESC,id DESC LIMIT 720)',(sid,sid))
    conn.execute('DELETE FROM market_news WHERE applied_at>0 AND id NOT IN (SELECT id FROM market_news ORDER BY id DESC LIMIT 500)')
