(() => {
  "use strict";
  if (window.__corpOwnerConsole27) return;
  window.__corpOwnerConsole27 = true;

  const A = window.__corpAdmin;
  if (!A) return;

  const style = document.createElement("style");
  style.textContent = `
    .v27-owner-credit{background:#d9bf85!important;color:#17130a!important;border:0!important}
    .v27-owner-overlay{position:fixed;inset:0;z-index:9000;background:#000b;display:grid;place-items:center;padding:16px;backdrop-filter:blur(8px)}
    .v27-owner-card{width:min(480px,100%);background:#151519;border:1px solid rgba(217,191,133,.28);border-radius:20px;padding:18px;box-shadow:0 28px 70px #0009}
    .v27-owner-card h3{margin:0 0 5px}.v27-owner-meta{font-size:12px;color:#a9abb3;line-height:1.5}
    .v27-owner-card label{display:grid;gap:6px;margin-top:12px;font-size:12px;color:#a9abb3}
    .v27-owner-card input,.v27-owner-card select{width:100%;padding:12px;border-radius:11px;border:1px solid #ffffff20;background:#0e0e11;color:#fff}
    .v27-owner-buttons{display:grid;grid-template-columns:1fr 1.25fr;gap:8px;margin-top:16px}
    .v27-owner-buttons button{padding:12px;border-radius:11px;border:1px solid #ffffff18;background:#202126;color:#fff;font-weight:850}
    .v27-owner-buttons [data-v27-ok]{background:#d9bf85;color:#17130a;border-color:#d9bf85}
    .v27-owner-error{min-height:18px;color:#ff8d8d;font-size:12px;margin-top:7px}
    .v27-owner-result{margin-top:10px;padding:10px;border-radius:10px;background:#ffffff08;color:#d9dce3;font-size:12px;line-height:1.45}
  `;
  document.head.appendChild(style);

  const esc = A.escape || (s => String(s ?? ""));
  const money = A.money || (n => `${Number(n || 0).toLocaleString("ru-RU")} ₽`);
  let busy = false;

  function dialog(playerId, playerName) {
    return new Promise(resolve => {
      const wrap = document.createElement("div");
      wrap.className = "v27-owner-overlay";
      wrap.innerHTML = `<div class="v27-owner-card">
        <h3>Начислить деньги</h3>
        <div class="v27-owner-meta">${esc(playerName)} · ID ${playerId}</div>
        <label>Сумма<input data-v27-amount type="number" min="0.01" step="0.01" inputmode="decimal" value="100000"></label>
        <label>Какой это доход<select data-v27-source>
          <option value="business">Бизнес</option>
          <option value="dividends">Дивиденды</option>
          <option value="bonds">Облигации</option>
          <option value="rent">Аренда недвижимости</option>
          <option value="trading">Прибыль от акций</option>
          <option value="bonus" selected>Бонус / другое</option>
        </select></label>
        <label>Комментарий (необязательно)<input data-v27-note maxlength="160" placeholder="Например: компенсация"></label>
        <div class="v27-owner-buttons"><button data-v27-cancel>Отмена</button><button data-v27-ok>Начислить</button></div>
        <div class="v27-owner-error"></div>
        <div class="v27-owner-result" hidden></div>
      </div>`;
      document.body.appendChild(wrap);
      const amountInput = wrap.querySelector("[data-v27-amount]");
      const close = value => { wrap.remove(); resolve(value); };
      wrap.addEventListener("click", async ev => {
        if (ev.target === wrap || ev.target.closest("[data-v27-cancel]")) return close(null);
        if (ev.target.closest("[data-v27-ok][data-v27-done='1']")) return;
        if (!ev.target.closest("[data-v27-ok]") || busy) return;
        const amount = Number(amountInput.value);
        const source = wrap.querySelector("[data-v27-source]").value;
        const note = wrap.querySelector("[data-v27-note]").value.trim();
        const err = wrap.querySelector(".v27-owner-error");
        if (!Number.isFinite(amount) || amount <= 0) { err.textContent = "Укажи положительную сумму."; return; }
        busy = true;
        const ok = wrap.querySelector("[data-v27-ok]");
        ok.disabled = true; ok.textContent = "Начисляю…"; err.textContent = "";
        try {
          const result = await A.request(`/api/admin/private-operation/${playerId}`, {method:"POST", body:JSON.stringify({amount,source,note})});
          const box = wrap.querySelector(".v27-owner-result");
          box.hidden = false;
          box.textContent = `Готово: ${money(result.credited)} · ${result.source_label}. Баланс: ${money(result.balance_before)} → ${money(result.balance_after)}`;
          ok.textContent = "Готово";
          ok.disabled = false;
          ok.dataset.v27Done = "1";
          await A.reload();
        } catch (e) {
          err.textContent = e?.message || "Начисление не выполнено";
          ok.disabled = false; ok.textContent = "Начислить";
        } finally { busy = false; }
      });
      wrap.addEventListener("click", ev => {
        const ok = ev.target.closest("[data-v27-ok][data-v27-done='1']");
        if (ok) close(true);
      });
      setTimeout(() => amountInput?.focus({preventScroll:true}), 30);
    });
  }

  function decorate(root = document) {
    root.querySelectorAll(".v22-player[data-player-id]").forEach(card => {
      const actions = card.querySelector(".v22-actions");
      if (!actions || actions.querySelector(".v27-owner-credit")) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "v27-owner-credit";
      btn.textContent = "+ Деньги";
      btn.addEventListener("click", ev => {
        ev.preventDefault(); ev.stopPropagation();
        dialog(Number(card.dataset.playerId), card.dataset.playerName || card.dataset.playerId);
      });
      actions.prepend(btn);
    });
  }

  window.addEventListener("corp-admin-players-rendered", e => decorate(e.detail?.root || document));
  decorate(document);
})();
