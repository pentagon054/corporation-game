from pathlib import Path
import re
import shutil
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parent
STYLE = ROOT / "web" / "style.css"
INDEX = ROOT / "web" / "index.html"
BOT = ROOT / "bot.py"

CSS_MARKER_START = "/* === CORPORATION V14.2: MOBILE NAV HARD FIX =============================== */"
CSS_MARKER_END = "/* === END CORPORATION V14.2 ================================================ */"

CSS_PATCH = r"""
/* === CORPORATION V14.2: MOBILE NAV HARD FIX =============================== */
*,
*::before,
*::after {
  box-sizing: border-box;
}

/* Всегда привязываем меню к реальной ширине Telegram WebView.
   Никакого центрирования через 50%/translateX и никакой фиксированной ширины. */
.tabs {
  position: fixed !important;
  left: 6px !important;
  right: 6px !important;
  bottom: max(6px, env(safe-area-inset-bottom)) !important;

  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;

  margin: 0 !important;
  padding: 6px !important;
  transform: none !important;

  display: grid !important;
  grid-template-columns: repeat(6, minmax(0, 1fr)) !important;
  align-items: stretch !important;
  gap: 2px !important;

  overflow: hidden !important;
  z-index: 1000 !important;

  border: 1px solid rgba(255,255,255,.58) !important;
  border-radius: 22px !important;
  background: rgba(244,244,239,.98) !important;
  box-shadow: 0 14px 34px rgba(0,0,0,.38) !important;
  backdrop-filter: blur(18px) !important;
  -webkit-backdrop-filter: blur(18px) !important;
}

.tabs .tab,
.tabs .tab[data-page="realestate"] {
  position: relative !important;
  left: auto !important;
  right: auto !important;
  top: auto !important;
  bottom: auto !important;

  width: 100% !important;
  min-width: 0 !important;
  max-width: 100% !important;
  height: 54px !important;
  min-height: 54px !important;

  margin: 0 !important;
  padding: 5px 1px 4px !important;
  transform: none !important;

  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 3px !important;

  border: 0 !important;
  border-radius: 16px !important;
  background: transparent !important;
  color: #171719 !important;
  box-shadow: none !important;
  overflow: hidden !important;
}

.tabs .tab.active,
.tabs .tab[data-page="realestate"].active {
  background: #151517 !important;
  color: #ffd400 !important;
  transform: none !important;
  box-shadow: none !important;
}

.tabs .tab::before,
.tabs .tab::after,
.tabs .tab[data-page="realestate"]::before,
.tabs .tab[data-page="realestate"]::after {
  content: none !important;
  display: none !important;
}

.tabs .nav-icon {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;

  width: 20px !important;
  height: 20px !important;
  min-width: 20px !important;
  flex: 0 0 20px !important;

  color: currentColor !important;
  font-size: 21px !important;
  line-height: 20px !important;
  font-weight: 900 !important;
}

.tabs .nav-icon svg {
  display: block !important;
  width: 20px !important;
  height: 20px !important;
  fill: none !important;
  stroke: currentColor !important;
  stroke-width: 2 !important;
  stroke-linecap: round !important;
  stroke-linejoin: round !important;
}

.tabs .nav-label {
  display: block !important;
  width: 100% !important;
  min-width: 0 !important;

  overflow: hidden !important;
  white-space: nowrap !important;
  text-overflow: clip !important;

  text-align: center !important;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
  font-size: 7px !important;
  line-height: 9px !important;
  font-weight: 800 !important;
  letter-spacing: -0.28px !important;
}

.tabs .tab[data-page="realestate"] .nav-label {
  font-size: 6.2px !important;
  letter-spacing: -0.48px !important;
}

/* На очень узких экранах сохраняем все шесть кнопок внутри viewport. */
@media (max-width: 390px) {
  .tabs {
    left: 4px !important;
    right: 4px !important;
    padding: 5px 4px !important;
    gap: 1px !important;
  }

  .tabs .tab,
  .tabs .tab[data-page="realestate"] {
    height: 52px !important;
    min-height: 52px !important;
    border-radius: 14px !important;
  }

  .tabs .nav-icon,
  .tabs .nav-icon svg {
    width: 19px !important;
    height: 19px !important;
  }

  .tabs .nav-label {
    font-size: 6.5px !important;
    letter-spacing: -0.4px !important;
  }

  .tabs .tab[data-page="realestate"] .nav-label {
    font-size: 5.8px !important;
    letter-spacing: -0.55px !important;
  }
}

/* Старое desktop-правило v14 больше не должно сдвигать панель. */
@media (min-width: 430px) {
  .tabs {
    left: 6px !important;
    right: 6px !important;
    width: auto !important;
    max-width: none !important;
    transform: none !important;
  }
}

#content {
  padding-bottom: 88px !important;
}

.app {
  padding-bottom: 98px !important;
}
/* === END CORPORATION V14.2 ================================================ */
"""

def backup(path: Path):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(path.name + f".backup_{stamp}")
    shutil.copy2(path, target)
    return target

def patch_style():
    text = STYLE.read_text(encoding="utf-8")

    # Удаляем предыдущую копию v14.2 при повторном запуске.
    pattern = re.compile(
        re.escape(CSS_MARKER_START) + r".*?" + re.escape(CSS_MARKER_END),
        re.S,
    )
    text = pattern.sub("", text).rstrip() + "\n\n" + CSS_PATCH.strip() + "\n"

    backup(STYLE)
    STYLE.write_text(text, encoding="utf-8")
    print("web/style.css: нижняя панель жёстко привязана к ширине WebView.")

def bump_index():
    text = INDEX.read_text(encoding="utf-8")
    new = re.sub(r'(/static/style\.css\?v=)[^"\']+', r'\g<1>142', text)
    new = re.sub(r'(/static/app\.js\?v=)[^"\']+', r'\g<1>142', new)
    if new != text:
        backup(INDEX)
        INDEX.write_text(new, encoding="utf-8")
    print("web/index.html: cache version -> 142.")

def bump_bot():
    if not BOT.exists():
        return
    text = BOT.read_text(encoding="utf-8")
    new = re.sub(
        r'WEBAPP_VERSION\s*=\s*["\'][^"\']+["\']',
        'WEBAPP_VERSION = "142"',
        text,
        count=1,
    )
    if new != text:
        backup(BOT)
        BOT.write_text(new, encoding="utf-8")
    print("bot.py: WebApp version -> 142.")

def main():
    if not STYLE.exists() or not INDEX.exists():
        raise RuntimeError(
            "Не найдены web/style.css или web/index.html. "
            "Распакуй архив в корень проекта рядом с app.py и папкой web."
        )

    print("=== Corporation v14.2 Bottom Nav Fix ===")
    patch_style()
    bump_index()
    bump_bot()

    print()
    print("ГОТОВО.")
    print("- панель больше не центрируется через translateX;")
    print("- width:auto + left/right удерживают её внутри Telegram WebView;")
    print("- все 6 вкладок остаются видимыми;")
    print("- app.py и corporation.db НЕ изменялись.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ОШИБКА:", exc)
        sys.exit(1)
