import importlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class V27OwnerAndRatingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.update({
            "DB_PATH": os.path.join(self.tmp.name, "game.db"),
            "ALLOW_DEV_AUTH": "1",
            "APP_ENV": "test",
            "BOT_TOKEN": "test",
            "ADMIN_IDS": "1,2",
            "OWNER_ID": "1",
        })
        import app
        self.app = importlib.reload(app)
        self.app.init_db()
        self.client = TestClient(self.app.api)
        self.owner = {"X-User-Id": "1"}
        self.admin = {"X-User-Id": "2"}
        self.player = {"X-User-Id": "27001"}
        self.client.get("/api/state", headers=self.player)

    def tearDown(self):
        self.tmp.cleanup()

    def test_private_extension_is_only_disclosed_to_owner(self):
        owner_overview = self.client.get("/api/admin/overview", headers=self.owner)
        self.assertEqual(owner_overview.status_code, 200)
        self.assertIn("extension", owner_overview.json())

        admin_overview = self.client.get("/api/admin/overview", headers=self.admin)
        self.assertEqual(admin_overview.status_code, 200)
        self.assertNotIn("extension", admin_overview.json())

        owner_ext = self.client.get("/api/admin/extension", headers=self.owner)
        self.assertEqual(owner_ext.status_code, 200)
        self.assertIn("application/javascript", owner_ext.headers.get("content-type", ""))
        self.assertIn("Начислить деньги", owner_ext.text)

        hidden = self.client.get("/api/admin/extension", headers=self.admin)
        self.assertEqual(hidden.status_code, 404)

    def test_private_money_operation_changes_balance_and_is_not_in_shared_admin_log(self):
        before = self.client.get("/api/state", headers=self.player).json()["player"]["money"]
        r = self.client.post(
            "/api/admin/private-operation/27001",
            headers=self.owner,
            json={"amount": 98765.43, "source": "trading", "note": "v27 verification"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertAlmostEqual(data["balance_before"], before, places=2)
        self.assertAlmostEqual(data["balance_after"] - data["balance_before"], 98765.43, places=2)
        current = self.client.get("/api/state", headers=self.player).json()["player"]["money"]
        self.assertAlmostEqual(current - before, 98765.43, places=2)

        with sqlite3.connect(self.app.DB_PATH) as conn:
            public_log = conn.execute("SELECT COUNT(*) FROM admin_logs WHERE action LIKE '%balance%' OR action LIKE '%credit%'").fetchone()[0]
            private_log = conn.execute("SELECT COUNT(*) FROM owner_logs WHERE action='private_balance_adjustment'").fetchone()[0]
        self.assertEqual(public_log, 0)
        self.assertEqual(private_log, 1)

    def test_other_admin_cannot_use_private_money_operation(self):
        before = self.client.get("/api/state", headers=self.player).json()["player"]["money"]
        r = self.client.post(
            "/api/admin/private-operation/27001",
            headers=self.admin,
            json={"amount": 100000, "source": "bonus"},
        )
        self.assertEqual(r.status_code, 404)
        after = self.client.get("/api/state", headers=self.player).json()["player"]["money"]
        self.assertAlmostEqual(after, before, places=2)

    def test_public_admin_assets_do_not_disclose_private_money_tool(self):
        root = Path(__file__).resolve().parents[1]
        public_js = (root / "web" / "v22_admin.js").read_text(encoding="utf-8")
        public_html = (root / "web" / "admin.html").read_text(encoding="utf-8")
        for needle in ("Начислить деньги", "private-operation", "/credit", "+ Деньги"):
            self.assertNotIn(needle, public_js)
            self.assertNotIn(needle, public_html)

    def test_rating_controls_are_portaled_to_document_body(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        js = (root / "web" / "premium_v27.js").read_text(encoding="utf-8")
        css = (root / "web" / "premium_v27.css").read_text(encoding="utf-8")
        self.assertIn("premium_v27.js?v=270", html)
        self.assertIn("premium_v27.css?v=270", html)
        self.assertIn("document.body.appendChild(candidate)", js)
        self.assertIn("position:fixed!important", css)
        self.assertIn("top:50dvh!important", css)


if __name__ == "__main__":
    unittest.main()
