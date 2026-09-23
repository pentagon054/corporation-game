from pathlib import Path
import ast
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / 'apply_subscription_gate_v32.py'

SAMPLE = '''\
import os\n\nfrom fastapi import FastAPI, Header, HTTPException\nBOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")\napi = FastAPI(title="Corporation")\n\ndef user_from_request(x_telegram_init_data, x_user_id):\n    if x_telegram_init_data:\n        return 123, "tester", "Tester"\n    raise HTTPException(401, "Authentication required")\n\n@api.get("/api/state")\ndef state(x_telegram_init_data: str | None = Header(None), x_user_id: str | None = Header(None)):\n    uid, username, first_name = user_from_request(x_telegram_init_data, x_user_id)\n    return {"user_id": uid}\n'''

with tempfile.TemporaryDirectory() as td:
    project = Path(td)
    app = project / 'app.py'
    app.write_text(SAMPLE, encoding='utf-8')
    subprocess.run([sys.executable, str(PATCHER), '--project', str(project)], check=True)
    patched = app.read_text(encoding='utf-8')
    assert patched.count('CORPORATION_REQUIRED_CHANNEL_V32_BEGIN') == 1
    assert '/api/subscription/check' in patched
    assert '_v32_base_user_from_request = user_from_request' in patched
    ast.parse(patched)

    # Re-applying must stay idempotent.
    subprocess.run([sys.executable, str(PATCHER), '--project', str(project)], check=True)
    patched2 = app.read_text(encoding='utf-8')
    assert patched2.count('CORPORATION_REQUIRED_CHANNEL_V32_BEGIN') == 1
    ast.parse(patched2)

print('v32 patch tests passed')
