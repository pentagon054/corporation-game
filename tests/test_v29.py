"""Corporation v29 regressions: business slot limits and expansion cooldown."""
import importlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class V29Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update(
            DB_PATH=str(Path(self.tmp.name) / 'game.db'),
            APP_ENV='test', ALLOW_DEV_AUTH='1', BOT_TOKEN='test', ADMIN_IDS='1', OWNER_ID='1'
        )
        import app
        self.app = importlib.reload(app)
        self.client = TestClient(self.app.api, headers={'X-User-Id': '29001'})
        self.app.ensure_player(29001)
        self.app.update_stock_market = lambda: None
        self.app.sync_passive_income = lambda uid: None
        with self.app.closing(self.app.db()) as c:
            c.execute('UPDATE players SET money=100000000,last_income_sync=? WHERE user_id=29001', (int(time.time()),))
            c.commit()

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_limit_is_ten_then_one_slot_can_be_bought(self):
        for _ in range(10):
            r = self.client.post('/api/business/coffee/buy')
            self.assertEqual(r.status_code, 200, r.text)
        state = self.client.get('/api/state').json()
        self.assertEqual(state['business_slots']['slots'], 10)
        self.assertEqual(state['business_slots']['used'], 10)
        self.assertEqual(state['business_slots']['available'], 0)
        self.assertEqual(state['business_slots']['next_cost'], 100000.0)

        blocked = self.client.post('/api/business/coffee/buy')
        self.assertEqual(blocked.status_code, 400)
        self.assertIn('10', blocked.text)

        expanded = self.client.post('/api/business-slots/expand')
        self.assertEqual(expanded.status_code, 200, expanded.text)
        body = expanded.json()
        self.assertEqual(body['slots'], 11)
        self.assertEqual(body['cost'], 100000.0)
        self.assertGreater(body['state']['business_slots']['seconds_left'], 0)
        self.assertEqual(body['state']['business_slots']['next_cost'], 150000.0)

        eleventh = self.client.post('/api/business/coffee/buy')
        self.assertEqual(eleventh.status_code, 200, eleventh.text)
        self.assertEqual(eleventh.json()['business_slots']['used'], 11)

    def test_expansion_has_one_hour_cooldown(self):
        first = self.client.post('/api/business-slots/expand')
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.post('/api/business-slots/expand')
        self.assertEqual(second.status_code, 429, second.text)
        with self.app.closing(self.app.db()) as c:
            c.execute('UPDATE business_slot_limits SET last_expanded_at=? WHERE user_id=?', (int(time.time()) - 3601, 29001))
            c.commit()
        third = self.client.post('/api/business-slots/expand')
        self.assertEqual(third.status_code, 200, third.text)
        self.assertEqual(third.json()['slots'], 12)
        self.assertEqual(third.json()['cost'], 150000.0)

    def test_concurrent_purchases_never_exceed_slot_limit(self):
        with ThreadPoolExecutor(max_workers=14) as pool:
            results = list(pool.map(lambda _: self.client.post('/api/business/coffee/buy'), range(14)))
        success = [r for r in results if r.status_code == 200]
        self.assertEqual(len(success), 10, [(r.status_code, r.text) for r in results])
        state = self.client.get('/api/state').json()
        self.assertEqual(state['business_slots']['used'], 10)
        self.assertEqual(len([b for b in state['businesses'] if b['owned']]), 10)

    def test_existing_portfolio_above_ten_is_grandfathered_on_init(self):
        with self.app.closing(self.app.db()) as c:
            for i in range(12):
                c.execute(
                    'INSERT INTO businesses(user_id,business_id,level) VALUES(?,?,1)',
                    (29001, f'coffee~legacy{i}')
                )
            c.commit()
        self.app.init_db()
        state = self.client.get('/api/state').json()
        self.assertEqual(state['business_slots']['slots'], 12)
        self.assertEqual(state['business_slots']['used'], 12)
        self.assertEqual(state['business_slots']['available'], 0)

    def test_frontend_v29_is_wired_and_uses_sliders(self):
        root = Path(self.app.__file__).resolve().parent
        index = (root / 'web' / 'index.html').read_text(encoding='utf-8')
        js = (root / 'web' / 'v29.js').read_text(encoding='utf-8')
        css = (root / 'web' / 'v29.css').read_text(encoding='utf-8')
        self.assertIn('nav-label">Главная</span>', index)
        self.assertIn('/static/v29.js?v=290', index)
        self.assertIn('/static/v29.css?v=290', index)
        self.assertIn("window.openBondTrade", js)
        self.assertIn("price,side:'buy'", js)
        self.assertIn("window.buyFleetVehicle25", js)
        self.assertIn('business-slots29', js)
        self.assertIn('.rating-page>.grid{padding-right:0!important', css)

    def test_reset_restores_ten_slots(self):
        r = self.client.post('/api/business-slots/expand')
        self.assertEqual(r.status_code, 200, r.text)
        with self.app.closing(self.app.db()) as c:
            self.app.reset_all_progress_conn(c, int(time.time()))
            c.commit()
        state = self.client.get('/api/state').json()
        self.assertEqual(state['business_slots']['slots'], 10)
        self.assertEqual(state['business_slots']['used'], 0)
        self.assertEqual(state['business_slots']['seconds_left'], 0)

if __name__ == '__main__':
    unittest.main()
