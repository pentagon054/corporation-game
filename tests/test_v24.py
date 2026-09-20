import os,tempfile,unittest,time,json,hmac,hashlib
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor
os.environ['APP_ENV']='test';os.environ['ALLOW_DEV_AUTH']='1'
os.environ['DB_PATH']=tempfile.mktemp(suffix='.db')
import app, market_v24
from fastapi.testclient import TestClient

class UpdateTests(unittest.TestCase):
 def setUp(self):
  app._rate_buckets.clear();app.ensure_player(999001)
  self.c=TestClient(app.api,headers={'X-User-Id':'999001'})
 def signed(self,uid,age=0):
  d={'auth_date':str(int(time.time())-age),'user':json.dumps({'id':uid})}
  key=hmac.new(b'WebAppData',app.BOT_TOKEN.encode(),hashlib.sha256).digest()
  d['hash']=hmac.new(key,'\n'.join(f'{k}={v}' for k,v in sorted(d.items())).encode(),hashlib.sha256).hexdigest()
  return urlencode(d)
 def test_signed_admin_allowlist(self):
  old=app.BOT_TOKEN;admins=app.ADMIN_IDS;app.BOT_TOKEN='test-token';app.ADMIN_IDS={12345}
  os.environ['ALLOW_DEV_AUTH']='0'
  try:
   c=TestClient(app.api)
   self.assertEqual(c.get('/api/admin/overview',headers={'X-Telegram-Init-Data':self.signed(67890)}).status_code,403)
   self.assertEqual(c.get('/api/admin/overview',headers={'X-Telegram-Init-Data':self.signed(12345)}).status_code,200)
   self.assertEqual(c.get('/api/state',headers={'X-Telegram-Init-Data':self.signed(12345,90000)}).status_code,401)
   self.assertEqual(c.get('/api/state',headers={'X-User-Id':'12345'}).status_code,400)
   forged=self.signed(67890).replace('67890','12345')
   self.assertEqual(c.get('/api/admin/overview',headers={'X-Telegram-Init-Data':forged}).status_code,401)
  finally:app.BOT_TOKEN=old;app.ADMIN_IDS=admins;os.environ['ALLOW_DEV_AUTH']='1'
 def test_bounded_body_chunked(self):
  def chunks():
   for _ in range(100):yield b'x'*1000
  r=self.c.post('/api/rename',content=chunks(),headers={'Content-Type':'application/json'})
  self.assertEqual(r.status_code,413)
 def test_no_dev_auth_in_production(self):
  os.environ['APP_ENV']='production'
  try:self.assertEqual(self.c.get('/api/state').status_code,400)
  finally:os.environ['APP_ENV']='test'
 def test_new_stocks_and_news(self):
  rows=self.c.get('/api/stocks').json()
  for sid in ['apple','google','intel']:
   self.assertEqual(len(app.MARKET_NEWS_TEMPLATES[sid]['good']),3)
   self.assertEqual(len(app.MARKET_NEWS_TEMPLATES[sid]['bad']),3)
   self.assertEqual(self.c.get('/api/stocks/'+sid).status_code,200)
 def test_rank_beyond_20_and_privacy(self):
  for i in range(35):app.ensure_player(70000+i)
  rows=self.c.get('/api/rating').json()
  self.assertGreater(len(rows),20);self.assertIn(999001,[r['user_id'] for r in rows])
  self.assertTrue(all('username' not in r for r in rows))
 def test_parallel_sale_only_once(self):
  with app.closing(app.db()) as conn:
   conn.execute('DELETE FROM businesses WHERE user_id=999001');conn.execute('UPDATE players SET money=20000 WHERE user_id=999001');conn.commit()
  self.assertEqual(self.c.post('/api/business/coffee/buy').status_code,200)
  with ThreadPoolExecutor(max_workers=2) as pool:
   results=list(pool.map(lambda _:self.c.post('/api/business/coffee/sell').status_code,range(2)))
  self.assertEqual(sorted(results),[200,400])
 def test_patterns_bounds_and_growth(self):
  for kind in ['inverse_head_shoulders','ascending_triangle']:
   pts=market_v24.pattern_points(350,180,650,kind)
   self.assertTrue(all(180<=v<=650 for v in pts));self.assertGreaterEqual(pts[-1],350*1.25)
 def test_clock_jitter_and_restart(self):
  now=int(time.time())
  with app.closing(app.db()) as conn:
   app.reset_stock_market_conn(conn,now)
   market_v24.advance(conn,now,app.STOCKS,app._publish_market_news_conn)
   nxt=conn.execute('SELECT next_news_at FROM market_news_state').fetchone()[0]
   self.assertTrue(3600<=nxt-now<=6300)
   count=conn.execute('SELECT count(*) FROM market_news').fetchone()[0]
   market_v24.advance(conn,now,app.STOCKS,app._publish_market_news_conn)
   self.assertEqual(count,conn.execute('SELECT count(*) FROM market_news').fetchone()[0])
   conn.commit()
  app.init_db()
  with app.closing(app.db()) as conn:self.assertEqual(nxt,conn.execute('SELECT next_news_at FROM market_news_state').fetchone()[0])
 def test_chronology_and_history_per_stock(self):
  now=int(time.time());start=now-60*800
  with app.closing(app.db()) as conn:
   app.reset_stock_market_conn(conn,start)
   market_v24.advance(conn,now,app.STOCKS,app._publish_market_news_conn)
   for sid in app.STOCKS:
    rows=conn.execute('SELECT price,created_at FROM stock_history WHERE stock_id=? ORDER BY id',(sid,)).fetchall()
    self.assertGreaterEqual(len(rows),710);self.assertLessEqual(len(rows),720)
    times=[r['created_at'] for r in rows];self.assertEqual(times,sorted(times))
    self.assertEqual(rows[-1]['price'],conn.execute('SELECT current_price FROM stocks WHERE id=?',(sid,)).fetchone()[0])
   conn.commit()
 def test_pattern_lottery_persistence(self):
  class Rng:
   def random(self):return 0
   def choice(self,x):return x[0]
   def uniform(self,a,b):return a
   def randint(self,a,b):return a
   def gauss(self,a,b):return 0
  now=int(time.time())//3600*3600
  with app.closing(app.db()) as conn:
   app.reset_stock_market_conn(conn,now-60)
   conn.execute('UPDATE market_clock SET next_pattern_at=?',(now,))
   conn.execute('UPDATE market_news_state SET next_news_at=?',(now+9999,))
   market_v24.advance(conn,now,app.STOCKS,app._publish_market_news_conn,rng=Rng())
   r=conn.execute('SELECT * FROM market_patterns').fetchall();self.assertEqual(len(r),1)
   sid=r[0]['stock_id'];target=json.loads(r[0]['points'])[-1]
   market_v24.advance(conn,now+2400,app.STOCKS,app._publish_market_news_conn,rng=Rng())
   self.assertEqual(conn.execute('SELECT current_price FROM stocks WHERE id=?',(sid,)).fetchone()[0],target)
   self.assertEqual(conn.execute('SELECT next_pattern_at FROM market_clock').fetchone()[0],now+3600)
   conn.commit()
if __name__=='__main__':unittest.main(verbosity=2)
