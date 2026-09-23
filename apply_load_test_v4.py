from pathlib import Path
from datetime import datetime
import shutil
import sys

START = "# === CORPORATION LOAD TEST V4 START ==="
END = "# === CORPORATION LOAD TEST V4 END ==="
BLOCK = '# === CORPORATION LOAD TEST V4 START ===\n# Temporary, read-only production load-test endpoint.\n# Protected by LOAD_TEST_TOKEN. Remove after testing.\n\n@api.get("/api/internal/load-test/read")\ndef corporation_load_test_read(\n    seed: int = 0,\n    x_load_test_token: str | None = Header(None),\n):\n    expected = os.getenv("LOAD_TEST_TOKEN", "")\n    if not expected or x_load_test_token != expected:\n        raise HTTPException(status_code=404, detail="Not Found")\n\n    conn = db()\n    query_count = 0\n    row_count = 0\n\n    try:\n        table_rows = conn.execute(\n            "SELECT name FROM sqlite_master WHERE type=\'table\'"\n        ).fetchall()\n        query_count += 1\n        tables = {str(r["name"]) for r in table_rows}\n\n        def columns(table):\n            nonlocal query_count\n            rows = conn.execute(f\'PRAGMA table_info("{table}")\').fetchall()\n            query_count += 1\n            return {str(r["name"]) for r in rows}\n\n        def fetch(sql, params=()):\n            nonlocal query_count, row_count\n            rows = conn.execute(sql, params).fetchall()\n            query_count += 1\n            row_count += len(rows)\n            return rows\n\n        uid = None\n\n        if "players" in tables:\n            pcols = columns("players")\n            total = fetch("SELECT COUNT(*) AS c FROM players")\n            count = int(total[0]["c"]) if total else 0\n\n            if count > 0:\n                offset = abs(int(seed)) % count\n                selected = fetch(\n                    "SELECT * FROM players ORDER BY user_id LIMIT 1 OFFSET ?",\n                    (offset,),\n                )\n                if selected and "user_id" in pcols:\n                    uid = int(selected[0]["user_id"])\n\n            if "money" in pcols:\n                fetch("SELECT * FROM players ORDER BY money DESC LIMIT 20")\n            else:\n                fetch("SELECT * FROM players LIMIT 20")\n\n        if "stocks" in tables:\n            fetch("SELECT * FROM stocks LIMIT 50")\n\n        per_user_tables = (\n            "stats",\n            "businesses",\n            "business_instances",\n            "stock_holdings",\n            "bond_holdings",\n            "real_estate_holdings",\n            "daily_profit",\n            "taxes",\n        )\n\n        for table in per_user_tables:\n            if uid is None or table not in tables:\n                continue\n            tcols = columns(table)\n            if "user_id" not in tcols:\n                continue\n\n            if table == "daily_profit" and "day" in tcols:\n                fetch(\n                    \'SELECT * FROM "daily_profit" WHERE user_id=? \'\n                    \'ORDER BY day DESC LIMIT 30\',\n                    (uid,),\n                )\n            else:\n                fetch(\n                    f\'SELECT * FROM "{table}" WHERE user_id=? LIMIT 50\',\n                    (uid,),\n                )\n\n        for table in (\n            "businesses",\n            "business_instances",\n            "stock_holdings",\n            "bond_holdings",\n            "real_estate_holdings",\n        ):\n            if table in tables:\n                fetch(f\'SELECT COUNT(*) AS c FROM "{table}"\')\n\n        return {\n            "ok": True,\n            "queries": query_count,\n            "rows": row_count,\n            "player_found": uid is not None,\n        }\n    finally:\n        conn.close()\n# === CORPORATION LOAD TEST V4 END ==='

def main():
    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    app = project / "app.py"

    if not app.exists():
        raise SystemExit(f"app.py not found: {app}")

    text = app.read_text(encoding="utf-8")

    if START in text:
        print("V4 load-test endpoint is already installed.")
        return

    anchor = '@api.get("/")'
    pos = text.find(anchor)
    if pos < 0:
        raise SystemExit('Could not find @api.get("/") in app.py; no changes made.')

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = app.with_name(f"app.py.backup_loadtest_v4_{stamp}")
    shutil.copy2(app, backup)

    new_text = text[:pos] + BLOCK.strip() + "\n\n\n" + text[pos:]
    app.write_text(new_text, encoding="utf-8")

    print("Installed temporary read-only load-test endpoint.")
    print(f"Backup: {backup.name}")
    print("Next: commit/push, then set LOAD_TEST_TOKEN in Railway.")

if __name__ == "__main__":
    main()
