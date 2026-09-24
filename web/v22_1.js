(() => {
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
        border:1px solid rgba(221,194,139,.34);
        background:radial-gradient(circle at 35% 25%,rgba(221,194,139,.12),transparent 48%),#151517;
        color:#ddc28b;
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
      modal("Не удалось обновить", error.message || "Проверь соединение и попробуй снова.");
    }finally{
      if(button){
        button.classList.remove("loading");
        button.disabled=false;
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

})();
