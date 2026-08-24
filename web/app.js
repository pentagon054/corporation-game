
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const DEV_ID = 999001;
let state = null;
let page = "businesses";

function fmt(n){ return Number(n).toLocaleString("ru-RU") + " ₽"; }

async function api(url, options={}){
  const headers = {...(options.headers || {})};
  if (tg?.initData) headers["X-Telegram-Init-Data"] = tg.initData;
  else headers["X-User-Id"] = String(DEV_ID);

  const res = await fetch(url, {...options, headers});
  if(!res.ok){
    let data;
    try { data = await res.json(); } catch { data = {detail:"Ошибка сервера"}; }
    throw new Error(data.detail || "Ошибка");
  }
  return res.json();
}

function modal(title, text){
  document.querySelector("#modalTitle").textContent = title;
  document.querySelector("#modalText").textContent = text;
  document.querySelector("#modal").classList.remove("hidden");
}
document.querySelector("#modalClose").onclick = () => document.querySelector("#modal").classList.add("hidden");

function renderHeader(){
  const p = state.player;
  document.querySelector("#corpName").textContent = p.corp_name;
  document.querySelector("#money").textContent = fmt(p.money);
  document.querySelector("#income").textContent = fmt(state.hourly_income) + "/ч";
  document.querySelector("#reputation").textContent = p.reputation;
}

function renderBusinesses(){
  const html = state.businesses.map(b => {
    const can = !b.locked && state.player.money >= b.next_cost;
    return `<article class="card ${b.locked ? "locked":""}">
      <div class="business-head"><div><h3>${b.name}</h3><p>${b.desc}</p></div><b>ур. ${b.level}</b></div>
      <div class="meta"><span>📈 +${fmt(b.base_income * Math.max(1,b.level))}/ч</span><span>${b.locked ? "🔒 Реп. "+b.unlock : "⭐ Доступно"}</span></div>
      <button class="buy" ${can ? "" : "disabled"} onclick="buyBusiness('${b.id}')">
        ${b.level ? "Улучшить" : "Открыть"} за ${fmt(b.next_cost)}
      </button>
    </article>`;
  }).join("");
  document.querySelector("#content").innerHTML = `<div class="grid">${html}</div>`;
}

function renderTechs(){
  const html = state.techs.map(t => `<article class="card">
    <div class="business-head"><div><h3>${t.name}</h3><p>${t.desc}</p></div>${t.owned ? "✅" : ""}</div>
    <button class="buy" ${t.owned || state.player.money < t.cost ? "disabled":""} onclick="buyTech('${t.id}')">
      ${t.owned ? "Исследовано" : "Исследовать за "+fmt(t.cost)}
    </button>
  </article>`).join("");
  document.querySelector("#content").innerHTML = `<div class="grid">${html}</div>`;
}

async function renderRating(){
  document.querySelector("#content").innerHTML = `<div class="empty">Загружаем рейтинг...</div>`;
  try{
    const rows = await api("/api/rating");
    document.querySelector("#content").innerHTML = `<div class="grid">${rows.map((r,i)=>`
      <article class="card rank"><div class="rank-num">#${i+1}</div><div><h3>${r.corp_name}</h3><p>💰 ${fmt(r.money)} · ⭐ ${r.reputation}</p></div></article>`).join("")}</div>`;
  }catch(e){ modal("Ошибка",e.message); }
}

function render(){
  renderHeader();
  if(page === "businesses") renderBusinesses();
  if(page === "techs") renderTechs();
  if(page === "rating") renderRating();
}

async function refresh(){
  state = await api("/api/state");
  render();
}

window.buyBusiness = async function(id){
  try{ state = await api(`/api/business/${id}/buy`, {method:"POST"}); render(); }
  catch(e){ modal("Не удалось",e.message); }
}

window.buyTech = async function(id){
  try{ state = await api(`/api/tech/${id}/buy`, {method:"POST"}); render(); }
  catch(e){ modal("Не удалось",e.message); }
}

document.querySelector("#collectBtn").onclick = async () => {
  try{
    const result = await api("/api/collect",{method:"POST"});
    state = result.state;
    render();
    modal(result.event.name, `${result.event.desc}\n\nТы получил ${fmt(result.earned)}.`);
    tg?.HapticFeedback?.notificationOccurred("success");
  }catch(e){
    modal("Доход",e.message);
    tg?.HapticFeedback?.notificationOccurred("error");
  }
};

document.querySelector("#renameBtn").onclick = async () => {
  const name = prompt("Новое название корпорации:", state.player.corp_name);
  if(!name) return;
  try{
    state = await api("/api/rename",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({name})
    });
    render();
  }catch(e){ modal("Ошибка",e.message); }
};

document.querySelectorAll(".tab").forEach(btn => btn.onclick = () => {
  page = btn.dataset.page;
  document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===btn));
  render();
});

refresh().catch(e => modal("Ошибка запуска",e.message));
