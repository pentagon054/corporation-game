from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"

CORRECT_BLOCK = r"""# === CORPORATION_PERSISTENT_DB_V14_1 ==========================================
def _is_railway_runtime():
    return bool(
        os.getenv("RAILWAY_DEPLOYMENT_ID")
        or os.getenv("RAILWAY_PROJECT_ID")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("RAILWAY_SERVICE_ID")
    )


def _resolve_database_path():
    configured = (os.getenv("DB_PATH") or "").strip()
    volume_mount = (os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "").strip()

    if _is_railway_runtime():
        if not volume_mount:
            raise RuntimeError(
                "Railway Volume не подключён к backend-сервису. "
                "Corporation остановлена, чтобы не создать временную базу."
            )

        volume_mount = os.path.abspath(volume_mount)
        os.makedirs(volume_mount, exist_ok=True)

        probe = os.path.join(volume_mount, ".corporation_write_test")
        try:
            with open(probe, "a", encoding="utf-8"):
                pass
            if os.path.exists(probe):
                os.remove(probe)
        except OSError as exc:
            raise RuntimeError(
                f"Railway Volume недоступен для записи: {volume_mount}: {exc}"
            ) from exc

        db_name = os.path.basename(configured) if configured else "corporation.db"
        if not db_name or db_name in (".", ".."):
            db_name = "corporation.db"

        persistent_path = os.path.abspath(os.path.join(volume_mount, db_name))
        if os.path.commonpath([persistent_path, volume_mount]) != volume_mount:
            raise RuntimeError("DB_PATH пытается выйти за пределы Railway Volume.")

        os.environ["DB_PATH"] = persistent_path
        return persistent_path

    return configured or "corporation.db"


DB_PATH = _resolve_database_path()
os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)) or ".", exist_ok=True)

if _is_railway_runtime():
    _mount = os.path.abspath(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ""))
    _exists = os.path.exists(DB_PATH)
    _size = os.path.getsize(DB_PATH) if _exists else 0
    print(
        f"[Corporation] PERSISTENT STORAGE OK | "
        f"mount={_mount} | db={DB_PATH} | exists={_exists} | size={_size}"
    )
else:
    print(f"[Corporation] Local SQLite database: {DB_PATH}")
# ============================================================================"""

def backup(path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(path.name + f".backup_{stamp}")
    shutil.copy2(path, target)
    return target

def main():
    if not APP.exists():
        raise RuntimeError("Не найден app.py. Запусти hotfix из корня проекта.")

    text = APP.read_text(encoding="utf-8")

    patterns = [
        r'# === CORPORATION_PERSISTENT_DB_V14_1 ={5,}.*?# ={20,}',
        r'# === CORPORATION_PERSISTENT_DB_V14 ={5,}.*?# ={20,}',
        r'# === CORPORATION_PERSISTENT_DB_V12 ={5,}.*?# ={20,}',
    ]

    new_text = None
    for p in patterns:
        if re.search(p, text, flags=re.S):
            new_text = re.sub(p, CORRECT_BLOCK, text, count=1, flags=re.S)
            break

    if new_text is None:
        raise RuntimeError("Не найден persistence-блок в app.py. Ничего не изменено.")

    b = backup(APP)
    APP.write_text(new_text, encoding="utf-8")

    # Syntax validation before user pushes.
    import py_compile
    try:
        py_compile.compile(str(APP), doraise=True)
    except Exception:
        shutil.copy2(b, APP)
        raise RuntimeError("Проверка синтаксиса не прошла. app.py автоматически восстановлен из backup.")

    print("ГОТОВО: app.py исправлен и успешно прошёл py_compile.")
    print(f"Backup: {b.name}")
    print("Теперь можно делать git add/commit/push.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ОШИБКА:", exc)
        sys.exit(1)
