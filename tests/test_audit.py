import os
os.environ['APP_ENV']='test'
"""Regression tests use a fresh temporary database, never player saves."""
import os, sys, tempfile, unittest, itertools, importlib
from pathlib import Path
TMP=tempfile.TemporaryDirectory()
os.environ['DB_PATH']=str(Path(TMP.name)/'test.db')
os.environ['ALLOW_DEV_AUTH']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from fastapi.testclient import TestClient
app.sync_passive_income=lambda uid: None
app.update_stock_market=lambda: None
app.process_market_news=lambda: None
client=TestClient(app.api,headers={'X-User-Id':'999001'})

class AuditTests(unittest.TestCase):
 def setUp(self):
  app._rate_buckets.clear()
  app.ensure_player(999001)
  with app.closing(app.db()) as conn:
   for table in ['stock_holdings','bond_holdings','businesses','real_estate_holdings']:
    conn.execute(f'DELETE FROM {table} WHERE user_id=999001')
   conn.execute('UPDATE players SET money=20000 WHERE user_id=999001')
   conn.commit()
 def holdings(self):
  with app.closing(app.db()) as c:
   return tuple([tuple(tuple(r) for r in c.execute(q)) for q in [
    'SELECT money FROM players WHERE user_id=999001',
    'SELECT * FROM stock_holdings WHERE user_id=999001',
    'SELECT * FROM bond_holdings WHERE user_id=999001']])
 def test_invalid_quantities_four_routes(self):
  for kind,ident in [('stocks','tesla'),('bonds','ofz_ru')]:
   for side in ['buy','sell']:
    for qty in [1.5,'1.5','1abc','1',True,False,0,-1,'',None,9007199254740992]:
     with self.subTest(kind=kind,side=side,qty=qty):
      before=self.holdings()
      r=client.post(f'/api/{kind}/{ident}/{side}',json={'quantity':qty})
      self.assertEqual(r.status_code,422,r.text)
      self.assertEqual(before,self.holdings())
 def test_buy_sell_and_excess(self):
  for kind,ident in [('stocks','tesla'),('bonds','ofz_ru')]:
   path=f'/api/{kind}/{ident}'
   r=client.post(path+'/buy',json={'quantity':1});self.assertEqual(r.status_code,200,r.text)
   before=self.holdings()
   self.assertEqual(client.post(path+'/sell',json={'quantity':2}).status_code,400)
   self.assertEqual(before,self.holdings())
   self.assertEqual(client.post(path+'/sell',json={'quantity':1}).status_code,200)
   before=self.holdings()
   self.assertEqual(client.post(path+'/buy',json={'quantity':9007199254740991}).status_code,400)
   self.assertEqual(before,self.holdings())
 def test_stale_price_does_not_trade(self):
  for kind,ident in [('stocks','tesla'),('bonds','ofz_ru')]:
   before=self.holdings()
   r=client.post(f'/api/{kind}/{ident}/buy',json={'quantity':1,'expected_price':0.01})
   self.assertEqual(r.status_code,409,r.text);self.assertEqual(before,self.holdings())
 def test_upgrade_preview_every_order(self):
  # 24 orders verify every additive combination, including installed upgrades.
  for order in itertools.permutations(app.BUSINESS_UPGRADES):
   self.setUp()
   r=client.post('/api/business/coffee/buy');self.assertEqual(r.status_code,200,r.text)
   for key in order:
    b=next(x for x in r.json()['businesses'] if x['id']=='coffee')
    u=next(x for x in b['upgrades'] if x['id']==key)
    r=client.post('/api/business/coffee/upgrade/'+key)
    self.assertEqual(r.status_code,200,r.text)
    after=next(x for x in r.json()['businesses'] if x['id']=='coffee')
    self.assertAlmostEqual(after['current_income'],u['income_after_upgrade'])
    self.assertAlmostEqual(after['current_income']-b['current_income'],u['income_delta'])
 def test_report_coffee_example_and_capital(self):
  client.post('/api/business/coffee/buy')
  r=client.post('/api/business/coffee/upgrade/staff').json()
  b=next(x for x in r['businesses'] if x['id']=='coffee')
  u=next(x for x in b['upgrades'] if x['id']=='automation')
  self.assertEqual((b['current_income'],u['income_delta'],u['income_after_upgrade']),(420,105,525))
  self.assertEqual(r['capital'],sum(r['capital_breakdown'][k] for k in ['cash','businesses','stocks','bonds','real_estate']))
 def test_property_balance_boundaries(self):
  ident=next(iter(app.REAL_ESTATE));price=app.REAL_ESTATE[ident]['price']
  for money in [price-1,price,price+1]:
   self.setUp()
   with app.closing(app.db()) as c:
    c.execute('UPDATE players SET money=? WHERE user_id=999001',(money,));c.commit()
   r=client.post(f'/api/real-estate/{ident}/buy')
   self.assertEqual(r.status_code,400 if money<price else 200,r.text)
   self.assertAlmostEqual(app.get_player(999001)['money'],money if money<price else money-price)
 def test_restart_initialization_preserves_holdings(self):
  client.post('/api/bonds/ofz_ru/buy',json={'quantity':1})
  before=self.holdings();app.init_db();self.assertEqual(before,self.holdings())
 def test_unsigned_requests_rejected(self):
  os.environ['ALLOW_DEV_AUTH']='0'
  try:
   self.assertIn(client.get('/api/state').status_code,(400,401))
   self.assertIn(client.get('/api/admin/overview').status_code,(400,401))
  finally:os.environ['ALLOW_DEV_AUTH']='1'

if __name__=='__main__':unittest.main(verbosity=2)
