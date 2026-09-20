import importlib
import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient


class FleetUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update({"DB_PATH": os.path.join(self.tmp.name, "game.db"), "ALLOW_DEV_AUTH": "1", "APP_ENV": "test", "BOT_TOKEN": "test", "ADMIN_IDS": "1", "OWNER_ID": "1"})
        import app
        self.app = importlib.reload(app)
        self.app.init_db()
        self.client = TestClient(self.app.api)
        self.headers = {"X-User-Id": "25001"}
        self.client.get("/api/state", headers=self.headers)
        with sqlite3.connect(self.app.DB_PATH) as conn:
            conn.execute("UPDATE players SET money=20000000 WHERE user_id=25001")

    def tearDown(self):
        self.tmp.cleanup()

    def test_taxi_fleet_capacity_income_and_capital(self):
        state = self.client.post("/api/business/taxi/buy", headers=self.headers).json()
        taxi = next(b for b in state["businesses"] if b["id"] == "taxi")
        self.assertEqual(taxi["transport"]["capacity"], 5)
        self.assertEqual(taxi["current_income"], 0)
        state = self.client.post("/api/fleet/taxi/vehicle/city/buy", headers=self.headers, json={"quantity": 5}).json()["state"]
        taxi = next(b for b in state["businesses"] if b["id"] == "taxi")
        self.assertEqual(taxi["transport"]["occupied"], 5)
        self.assertEqual(taxi["current_income"], 1200)
        self.assertEqual(taxi["capitalization"], 35000 + 5 * 12000)
        blocked = self.client.post("/api/fleet/taxi/vehicle/city/buy", headers=self.headers, json={"quantity": 1})
        self.assertEqual(blocked.status_code, 400)

    def test_garage_upgrade_is_timed_and_capitalized(self):
        self.client.post("/api/business/logistics/buy", headers=self.headers)
        result = self.client.post("/api/fleet/logistics/garage/upgrade", headers=self.headers).json()
        logistics = next(b for b in result["state"]["businesses"] if b["id"] == "logistics")
        self.assertTrue(logistics["transport"]["upgrading"])
        self.assertEqual(logistics["transport"]["capacity"], 5)
        self.assertEqual(logistics["transport"]["next_capacity"], 10)
        self.assertEqual(logistics["capitalization"], 90000 + 75000)

    def test_retired_us_bond_is_refunded_once(self):
        with sqlite3.connect(self.app.DB_PATH) as conn:
            before = conn.execute("SELECT money FROM players WHERE user_id=25001").fetchone()[0]
            conn.execute("INSERT INTO bond_holdings(user_id,bond_id,quantity) VALUES(25001,'ofz_us',3)")
        self.app.init_db()
        self.app.init_db()
        with sqlite3.connect(self.app.DB_PATH) as conn:
            after = conn.execute("SELECT money FROM players WHERE user_id=25001").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM bond_holdings WHERE bond_id='ofz_us'").fetchone()[0]
        self.assertEqual(after - before, 6000)
        self.assertEqual(count, 0)

    def test_news_impact_is_eleven_to_thirty_five_percent(self):
        self.assertEqual(self.app.MARKET_NEWS_MIN_IMPACT, .11)
        self.assertEqual(self.app.MARKET_NEWS_MAX_IMPACT, .35)
        self.assertNotIn("ofz_us", self.app.BONDS)
        self.assertNotIn("delivery", self.app.BUSINESSES)

    def test_admin_grant_tracks_selected_income_category(self):
        admin_headers = {"X-User-Id": "1"}
        self.client.get("/api/state", headers=admin_headers)
        before = self.client.get("/api/statistics", headers=self.headers).json()["total_earned"]
        r = self.client.post("/api/admin/player/25001/grant", headers=admin_headers, json={"amount": 12345, "category": "prize", "note": "QA", "count_as_income": True})
        self.assertEqual(r.status_code, 200, r.text)
        stats = self.client.get("/api/statistics", headers=self.headers).json()
        self.assertAlmostEqual(stats["total_earned"] - before, 12345, places=2)
        prize = next(x for x in stats["income_breakdown"] if x["category"] == "prize")
        self.assertEqual(prize["amount"], 12345)

    def test_admin_balance_only_grant_does_not_inflate_profit(self):
        admin_headers = {"X-User-Id": "1"}
        self.client.get("/api/state", headers=admin_headers)
        before = self.client.get("/api/statistics", headers=self.headers).json()["total_earned"]
        r = self.client.post("/api/admin/player/25001/grant", headers=admin_headers, json={"amount": 5000, "category": "balance", "count_as_income": False})
        self.assertEqual(r.status_code, 200, r.text)
        after = self.client.get("/api/statistics", headers=self.headers).json()["total_earned"]
        self.assertEqual(after, before)


    def test_state_exposes_server_clock_for_precise_live_timers(self):
        state = self.client.get("/api/state", headers=self.headers).json()
        self.assertIsInstance(state.get("server_time"), int)
        self.assertIsInstance(state.get("server_time_ms"), int)
        self.assertLessEqual(abs(state["server_time"] - int(__import__("time").time())), 2)
        self.assertLessEqual(abs(state["server_time_ms"] - int(__import__("time").time()*1000)), 2000)

    def test_private_balance_correction_is_owner_only_and_hidden_from_other_admins(self):
        owner_headers = {"X-User-Id": "1"}
        other_headers = {"X-User-Id": "2"}
        self.client.get("/api/state", headers=owner_headers)
        self.client.get("/api/state", headers=other_headers)
        old_admins = self.app.ADMIN_IDS
        old_owner = self.app.OWNER_ID
        self.app.ADMIN_IDS = {1, 2}
        self.app.OWNER_ID = 1
        try:
            owner_overview = self.client.get("/api/admin/overview", headers=owner_headers).json()
            self.assertTrue(owner_overview.get("private_capabilities", {}).get("grant_money"))
            other_overview = self.client.get("/api/admin/overview", headers=other_headers).json()
            self.assertNotIn("private_capabilities", other_overview)
            denied = self.client.post("/api/admin/player/25001/grant", headers=other_headers, json={"amount": 1, "category": "balance", "count_as_income": False})
            self.assertEqual(denied.status_code, 404)
            allowed = self.client.post("/api/admin/player/25001/grant", headers=owner_headers, json={"amount": 1, "category": "balance", "count_as_income": False})
            self.assertEqual(allowed.status_code, 200, allowed.text)
            hidden_logs = self.client.get("/api/admin/overview", headers=other_headers).json().get("logs", [])
            self.assertFalse(any(x.get("action") == "grant_money" for x in hidden_logs))
        finally:
            self.app.ADMIN_IDS = old_admins
            self.app.OWNER_ID = old_owner

    def test_news_photos_are_local_fast_assets_with_source_reference(self):
        for stock_id, template in self.app.MARKET_NEWS_TEMPLATES.items():
            self.assertTrue(template["photo"].startswith(f"/static/news/{stock_id}.webp"), stock_id)
            self.assertTrue(template.get("source_photo", "").startswith("https://"), stock_id)

    def test_google_uses_canonical_game_name(self):
        self.assertEqual(self.app.STOCKS["google"]["name"], "Google")

    def test_news_static_assets_are_cacheable(self):
        r = self.client.get("/static/news/google.webp?v=263")
        self.assertEqual(r.status_code, 200)
        self.assertIn("max-age=604800", r.headers.get("cache-control", ""))

    def test_news_ui_has_no_fictional_banner_and_uses_contain(self):
        js = open(os.path.join(os.path.dirname(self.app.__file__), "web", "premium_v25.js"), encoding="utf-8").read()
        css = open(os.path.join(os.path.dirname(self.app.__file__), "web", "premium_v25.css"), encoding="utf-8").read()
        self.assertNotIn("Вымышленные события появляются", js)
        self.assertIn("object-fit:contain!important", css)

    def test_published_news_impact_is_inside_requested_range(self):
        with sqlite3.connect(self.app.DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("UPDATE stocks SET current_price=(min_price+max_price)/2")
            self.app._publish_market_news_conn(conn, 1700000000)
            row = conn.execute("SELECT sentiment,impact_percent FROM market_news ORDER BY id DESC LIMIT 1").fetchone()
        impact = float(row["impact_percent"])
        self.assertGreaterEqual(abs(impact), .11)
        self.assertLessEqual(abs(impact), .35)
        self.assertGreater(impact, 0) if row["sentiment"] == "good" else self.assertLess(impact, 0)


if __name__ == "__main__":
    unittest.main()
