import importlib
import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient


class FleetUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update({"DB_PATH": os.path.join(self.tmp.name, "game.db"), "ALLOW_DEV_AUTH": "1", "APP_ENV": "test", "BOT_TOKEN": "test", "ADMIN_IDS": "1"})
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

    def test_news_impact_is_ten_percent(self):
        self.assertEqual(self.app.MARKET_NEWS_MIN_IMPACT, .10)
        self.assertEqual(self.app.MARKET_NEWS_MAX_IMPACT, .10)
        self.assertNotIn("ofz_us", self.app.BONDS)
        self.assertNotIn("delivery", self.app.BUSINESSES)


if __name__ == "__main__":
    unittest.main()
