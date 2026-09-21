"""Real API/SQLite regressions for multiple independent business instances."""
import importlib
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        os.environ.update(DB_PATH=str(Path(self.tmp.name)/'game.db'),APP_ENV='test',ALLOW_DEV_AUTH='1',BOT_TOKEN='test',ADMIN_IDS='1',OWNER_ID='1')
        import app
        self.app=importlib.reload(app)
        self.client=TestClient(self.app.api,headers={'X-User-Id':'28001'})
        self.app.ensure_player(28001)
        with self.app.closing(self.app.db()) as c:
            c.execute('UPDATE players SET money=100000000,last_income_sync=? WHERE user_id=28001',(int(time.time()),));c.commit()
        self.app.update_stock_market=lambda:None
        self.real_sync=self.app.sync_passive_income
        self.app.sync_passive_income=lambda uid:None
    def tearDown(self):self.tmp.cleanup()
    def post(self,url,**kw):
        r=self.client.post(url,**kw);self.assertEqual(r.status_code,200,r.text);return r.json()
    def owned(self,s,kind):return [b for b in s['businesses'] if b['owned'] and b['type_id']==kind]
    def test_five_coffees_upgrade_and_sale_are_independent(self):
        for _ in range(5):s=self.post('/api/business/coffee/buy')
        items=self.owned(s,'coffee');self.assertEqual(len(items),5)
        self.assertEqual(len({b['id'] for b in items}),5)
        target=items[2]['id'];key=next(iter(self.app.BUSINESS_UPGRADES))
        s=self.post(f'/api/business/{target}/upgrade/{key}')
        items=self.owned(s,'coffee')
        self.assertEqual(sum(u['owned'] for b in items for u in b['upgrades']),1)
        self.assertEqual(s['income_breakdown']['business'],round(sum(b['current_income'] for b in items),2))
        self.assertEqual(s['capital_breakdown']['businesses'],sum(b['capitalization'] for b in items))
        self.assertEqual(s['stats']['companies_bought'],5)
        profile=self.client.get('/api/player/28001').json();self.assertEqual(len(profile['businesses']),5)
        r=self.post(f'/api/business/{target}/sell');self.assertEqual(len(self.owned(r['state'],'coffee')),4)
        self.assertNotIn(target,[b['id'] for b in r['state']['businesses'] if b['owned']])
        self.assertEqual(self.client.post(f'/api/business/{target}/sell').status_code,400)
    def test_three_taxis_and_logistics_have_separate_fleets_and_timers(self):
        for kind in ['taxi','logistics']:
            for _ in range(3):s=self.post(f'/api/business/{kind}/buy')
            ids=[b['id'] for b in self.owned(s,kind)]
            vehicle=next(iter(self.app.TRANSPORT_VEHICLES[kind]))
            for qty,bid in enumerate(ids,1):self.post(f'/api/fleet/{bid}/vehicle/{vehicle}/buy',json={'quantity':qty})
            s=self.post(f'/api/fleet/{ids[1]}/garage/upgrade')['state']
            items={b['id']:b for b in self.owned(s,kind)}
            self.assertEqual([items[i]['transport']['occupied'] for i in ids],[1,2,3])
            self.assertEqual([items[i]['transport']['upgrading'] for i in ids],[False,True,False])
            with self.app.closing(self.app.db()) as c:
                c.execute('UPDATE transport_fleets SET upgrade_finishes_at=? WHERE user_id=28001 AND business_id=?',(int(time.time())-1,ids[1]));c.commit()
            s=self.client.get('/api/state').json();items={b['id']:b for b in self.owned(s,kind)}
            self.assertEqual([items[i]['transport']['capacity'] for i in ids],[5,10,5])
            self.post(f'/api/fleet/{ids[2]}/vehicle/{vehicle}/sell',json={'quantity':1})
            s=self.post(f'/api/business/{ids[1]}/sell')['state']
            self.assertEqual([b['transport']['occupied'] for b in self.owned(s,kind)],[1,2])
        items=[b for b in s['businesses'] if b['owned']]
        self.assertEqual(s['capital_breakdown']['businesses'],sum(b['capitalization'] for b in items))
        self.assertEqual(s['income_breakdown']['business'],sum(b['current_income'] for b in items))
        with self.app.closing(self.app.db()) as c:c.execute('UPDATE players SET last_income_sync=?',(int(time.time()),));c.commit()
        ranked=next(r for r in self.app.all_ranked_players() if r['user_id']==28001)
        self.assertAlmostEqual(ranked['capital'],self.app.player_capital(28001)['total'],delta=1)
    def test_legacy_rows_and_new_instances_survive_reinitialization(self):
        self.post('/api/business/coffee/buy');self.post('/api/business/taxi/buy')
        self.post('/api/fleet/taxi/vehicle/city/buy',json={'quantity':3})
        self.post('/api/fleet/taxi/garage/upgrade')
        with self.app.closing(self.app.db()) as c:
            c.execute("UPDATE businesses SET level=4,marketing=1,equipment=1 WHERE business_id='coffee'");c.commit()
        self.post('/api/business/coffee/buy');self.post('/api/business/taxi/buy')
        def data():
            with self.app.closing(self.app.db()) as c:
                return [list(map(tuple,c.execute(f'SELECT * FROM {t} ORDER BY user_id,business_id'))) for t in ['businesses','transport_fleets','transport_vehicles']]
        before=data();self.app.init_db();self.app.init_db();self.assertEqual(before,data())
        s=self.client.get('/api/state').json();self.assertEqual(self.owned(s,'coffee')[0]['level'],4)
        self.assertEqual(self.owned(s,'taxi')[0]['transport']['occupied'],3)
    def test_instance_ownership_is_enforced(self):
        self.post('/api/business/taxi/buy');s=self.post('/api/business/taxi/buy');bid=self.owned(s,'taxi')[-1]['id']
        self.app.ensure_player(28002)
        for path,body in [(f'/api/business/{bid}/sell',None),(f'/api/fleet/{bid}/garage/upgrade',None),(f'/api/fleet/{bid}/vehicle/city/buy',{'quantity':1})]:
            r=self.client.post(path,headers={'X-User-Id':'28002'},json=body);self.assertEqual(r.status_code,400,r.text)
        self.assertEqual(len(self.owned(self.client.get('/api/state').json(),'taxi')),2)
    def test_passive_accrual_includes_every_instance(self):
        self.post('/api/business/coffee/buy');self.post('/api/business/coffee/buy')
        self.post('/api/business/taxi/buy');s=self.post('/api/business/taxi/buy')
        for b in self.owned(s,'taxi'):
            self.post(f"/api/fleet/{b['id']}/vehicle/city/buy",json={'quantity':2})
        rate=self.app.business_hourly_income(28001)
        with self.app.closing(self.app.db()) as c:
            c.execute('UPDATE players SET last_income_sync=? WHERE user_id=28001',(int(time.time())-3600,))
            before=c.execute('SELECT money FROM players WHERE user_id=28001').fetchone()[0];c.commit()
        result=self.real_sync(28001)
        self.assertAlmostEqual(result['business'],rate,delta=rate/1800)
        self.assertAlmostEqual(self.app.get_player(28001)['money']-before,rate,delta=rate/1800)
    def test_concurrent_purchases_create_distinct_rows(self):
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(lambda _:self.client.post('/api/business/coffee/buy'),range(3)))
        self.assertTrue(all(r.status_code==200 for r in results),[r.text for r in results])
        s=self.client.get('/api/state').json();self.assertEqual(len(self.owned(s,'coffee')),3)
        self.assertEqual(s['player']['money'],100000000-3*self.app.BUSINESSES['coffee']['base_cost'])

if __name__=='__main__':unittest.main()
