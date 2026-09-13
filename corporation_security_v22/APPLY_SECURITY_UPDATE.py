from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
# ZIP can be extracted either into project root or into a subfolder.
if not (ROOT / "app.py").exists() and (ROOT.parent / "app.py").exists():
    ROOT = ROOT.parent
APP = ROOT / "app.py"
WEB = ROOT / "web"
BOT = ROOT / "bot.py"

if not APP.exists() or not WEB.exists():
    raise SystemExit("ОШИБКА: положи файлы обновления в корень Corporation рядом с app.py и папкой web.")

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP_DIR = ROOT / f"security_backup_{STAMP}"
BACKUP_DIR.mkdir(exist_ok=True)


def backup(path: Path):
    rel = path.relative_to(ROOT)
    dst = BACKUP_DIR / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dst)


def write_if_changed(path: Path, text: str):
    old = path.read_text(encoding="utf-8")
    if old == text:
        print(f"{path.relative_to(ROOT)}: без изменений")
        return False
    backup(path)
    path.write_text(text, encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: обновлён")
    return True


def replace_once(text: str, pattern: str, replacement: str, label: str, flags=0):
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Не удалось безопасно найти блок: {label}. Файл не изменён.")
    return new

SECURITY_CONFIG = r'''# === CORPORATION SECURITY V22 ================================================
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip()
ADMIN_IDS = {int(x.strip()) for x in (os.getenv("ADMIN_IDS") or "").split(",") if x.strip().isdigit()}
STARTING_MONEY = 10000.0

# Telegram Mini App initData is short-lived. A stolen signed payload must not work forever.
TELEGRAM_AUTH_MAX_AGE = max(60, min(int(os.getenv("TELEGRAM_AUTH_MAX_AGE", "3600")), 86400))
MAX_INIT_DATA_BYTES = 8192
MAX_API_BODY_BYTES = max(4096, min(int(os.getenv("MAX_API_BODY_BYTES", "65536")), 1048576))

# Developer auth is deliberately impossible on Railway even if ALLOW_DEV_AUTH=1 was
# accidentally left in environment variables.
def _dev_auth_enabled():
    return os.getenv("ALLOW_DEV_AUTH") == "1" and not _is_railway_runtime()

# ============================================================================'''

AUTH_BLOCK = r'''def verify_init_data(init_data: str):
    """Validate Telegram Mini App initData exactly as required by Telegram.

    Security properties:
    - HMAC-SHA256 signature bound to BOT_TOKEN;
    - mandatory user + auth_date;
    - freshness window to limit replay of stolen initData;
    - bounded input size;
    - fail-closed in production.
    """
    if not init_data:
        if _dev_auth_enabled():
            return None
        raise HTTPException(401, "Open this game from Telegram.")

    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise HTTPException(503, "Server authentication is not configured")
    if len(init_data.encode("utf-8", errors="ignore")) > MAX_INIT_DATA_BYTES:
        raise HTTPException(400, "Telegram authentication payload is too large")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise HTTPException(401, "Invalid Telegram authentication payload")

    # Duplicate fields are ambiguous and are rejected rather than interpreted.
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise HTTPException(401, "Invalid Telegram authentication payload")

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash or not re.fullmatch(r"[0-9a-fA-F]{64}", received_hash):
        raise HTTPException(401, "Missing or invalid Telegram hash")

    data_check = "\\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    calculated = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated.lower(), received_hash.lower()):
        raise HTTPException(401, "Invalid Telegram authentication")

    try:
        auth_date = int(data.get("auth_date", "0"))
    except (TypeError, ValueError):
        raise HTTPException(401, "Invalid Telegram auth_date")
    now = int(time.time())
    if auth_date <= 0 or auth_date > now + 30 or now - auth_date > TELEGRAM_AUTH_MAX_AGE:
        raise HTTPException(401, "Telegram authentication expired")

    try:
        user = json.loads(data["user"])
        uid = int(user["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(401, "Invalid Telegram user")
    if uid <= 0:
        raise HTTPException(401, "Invalid Telegram user")

    user["id"] = uid
    return user


def user_from_request(x_telegram_init_data, x_user_id=None):
    # In production X-User-Id is NEVER an identity source. It exists only to keep
    # local localhost development compatible with old routes.
    tg_user = verify_init_data(x_telegram_init_data or "")
    if tg_user:
        return int(tg_user["id"]), str(tg_user.get("username") or "")[:64], str(tg_user.get("first_name") or "Игрок")[:128]

    if _dev_auth_enabled() and x_user_id:
        try:
            uid = int(x_user_id)
        except (TypeError, ValueError):
            raise HTTPException(401, "Invalid local developer user")
        if uid <= 0:
            raise HTTPException(401, "Invalid local developer user")
        return uid, "developer", "Разработчик"

    raise HTTPException(401, "Authentication required")
'''

MIDDLEWARE_BLOCK = r'''# === CORPORATION SECURITY V22 MIDDLEWARE ====================================
# Per-process defensive rate limiting. Railway/proxy-level rate limiting is still
# recommended for DDoS protection; this layer protects application resources.
from collections import defaultdict, deque

_rate_buckets = defaultdict(deque)
_rate_lock = threading.Lock()


def _client_key(request: Request):
    # Do not trust a client-supplied Telegram ID for rate-limit identity.
    host = request.client.host if request.client else "unknown"
    return str(host)[:128]


def _rate_limited(key: str, limit: int, window: int = 60):
    now = time.monotonic()
    with _rate_lock:
        q = _rate_buckets[key]
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(now)
        # Opportunistic cleanup prevents an unbounded dictionary under scans.
        if len(_rate_buckets) > 10000:
            for old_key in list(_rate_buckets.keys())[:1000]:
                if not _rate_buckets[old_key] or _rate_buckets[old_key][-1] < cutoff:
                    _rate_buckets.pop(old_key, None)
        return False


@api.middleware("http")
async def corporation_security_guard(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()

    if path.startswith("/api/"):
        # Explicitly reject the vulnerable identity header on Railway. Even if an
        # old endpoint accidentally reads it, the request never reaches the route.
        if _is_railway_runtime() and request.headers.get("X-User-Id"):
            return JSONResponse(status_code=400, content={"detail": "Legacy authentication header is disabled"})

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_API_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

        client = _client_key(request)
        limit = 180
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            limit = 90
        if path.startswith("/api/admin/"):
            limit = 45
        if _rate_limited(f"{client}:{'admin' if path.startswith('/api/admin/') else method}", limit):
            return JSONResponse(status_code=429, content={"detail": "Too many requests"}, headers={"Retry-After": "60"})

        # Defense in depth: every API endpoint is authenticated centrally, in
        # addition to the existing per-route auth() / require_admin() checks.
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        if not init_data and _dev_auth_enabled():
            # Local-only compatibility. This branch can never execute on Railway.
            if not request.headers.get("X-User-Id"):
                return JSONResponse(status_code=401, content={"detail": "Local developer authentication required"})
        else:
            try:
                verify_init_data(init_data)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    response = await call_next(request)

    # Browser hardening. CSP intentionally allows Telegram SDK and HTTPS images.
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'self'; "
        "script-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
        "connect-src 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org"
    )
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if _is_railway_runtime():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
# ============================================================================
'''


def patch_app():
    text = APP.read_text(encoding="utf-8")
    original = text

    # hashlib/hmac/json/os/random/... imports already exist; ensure re is present.
    if not re.search(r"^import re$", text, re.M):
        text = text.replace("import random\n", "import random\nimport re\n", 1)

    # Fail closed if token/admin configuration is missing in Railway.
    marker = 'BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")'
    if marker in text:
        old_config = re.escape(marker) + r"\nADMIN_IDS = .*?\nSTARTING_MONEY = 10000\.0"
        text = replace_once(text, old_config, SECURITY_CONFIG, "основные security-переменные", flags=re.S)
    elif "CORPORATION SECURITY V22" not in text:
        raise RuntimeError("Не найден ожидаемый блок BOT_TOKEN/ADMIN_IDS. Обновление остановлено.")

    # _dev_auth_enabled references _is_railway_runtime, which is defined later and
    # resolved only when called, so declaration order is safe in Python.

    if "CORPORATION SECURITY V22" in text:
        # Add startup checks after _is_railway_runtime definition area / DB setup.
        startup_marker = "# ============================================================================\n\nTAX_RATE ="
        startup_check = '''# ============================================================================\n\nif _is_railway_runtime():\n    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":\n        raise RuntimeError("BOT_TOKEN must be configured in Railway")\n    if os.getenv("ALLOW_DEV_AUTH") == "1":\n        print("[SECURITY] ALLOW_DEV_AUTH ignored on Railway; Telegram auth is mandatory.")\n\nTAX_RATE ='''
        if startup_marker in text and "ALLOW_DEV_AUTH ignored on Railway" not in text:
            text = text.replace(startup_marker, startup_check, 1)

    # Replace old Telegram auth implementation as a whole.
    if "def verify_init_data(init_data: str):" in text and "Telegram authentication expired" not in text:
        pattern = r"def verify_init_data\(init_data: str\):.*?\n\ndef ensure_player\(uid, username=\"\"\):"
        text = replace_once(text, pattern, AUTH_BLOCK + '\n\ndef ensure_player(uid, username=""):', "verify_init_data/user_from_request", flags=re.S)

    # Insert central middleware right after FastAPI creation, before StaticFiles mount.
    if "CORPORATION SECURITY V22 MIDDLEWARE" not in text:
        needle = 'api = FastAPI(title="Corporation")\n'
        if needle not in text:
            raise RuntimeError("Не найдено создание FastAPI app.")
        text = text.replace(needle, needle + MIDDLEWARE_BLOCK + "\n", 1)

    # Do not expose backup filenames in overview. Admin can still create backups,
    # but UI only receives metadata that does not reveal filesystem names.
    text = re.sub(
        r'last_backup = \{"name": os\.path\.basename\(f\), "created_at": int\(os\.path\.getmtime\(f\)\), "size": os\.path\.getsize\(f\)\}',
        'last_backup = {"created_at": int(os.path.getmtime(f)), "size": os.path.getsize(f)}',
        text,
    )

    # Stronger SQLite pragmas without touching persistent data.
    old_db = '''def db():\n    conn = sqlite3.connect(DB_PATH, timeout=30)\n    conn.row_factory = sqlite3.Row\n    return conn'''
    new_db = '''def db():\n    conn = sqlite3.connect(DB_PATH, timeout=30)\n    conn.row_factory = sqlite3.Row\n    conn.execute("PRAGMA foreign_keys=ON")\n    conn.execute("PRAGMA busy_timeout=30000")\n    return conn'''
    if old_db in text:
        text = text.replace(old_db, new_db, 1)

    if text != original:
        write_if_changed(APP, text)
    else:
        print("app.py: security v22 уже установлен")


def patch_frontend_js(path: Path):
    text = path.read_text(encoding="utf-8")
    original = text

    # Common current pattern: Telegram initData or unconditional X-User-Id fallback.
    text = text.replace(
        'if (tg?.initData) headers["X-Telegram-Init-Data"]=tg.initData; else headers["X-User-Id"]=String(DEV_ID);',
        'if (tg?.initData) headers["X-Telegram-Init-Data"]=tg.initData; else if (["localhost","127.0.0.1"].includes(location.hostname)) headers["X-User-Id"]=String(DEV_ID); else throw new Error("Открой игру через Telegram");'
    )
    text = text.replace(
        "if (tg?.initData) headers['X-Telegram-Init-Data']=tg.initData; else headers['X-User-Id']=String(DEV_ID);",
        "if (tg?.initData) headers['X-Telegram-Init-Data']=tg.initData; else if (['localhost','127.0.0.1'].includes(location.hostname)) headers['X-User-Id']=String(DEV_ID); else throw new Error('Открой игру через Telegram');"
    )

    # Generic fallback used in later v20/admin scripts.
    text = re.sub(
        r'else\s+headers\[(["\'])X-User-Id\1\]\s*=\s*String\([^;]+\);',
        r'else if (["localhost","127.0.0.1"].includes(location.hostname)) headers["X-User-Id"]=String(DEV_ID); else throw new Error("Открой игру через Telegram");',
        text,
    )

    if text != original:
        write_if_changed(path, text)


def patch_gitignore():
    path = ROOT / ".gitignore"
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    additions = [
        ".env", ".env.*", "!.env.example", "admin_backups/", "security_backup_*/",
        "*.db", "*.db-wal", "*.db-shm", "*.db-journal", "__pycache__/", "*.pyc",
    ]
    lines = set(current.splitlines())
    missing = [x for x in additions if x not in lines]
    if missing:
        if path.exists():
            backup(path)
        with path.open("a", encoding="utf-8") as f:
            if current and not current.endswith("\n"):
                f.write("\n")
            f.write("\n# Security-sensitive/runtime files\n")
            for x in missing:
                f.write(x + "\n")
        print(".gitignore: усилен")


def patch_bot():
    if not BOT.exists():
        return
    text = BOT.read_text(encoding="utf-8")
    original = text
    text = re.sub(r'WEBAPP_VERSION\s*=\s*["\']\d+["\']', 'WEBAPP_VERSION = "220"', text, count=1)
    # Avoid leaking admin ID list into Railway logs.
    text = re.sub(r'f"version=\{WEBAPP_VERSION\} \| admin_ids=\{sorted\(ADMIN_IDS\)\}"', 'f"version={WEBAPP_VERSION} | admins={len(ADMIN_IDS)}"', text)
    if text != original:
        write_if_changed(BOT, text)


def main():
    print("=== Corporation Security Update v22 ===")
    patch_app()

    # Patch every first-party JS file that may contain API helper logic.
    for path in sorted(WEB.glob("*.js")):
        patch_frontend_js(path)

    patch_bot()
    patch_gitignore()

    print("\nГОТОВО.")
    print(f"Резервная копия изменённых файлов: {BACKUP_DIR.name}")
    print("ВАЖНО для Railway:")
    print("  1) BOT_TOKEN должен быть задан и совпадать у backend и Telegram bot.")
    print("  2) ADMIN_IDS должен содержать только Telegram ID администраторов.")
    print("  3) ALLOW_DEV_AUTH можно удалить; на Railway он теперь всё равно игнорируется.")
    print("  4) Не добавляй BOT_TOKEN / секреты в GitHub.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nОШИБКА: {exc}")
        print("Проверь, что обновление запускается на актуальном проекте Corporation.")
        sys.exit(1)
