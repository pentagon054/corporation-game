from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
BOT = ROOT / "bot.py"
INDEX = ROOT / "web" / "index.html"

MARKER = "CORPORATION_PERSISTENT_DB_V12"
PERSISTENCE_BLOCK = '# === CORPORATION_PERSISTENT_DB_V12 ============================================\ndef _resolve_database_path():\n    configured = (os.getenv("DB_PATH") or "").strip()\n    volume_mount = (os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "").strip()\n\n    is_railway = bool(\n        os.getenv("RAILWAY_DEPLOYMENT_ID")\n        or os.getenv("RAILWAY_PROJECT_ID")\n        or os.getenv("RAILWAY_ENVIRONMENT_NAME")\n        or os.getenv("RAILWAY_SERVICE_ID")\n    )\n\n    if volume_mount:\n        volume_mount = os.path.abspath(volume_mount)\n        os.makedirs(volume_mount, exist_ok=True)\n\n        if configured:\n            db_name = os.path.basename(configured.rstrip("/\\\\"))\n            if not db_name or db_name in (".", ".."):\n                db_name = "corporation.db"\n        else:\n            db_name = "corporation.db"\n\n        persistent_path = os.path.join(volume_mount, db_name)\n        os.environ["DB_PATH"] = persistent_path\n        return persistent_path\n\n    if is_railway:\n        raise RuntimeError(\n            "Railway Volume is not attached to the backend service. "\n            "Attach a Volume to Railway #1. The game refuses to start "\n            "without persistent storage to protect player progress."\n        )\n\n    return configured or "corporation.db"\n\n\nDB_PATH = _resolve_database_path()\nos.makedirs(os.path.dirname(os.path.abspath(DB_PATH)) or ".", exist_ok=True)\nprint(f"[Corporation] Persistent SQLite database: {DB_PATH}")\n# ============================================================================'

def backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(path.name + f".backup_{stamp}")
    shutil.copy2(path, target)
    return target

def patch_app():
    if not APP.exists():
        raise FileNotFoundError(
            f"Не найден {APP}. Положи файлы обновления в корень проекта рядом с app.py."
        )

    text = APP.read_text(encoding="utf-8")

    if MARKER in text:
        print("app.py уже содержит защиту постоянных сохранений — пропускаю.")
        return

    old_line = 'DB_PATH = os.getenv("DB_PATH", "corporation.db")'
    if old_line not in text:
        raise RuntimeError(
            "Не нашёл ожидаемую строку DB_PATH в app.py. "
            "Файл отличается от присланной версии — обновление остановлено без изменений."
        )

    b = backup(APP)
    text = text.replace(old_line, PERSISTENCE_BLOCK, 1)
    APP.write_text(text, encoding="utf-8")
    print(f"Готово: app.py обновлён. Резервная копия: {b.name}")

def bump_versions():
    if BOT.exists():
        text = BOT.read_text(encoding="utf-8")
        new = re.sub(r'WEBAPP_VERSION\s*=\s*["\']\d+["\']',
                     'WEBAPP_VERSION = "12"', text, count=1)
        if new != text:
            backup(BOT)
            BOT.write_text(new, encoding="utf-8")
            print("bot.py: версия WebApp обновлена до 12.")

    if INDEX.exists():
        text = INDEX.read_text(encoding="utf-8")
        new = re.sub(r'(/static/(?:style\.css|app\.js)\?v=)\d+',
                     r'\g<1>12', text)
        if new != text:
            backup(INDEX)
            INDEX.write_text(new, encoding="utf-8")
            print("web/index.html: cache-busting версия обновлена до 12.")

def write_gitignore():
    gitignore = ROOT / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    existing_lines = existing.splitlines()
    additions = [
        "corporation.db",
        "*.db-wal",
        "*.db-shm",
        "*.db-journal",
        "__pycache__/",
        "*.pyc",
    ]
    missing = [x for x in additions if x not in existing_lines]
    if missing:
        with gitignore.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# Corporation runtime data — never deploy player DB from GitHub\n")
            for item in missing:
                f.write(item + "\n")
        print(".gitignore: база и временные SQLite-файлы исключены из будущих коммитов.")

def main():
    print("=== Corporation v12: persistent saves update ===")
    patch_app()
    bump_versions()
    write_gitignore()
    print()
    print("ОБНОВЛЕНИЕ УСТАНОВЛЕНО.")
    print("Railway backend теперь автоматически использует RAILWAY_VOLUME_MOUNT_PATH.")
    print("Важно: Volume должен быть подключён именно к Railway #1 (FastAPI backend).")
    print()
    print('Дальше: git add . && git commit -m "Fix persistent player saves" && git push origin main')

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("ОШИБКА:", exc)
        print("Никакие действия с corporation.db не выполнялись.")
        sys.exit(1)
