from pathlib import Path
from datetime import datetime
import shutil
import sys

START = "# === CORPORATION LOAD TEST V4 START ==="
END = "# === CORPORATION LOAD TEST V4 END ==="

def main():
    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    app = project / "app.py"

    if not app.exists():
        raise SystemExit(f"app.py not found: {app}")

    text = app.read_text(encoding="utf-8")
    a = text.find(START)
    b = text.find(END)

    if a < 0 or b < 0 or b < a:
        print("V4 load-test block not found; nothing to remove.")
        return

    b += len(END)
    while b < len(text) and text[b] in "\r\n":
        b += 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = app.with_name(f"app.py.backup_before_remove_loadtest_v4_{stamp}")
    shutil.copy2(app, backup)

    new_text = text[:a].rstrip() + "\n\n\n" + text[b:].lstrip()
    app.write_text(new_text, encoding="utf-8")

    print("Removed V4 temporary load-test endpoint.")
    print(f"Backup: {backup.name}")
    print("Also remove LOAD_TEST_TOKEN from Railway Variables after deploy.")

if __name__ == "__main__":
    main()
