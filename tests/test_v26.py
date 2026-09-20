import importlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class V26RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update({
            "DB_PATH": os.path.join(self.tmp.name, "game.db"),
            "ALLOW_DEV_AUTH": "1",
            "APP_ENV": "test",
            "BOT_TOKEN": "test",
            "ADMIN_IDS": "1",
            "OWNER_ID": "1",
        })
        import app
        self.app = importlib.reload(app)
        self.app.init_db()
        self.client = TestClient(self.app.api)
        self.player_headers = {"X-User-Id": "26001"}
        self.admin_headers = {"X-User-Id": "1"}
        self.client.get("/api/state", headers=self.player_headers)

    def tearDown(self):
        self.tmp.cleanup()

    def test_admin_credit_is_attributed_to_selected_income_source(self):
        before = self.client.get("/api/state", headers=self.player_headers).json()["player"]["money"]
        r = self.client.post(
            "/api/admin/private-operation/26001",
            headers=self.admin_headers,
            json={"amount": 123456.78, "source": "business", "note": "QA"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertEqual(data["source"], "business")
        self.assertAlmostEqual(data["state"]["player"]["money"] - before, 123456.78, places=2)
        stats = self.client.get("/api/statistics", headers=self.player_headers).json()
        sources = {x["source"]: x["amount"] for x in stats["income_sources"]}
        self.assertAlmostEqual(sources["business"], 123456.78, places=2)
        self.assertGreaterEqual(stats["total_earned"], 123456.78)
        with sqlite3.connect(self.app.DB_PATH) as conn:
            row = conn.execute("SELECT amount FROM income_stats WHERE user_id=? AND source='business'", (26001,)).fetchone()
        self.assertAlmostEqual(row[0], 123456.78, places=2)

    def test_admin_credit_rejects_unknown_category(self):
        r = self.client.post(
            "/api/admin/private-operation/26001",
            headers=self.admin_headers,
            json={"amount": 1000, "source": "magic"},
        )
        self.assertEqual(r.status_code, 400)

    def test_state_has_server_clock_for_second_accurate_timers(self):
        state = self.client.get("/api/state", headers=self.player_headers).json()
        self.assertIsInstance(state["server_time"], int)

    def test_four_single_vehicle_purchases_keep_working_until_garage_capacity(self):
        # Regression for the UI report: repeated single-vehicle buys must not die after the 3rd click.
        credit = self.client.post(
            "/api/admin/private-operation/26001",
            headers=self.admin_headers,
            json={"amount": 500000, "source": "bonus", "note": "fleet regression"},
        )
        self.assertEqual(credit.status_code, 200, credit.text)
        business = self.client.post("/api/business/logistics/buy", headers=self.player_headers)
        self.assertEqual(business.status_code, 200, business.text)
        for n in range(1, 5):
            r = self.client.post(
                "/api/fleet/logistics/vehicle/van/buy",
                headers=self.player_headers,
                json={"quantity": 1},
            )
            self.assertEqual(r.status_code, 200, f"single buy #{n}: {r.text}")
            fleet = r.json()["state"]["businesses"]
            logistics = next(x for x in fleet if x["id"] == "logistics")
            self.assertEqual(logistics["transport"]["occupied"], n)

    def test_frontend_regressions_are_wired(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        js = (root / "web" / "premium_v26.js").read_text(encoding="utf-8")
        css = (root / "web" / "premium_v26.css").read_text(encoding="utf-8")
        atlas = (root / "web" / "interactive_map.js").read_text(encoding="utf-8")
        self.assertIn("premium_v26.js?v=270", html)
        self.assertIn("action-modal26", js)
        self.assertNotIn("prompt(`Сколько машин купить", js)
        self.assertIn("data-tax-until", js)
        self.assertIn("data-impact-at", js)
        self.assertIn("cdn.simpleicons.org", js)
        self.assertIn("top:50%", css)
        self.assertIn("this.land.style.width=mapW+'px'", atlas)
        self.assertIn("Math.min(12", atlas)

    def test_news_uses_official_company_domains(self):
        expected = {
            "bmw": "bmwgroup.com", "kfc": "sanity.io", "spotify": "googleapis.com",
            "nvidia": "nvidia.com", "tesla": "tesla.com", "mcdonalds": "mcdonalds.com",
            "toyota": "toyota", "apple": "apple.com", "google": "gstatic.com", "intel": "intel.com",
        }
        for sid, domain in expected.items():
            self.assertIn(domain, self.app.MARKET_NEWS_TEMPLATES[sid]["photo"])


if __name__ == "__main__":
    unittest.main()
