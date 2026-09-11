from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path.cwd()
WEB = ROOT / "web"
INDEX = WEB / "index.html"
JS = WEB / "v22_1.js"

def die(msg):
    print(f"\n[ERROR] {msg}")
    raise SystemExit(1)

if not WEB.exists():
    die("Папка web не найдена. Распакуй архив в корень проекта Corporation.")
if not INDEX.exists():
    die("web/index.html не найден.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = ROOT / f"backup_before_v22_1_{stamp}"
backup.mkdir(exist_ok=True)

for file in (INDEX, WEB / "v22.js", JS):
    if file.exists():
        shutil.copy2(file, backup / file.name)

js = r'''(() => {
  const STYLE_ID = "corporation-v22-1-refresh-style";
  const BUTTON_ID = "corpV221Refresh";

  function installStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .corp-v22-refresh { display:none !important; }

      .hero { position:relative; }

      .corp-v22-1-actions{
        display:flex;
        align-items:center;
        gap:8px;
        flex:0 0 auto;
      }

      .corp-v22-1-refresh{
        width:42px;
        height:42px;
        border:1px solid rgba(255,212,0,.34);
        background:radial-gradient(circle at 35% 25%,rgba(255,212,0,.12),transparent 48%),#151517;
        color:#ffd400;
        border-radius:50%;
        display:grid;
        place-items:center;
        padding:0;
        font-size:22px;
        line-height:1;
        font-weight:950;
        box-shadow:0 7px 20px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.04);
        -webkit-tap-highlight-color:transparent;
      }

      .corp-v22-1-refresh:active{transform:scale(.94)}
      .corp-v22-1-refresh.loading .corp-v22-1-refresh-icon{animation:corpV221Spin .65s linear infinite}
      .corp-v22-1-refresh:disabled{opacity:.72}

      @keyframes corpV221Spin{to{transform:rotate(360deg)}}

      .corp-v22-1-refresh-icon{display:block;line-height:1}

      @media(max-width:360px){
        .corp-v22-1-actions{gap:6px}
        .corp-v22-1-refresh,#renameBtn.icon{width:39px;height:39px}
      }
    `;
    document.head.appendChild(style);
  }

  function getCurrentPage(){
    return document.querySelector(".tabs .tab.active")?.dataset?.page || "businesses";
  }

  async function refreshCurrentData(button){
    if(button?.classList.contains("loading")) return;

    try{
      if(button){
        button.classList.add("loading");
        button.disabled=true;
      }

      if(typeof api === "function"){
        const freshState = await api("/api/state");
        if(typeof state !== "undefined") state = freshState;
        if(typeof renderHeader === "function") renderHeader();
      }

      const activePage = getCurrentPage();

      if(activePage === "businesses" && typeof renderBusinesses === "function"){
        renderBusinesses();
      }else if(activePage === "investments"){
        if(typeof renderInvestments === "function") await renderInvestments();
        else if(typeof refreshInvestments === "function") await refreshInvestments();
      }else if(activePage === "realestate"){
        if(typeof renderRealEstate === "function") await renderRealEstate();
        else if(typeof renderRealestate === "function") await renderRealestate();
      }else if(activePage === "taxes" && typeof renderTaxes === "function"){
        await renderTaxes();
      }else if(activePage === "statistics" && typeof renderStatistics === "function"){
        await renderStatistics();
      }else if(activePage === "rating" && typeof renderRating === "function"){
        await renderRating();
      }

      try{
        window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.("light");
      }catch(_){}

    }catch(error){
      console.error("[Corporation v22.1] refresh failed:", error);
      try{
        const url = new URL(window.location.href);
        url.searchParams.set("_refresh", String(Date.now()));
        window.location.replace(url.toString());
        return;
      }catch(_){}
    }finally{
      if(button){
        setTimeout(()=>{
          button.classList.remove("loading");
          button.disabled=false;
        },280);
      }
    }
  }

  function installRefreshButton(){
    installStyles();

    const hero = document.querySelector(".hero");
    const renameButton = document.querySelector("#renameBtn");

    if(!hero || !renameButton) return false;
    if(document.getElementById(BUTTON_ID)) return true;

    let actions = hero.querySelector(".corp-v22-1-actions");

    if(!actions){
      actions = document.createElement("div");
      actions.className = "corp-v22-1-actions";
      renameButton.parentNode.insertBefore(actions, renameButton);
      actions.appendChild(renameButton);
    }

    const button = document.createElement("button");
    button.id = BUTTON_ID;
    button.className = "corp-v22-1-refresh";
    button.type = "button";
    button.title = "Обновить данные";
    button.setAttribute("aria-label","Обновить баланс, статистику, рейтинг и котировки");
    button.innerHTML = '<span class="corp-v22-1-refresh-icon" aria-hidden="true">↻</span>';
    button.addEventListener("click",()=>refreshCurrentData(button));

    actions.insertBefore(button, renameButton);
    return true;
  }

  installRefreshButton();

  let attempts=0;
  const timer=setInterval(()=>{
    attempts+=1;
    if(installRefreshButton() || attempts>40) clearInterval(timer);
  },250);

  const observer=new MutationObserver(()=>installRefreshButton());
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();'''

JS.write_text(js, encoding="utf-8")

html = INDEX.read_text(encoding="utf-8")
tag = '<script src="/static/v22_1.js?v=221"></script>'

if tag not in html:
    if "</body>" not in html:
        die("В web/index.html не найден </body>.")
    html = html.replace("</body>", f"  {tag}\n</body>")
    INDEX.write_text(html, encoding="utf-8")
    print("[OK] v22_1.js подключён в web/index.html")
else:
    print("[OK] v22_1.js уже подключён")

print("[OK] Кнопка ↻ добавлена в верхнюю панель слева от карандаша.")
print("[OK] Обновляется текущая открытая вкладка.")
print("[OK] БД и Railway Volume не изменяются.")
print(f"[OK] Backup: {backup.name}")
