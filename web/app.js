const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();

  try {
    tg.setHeaderColor("bg_color");
    tg.setBackgroundColor("bg_color");
  } catch (e) {
    console.warn("Telegram UI settings unavailable:", e);
  }
}

const DEV_ID = 999001;

let state = null;
let page = "businesses";

let stocksCache = [];
let brokerageCache = null;


/* ============================================================
   HELPERS
============================================================ */

function fmt(n) {
  return Number(n || 0).toLocaleString("ru-RU") + " ₽";
}

function fmtNumber(n) {
  return Number(n || 0).toLocaleString("ru-RU", {
    maximumFractionDigits: 2
  });
}

function fmtPercent(n) {
  const value = Number(n || 0);

  return (
    value > 0 ? "+" : ""
  ) + value.toFixed(2) + "%";
}


/* ============================================================
   API
============================================================ */

async function api(url, options = {}) {

  const headers = {
    ...(options.headers || {})
  };

  if (tg?.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  } else {
    headers["X-User-Id"] = String(DEV_ID);
  }

  const res = await fetch(url, {
    ...options,
    headers,
    cache: "no-store"
  });

  if (!res.ok) {

    let data;

    try {
      data = await res.json();
    } catch {
      data = {
        detail: "Ошибка сервера"
      };
    }

    throw new Error(
      data.detail || "Ошибка"
    );
  }

  return res.json();
}


/* ============================================================
   MODAL
============================================================ */

function modal(title, text) {

  document.querySelector("#modalTitle").textContent = title;

  document.querySelector("#modalText").innerHTML =
    typeof text === "string"
      ? text.replace(/\n/g, "<br>")
      : text;

  document.querySelector("#modal")
    .classList
    .remove("hidden");
}


document.querySelector("#modalClose").onclick = () => {

  document.querySelector("#modal")
    .classList
    .add("hidden");
};


/* ============================================================
   HEADER
============================================================ */

function businessCount() {

  if (!state?.businesses) {
    return 0;
  }

  return state.businesses.filter(
    business => Number(business.level || 0) > 0
  ).length;
}



function renderHeader() {

  if (!state || !state.player) {
    return;
  }

  const player = state.player;

  document.querySelector("#corpName").textContent =
    player.corp_name;

  document.querySelector("#money").textContent =
    fmt(player.money);

  document.querySelector("#income").textContent =
    fmt(state.hourly_income) + "/ч";

  document.querySelector("#businessCount").textContent =
    businessCount();
}


/* ============================================================
   BUSINESSES
============================================================ */

function renderBusinesses() {

  const html = (state.businesses || [])
    .map(business => {

      const canBuy =
        Number(state.player.money || 0)
        >= Number(business.next_cost || 0);

      const owned = Number(business.level || 0) > 0;

      return `
        <article class="card">

          <div class="business-head">
            <div>
              <h3>${business.name}</h3>
              <p>${business.desc}</p>
            </div>
            <b>ур. ${business.level}</b>
          </div>

          <div class="business-income-box">
            <span>${owned ? "Текущий доход" : "После покупки"}</span>
            <b>
              ${owned
                ? fmt(business.current_income) + "/ч"
                : fmt(business.income_after_purchase) + "/ч"}
            </b>
          </div>

          ${owned ? `
            <div class="business-income-next">
              После улучшения: <b>${fmt(business.income_after_purchase)}/ч</b>
            </div>
          ` : ""}

          <button
            class="buy"
            ${canBuy ? "" : "disabled"}
            onclick="buyBusiness('${business.id}')"
          >
            ${owned ? "Улучшить" : "Открыть"}
            за ${fmt(business.next_cost)}
          </button>

          ${owned ? `
            <button
              class="sell-business"
              onclick="sellBusiness('${business.id}')"
            >
              Продать бизнес за ${fmt(business.sell_price)}
            </button>
            <div class="business-capitalization">
              Капитализация: ${fmt(business.capitalization)} · продажа 30%
            </div>
          ` : ""}

        </article>
      `;
    })
    .join("");

  document.querySelector("#content").innerHTML = `
    <div class="grid">
      ${html}
    </div>
  `;
}


/* ============================================================
   TECHNOLOGIES
============================================================ */

function renderTechs() {

  const html = (state.techs || [])
    .map(tech => `

      <article class="card">

        <div class="business-head">

          <div>

            <h3>
              ${tech.name}
            </h3>

            <p>
              ${tech.desc}
            </p>

          </div>

          ${tech.owned ? "✅" : ""}

        </div>

        <button
          class="buy"
          ${
            tech.owned ||
            Number(state.player.money || 0)
              < Number(tech.cost || 0)
              ? "disabled"
              : ""
          }
          onclick="buyTech('${tech.id}')"
        >

          ${
            tech.owned
              ? "Исследовано"
              : "Исследовать за " + fmt(tech.cost)
          }

        </button>

      </article>

    `)
    .join("");

  document.querySelector("#content").innerHTML = `
    <div class="grid">
      ${html}
    </div>
  `;
}


/* ============================================================
   STATISTICS
============================================================ */

function renderProfitChart(data) {

  if (!data || !data.length) {

    return `
      <div class="empty">
        Пока нет собранной прибыли.
      </div>
    `;
  }

  const max = Math.max(
    ...data.map(item =>
      Number(item.earned || 0)
    ),
    1
  );

  return `
    <div class="profit-chart">

      ${data.map(item => {

        const earned =
          Number(item.earned || 0);

        const height = Math.max(
          6,
          Math.round(
            earned / max * 100
          )
        );

        const date =
          String(item.day || "")
            .split("-")
            .slice(1)
            .join(".");

        return `
          <div class="chart-column">

            <div class="chart-value">
              ${fmt(earned)}
            </div>

            <div
              class="chart-bar"
              style="height:${height}%"
            ></div>

            <div class="chart-date">
              ${date}
            </div>

          </div>
        `;

      }).join("")}

    </div>
  `;
}


async function renderStatistics() {

  document.querySelector("#content").innerHTML = `
    <div class="empty">
      Загружаем статистику...
    </div>
  `;

  try {

    const stats =
      await api("/api/statistics");

    document.querySelector("#content").innerHTML = `

      <section class="stats-page">

        <article class="stats-card">

          <span>
            💰 Общая прибыль
          </span>

          <b>
            ${fmt(stats.total_earned)}
          </b>

        </article>

        <article class="stats-card">

          <span>
            💸 Общие расходы
          </span>

          <b>
            ${fmt(stats.total_spent)}
          </b>

        </article>

        <article class="stats-card">

          <span>
            🏢 Куплено бизнесов
          </span>

          <b>
            ${stats.companies_bought}
          </b>

        </article>

        <section class="chart-card">

          <h2>
            📊 Прибыль по дням
          </h2>

          <p>
            Один столбец — один день
          </p>

          ${renderProfitChart(
            stats.daily_profit || []
          )}

        </section>

      </section>
    `;

  } catch (error) {

    modal(
      "Ошибка",
      error.message
    );
  }
}


/* ============================================================
   RATING
============================================================ */

async function renderRating() {

  document.querySelector("#content").innerHTML = `
    <div class="empty">
      Загружаем рейтинг...
    </div>
  `;

  try {

    const rows =
      await api("/api/rating");

    if (!rows.length) {

      document.querySelector("#content").innerHTML = `
        <div class="empty">
          Рейтинг пока пуст.
        </div>
      `;

      return;
    }

    document.querySelector("#content").innerHTML = `
      <div class="grid">

        ${rows.map((player, index) => `

          <button
            class="card rank rank-button"
            onclick="openPlayerProfile(${player.user_id})"
          >

            <div class="rank-num">
              #${index + 1}
            </div>

            <div>

              <h3>
                ${player.corp_name}
              </h3>

              <p>
                💰 ${fmt(player.money)}
              </p>

            </div>

          </button>

        `).join("")}

      </div>
    `;

  } catch (error) {

    modal(
      "Ошибка",
      error.message
    );
  }
}


/* ============================================================
   PLAYER PROFILE
============================================================ */

async function openPlayerProfile(playerId) {

  document.querySelector("#content").innerHTML = `
    <div class="empty">
      Загружаем профиль...
    </div>
  `;

  try {

    const profile =
      await api(`/api/player/${playerId}`);

    const businesses =
      profile.businesses?.length

        ? profile.businesses
            .map(business => `

              <article class="profile-business">

                <div>

                  <h3>
                    ${business.name}
                  </h3>

                  <p>
                    ${business.description}
                  </p>

                </div>

                <b>
                  ур. ${business.level}
                </b>

              </article>

            `)
            .join("")

        : `
          <div class="empty">
            Бизнесов пока нет.
          </div>
        `;

    document.querySelector("#content").innerHTML = `

      <section class="profile-page">

        <button
          class="back-button"
          onclick="backToRating()"
        >
          ← Назад к рейтингу
        </button>

        <article class="profile-header">

          <div class="eyebrow">
            ПРОФИЛЬ ИГРОКА
          </div>

          <h2>
            ${profile.player.corp_name}
          </h2>

          <p>
            💰 Капитал:
            ${fmt(profile.player.money)}
          </p>

          <p>
            📈 Доход:
            ${fmt(profile.hourly_income)}/ч
          </p>

        </article>

        <section class="profile-stats">

          <div>

            <span>
              💰 Общая прибыль
            </span>

            <b>
              ${fmt(profile.stats.total_earned)}
            </b>

          </div>

          <div>

            <span>
              💸 Общие расходы
            </span>

            <b>
              ${fmt(profile.stats.total_spent)}
            </b>

          </div>

        </section>

        <section class="profile-businesses">

          <h2>
            🏢 Бизнесы
          </h2>

          ${businesses}

        </section>

      </section>
    `;

  } catch (error) {

    modal(
      "Ошибка",
      error.message
    );
  }
}


function backToRating() {

  page = "rating";

  updateActiveTab();

  renderRating();
}


/* ============================================================
   INVESTMENTS
============================================================ */

async function loadStocks() {

  stocksCache =
    await api("/api/stocks");

  return stocksCache;
}


async function loadBrokerage() {

  brokerageCache =
    await api("/api/brokerage-account");

  return brokerageCache;
}


function getHolding(stockId) {

  if (!brokerageCache) {
    return null;
  }

  return (
    brokerageCache.holdings || []
  ).find(
    holding =>
      String(holding.stock_id)
      === String(stockId)
  ) || null;
}


function stockChange(stock) {

  if (
    stock.change_percent !== undefined &&
    stock.change_percent !== null
  ) {
    return Number(
      stock.change_percent
    );
  }

  if (
    stock.price_change_percent !== undefined &&
    stock.price_change_percent !== null
  ) {
    return Number(
      stock.price_change_percent
    );
  }

  return 0;
}


function renderStockMiniChart(history) {

  if (!history || !history.length) {
    return `
      <div class="stock-chart-empty">
        История цены пока формируется
      </div>
    `;
  }

  const prices = history.map(item => Number(item.price || 0));
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const width = 360;
  const height = 120;
  const labelWidth = 78;
  const plotWidth = width - labelWidth - 8;
  const topPad = 8;
  const bottomPad = 8;
  const plotHeight = height - topPad - bottomPad;

  const yFor = price =>
    topPad + plotHeight - ((price - min) / range * plotHeight);

  const points = prices.map((price, index) => {
    const x = prices.length === 1
      ? plotWidth / 2
      : index / (prices.length - 1) * plotWidth;
    return `${x},${yFor(price)}`;
  }).join(" ");

  const currentPrice = prices[prices.length - 1];
  const currentY = yFor(currentPrice);
  const labelY = Math.min(height - 25, Math.max(3, currentY - 12));

  return `
    <div class="stock-chart">
      <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
        <line
          x1="0" y1="${currentY}"
          x2="${plotWidth}" y2="${currentY}"
          class="stock-current-line"
        />
        <polyline
          points="${points}"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle
          cx="${plotWidth}" cy="${currentY}" r="4"
          class="stock-current-dot"
        />
        <rect
          x="${plotWidth + 5}" y="${labelY}"
          width="${labelWidth}" height="24" rx="4"
          class="stock-current-label-bg"
        />
        <text
          x="${plotWidth + 11}" y="${labelY + 16}"
          class="stock-current-label"
        >${fmtNumber(currentPrice)} ₽</text>
      </svg>
    </div>
  `;
}


/* ============================================================
   INVESTMENT PAGE
============================================================ */

async function renderInvestments() {

  const content =
    document.querySelector("#content");

  content.innerHTML = `
    <div class="empty">
      Загружаем фондовый рынок...
    </div>
  `;

  try {

    const [
      stocks,
      brokerage
    ] = await Promise.all([
      loadStocks(),
      loadBrokerage()
    ]);

    stocksCache = stocks || [];
    brokerageCache = brokerage || {};

    const holdings =
      brokerageCache.holdings || [];

    const totalProfit =
      Number(
        brokerageCache.total_profit || 0
      );

    const totalProfitPercent =
      Number(
        brokerageCache.total_profit_percent || 0
      );

    content.innerHTML = `

      <section class="investment-page">

        <article class="investment-summary">

          <div class="eyebrow">
            МОЙ БРОКЕРСКИЙ СЧЁТ
          </div>

          <h2>
            ${fmt(
              brokerageCache.total_current_value || 0
            )}
          </h2>

          <div class="
            investment-profit
            ${totalProfit >= 0
              ? "positive"
              : "negative"}
          ">

            ${totalProfit >= 0 ? "▲" : "▼"}

            ${fmt(Math.abs(totalProfit))}

            (${fmtPercent(
              totalProfitPercent
            )})

          </div>

          <div class="investment-summary-grid">

            <div>

              <span>
                Вложено
              </span>

              <b>
                ${fmt(
                  brokerageCache.total_invested || 0
                )}
              </b>

            </div>

            <div>

              <span>
                Позиций
              </span>

              <b>
                ${holdings.length}
              </b>

            </div>

          </div>

        </article>


        <div class="investment-section-title">

          <div>

            <div class="eyebrow">
              ФОНДОВЫЙ РЫНОК
            </div>

            <h2>
              📈 Акции
            </h2>

          </div>

          <button
            class="refresh-market"
            onclick="refreshInvestments()"
          >
            ↻
          </button>

        </div>


        <div class="grid">

          ${
            stocksCache.length
              ? stocksCache
                  .map(stock =>
                    renderStockCard(stock)
                  )
                  .join("")
              : `
                <div class="empty">
                  На рынке пока нет акций.
                </div>
              `
          }

        </div>


        <article class="card bond-placeholder">

          <div class="business-head">

            <div>

              <h3>
                🏦 Облигации
              </h3>

              <p>
                Инструмент с фиксированной
                доходностью появится в одном
                из следующих обновлений.
              </p>

            </div>

            <b>
              СКОРО
            </b>

          </div>

        </article>


        ${renderHoldings()}

      </section>
    `;

  } catch (error) {

    modal(
      "Инвестиции",
      error.message
    );
  }
}


/* ============================================================
   STOCK CARD
============================================================ */

function renderStockCard(stock) {

  const holding =
    getHolding(stock.id);

  const price =
    Number(stock.current_price || 0);

  const change =
    stockChange(stock);

  const owned =
    Number(
      holding?.quantity || 0
    );

  return `

    <article class="
      card
      stock-card
    ">

      <div class="stock-header">

        <div>

          <div class="stock-symbol">
            ${stock.symbol}
          </div>

          <h3>
            ${stock.name}
          </h3>

        </div>

        <div class="stock-price-block">

          <b class="stock-price">
            ${fmt(price)}
          </b>

          <span class="
            stock-change
            ${change >= 0
              ? "positive"
              : "negative"}
          ">

            ${change >= 0
              ? "▲"
              : "▼"}

            ${Math.abs(change).toFixed(2)}%

          </span>

        </div>

      </div>


      <p class="stock-description">
        ${stock.description || ""}
      </p>


      ${
        stock.history?.length
          ? renderStockMiniChart(
              stock.history
            )
          : `
            <button
              class="stock-history-button"
              onclick="openStock('${stock.id}')"
            >
              📊 Открыть график
            </button>
          `
      }


      <div class="stock-position">

        <span>
          У тебя:
        </span>

        <b>
          ${owned} шт.
        </b>

      </div>


      <div class="stock-actions">

        <button
          class="buy stock-buy"
          onclick="openTrade('${stock.id}', 'buy')"
        >
          Купить
        </button>

        <button
          class="stock-sell"
          ${owned > 0 ? "" : "disabled"}
          onclick="openTrade('${stock.id}', 'sell')"
        >
          Продать
        </button>

      </div>

    </article>
  `;
}


/* ============================================================
   HOLDINGS
============================================================ */

function renderHoldings() {

  if (
    !brokerageCache ||
    !brokerageCache.holdings ||
    !brokerageCache.holdings.length
  ) {

    return `
      <article class="card empty">
        У тебя пока нет акций.
        Выбери компанию выше,
        чтобы начать инвестировать.
      </article>
    `;
  }

  return `

    <section class="holdings-section">

      <div class="investment-section-title">

        <div>

          <div class="eyebrow">
            ТВОИ АКТИВЫ
          </div>

          <h2>
            💼 Портфель
          </h2>

        </div>

      </div>


      <div class="grid">

        ${brokerageCache.holdings
          .map(holding =>
            renderHoldingCard(holding)
          )
          .join("")}

      </div>

    </section>
  `;
}


function renderHoldingCard(holding) {

  const profit =
    Number(
      holding.profit || 0
    );

  const profitPercent =
    Number(
      holding.profit_percent || 0
    );

  return `

    <article class="
      card
      holding-card
    ">

      <div class="business-head">

        <div>

          <div class="stock-symbol">
            ${holding.symbol}
          </div>

          <h3>
            ${holding.name}
          </h3>

        </div>

        <b>
          ${holding.quantity} шт.
        </b>

      </div>


      <div class="holding-row">

        <span>
          Средняя цена
        </span>

        <b>
          ${fmt(
            holding.avg_buy_price
          )}
        </b>

      </div>


      <div class="holding-row">

        <span>
          Текущая цена
        </span>

        <b>
          ${fmt(
            holding.current_price
          )}
        </b>

      </div>


      <div class="holding-row">

        <span>
          Стоимость
        </span>

        <b>
          ${fmt(
            holding.current_value
          )}
        </b>

      </div>


      <div class="
        holding-profit
        ${profit >= 0
          ? "positive"
          : "negative"}
      ">

        ${profit >= 0
          ? "▲ Прибыль"
          : "▼ Убыток"}

        ${fmt(Math.abs(profit))}

        (${fmtPercent(
          profitPercent
        )})

      </div>

    </article>
  `;
}


/* ============================================================
   STOCK DETAILS
============================================================ */

async function openStock(stockId) {

  try {

    const stock =
      await api(
        `/api/stocks/${stockId}`
      );

    const holding =
      getHolding(stock.id);

    const history =
      stock.history || [];

    const chart =
      renderStockMiniChart(history);

    const price =
      Number(
        stock.current_price || 0
      );

    const change =
      stockChange(stock);

    document.querySelector("#modalTitle").textContent =
      `${stock.symbol} — ${stock.name}`;

    document.querySelector("#modalText").innerHTML = `
      <div>

        <div style="
          font-size: 24px;
          font-weight: 900;
          margin-bottom: 8px;
        ">
          ${fmt(price)}
        </div>

        <div class="
          ${change >= 0
            ? "positive"
            : "negative"}
        ">
          ${change >= 0 ? "▲" : "▼"}
          ${Math.abs(change).toFixed(2)}%
        </div>

        <div style="margin-top: 12px;">
          ${chart}
        </div>

        <p>
          У тебя:
          ${holding?.quantity || 0} шт.
        </p>

        <p>
          ${stock.description || ""}
        </p>

      </div>
    `;

    document.querySelector("#modal")
      .classList
      .remove("hidden");

  } catch (error) {

    modal(
      "Ошибка",
      error.message
    );
  }
}


/* ============================================================
   REFRESH INVESTMENTS
============================================================ */

async function refreshInvestments() {

  await renderInvestments();
}


/* ============================================================
   TRADING
============================================================ */

async function openTrade(stockId, side) {

  const stock =
    stocksCache.find(
      item =>
        String(item.id)
        === String(stockId)
    );

  if (!stock) {

    modal(
      "Ошибка",
      "Акция не найдена."
    );

    return;
  }

  const holding =
    getHolding(stockId);

  const owned =
    Number(
      holding?.quantity || 0
    );

  const price =
    Number(
      stock.current_price || 0
    );

  if (price <= 0) {

    modal(
      "Ошибка",
      "Цена акции недоступна."
    );

    return;
  }

  const maxBuy =
    Math.floor(
      Number(state.player.money || 0)
      / price
    );

  const maxSell =
    owned;

  const max =
    side === "buy"
      ? maxBuy
      : maxSell;

  if (max <= 0) {

    modal(
      side === "buy"
        ? "Недостаточно денег"
        : "Нет акций",

      side === "buy"
        ? "У тебя недостаточно денег для покупки этой акции."
        : "У тебя нет этой акции."
    );

    return;
  }

  const quantity =
    prompt(
      `${
        side === "buy"
          ? "Покупка"
          : "Продажа"
      } ${stock.name}

Цена: ${fmt(price)}

Максимум: ${max} шт.

Введите количество:`,

      "1"
    );

  if (quantity === null) {
    return;
  }

  const qty =
    Number.parseInt(
      quantity,
      10
    );

  if (
    !Number.isInteger(qty) ||
    qty <= 0
  ) {

    modal(
      "Ошибка",
      "Количество должно быть целым числом больше нуля."
    );

    return;
  }

  if (qty > max) {

    modal(
      "Ошибка",
      `Максимально доступно: ${max} шт.`
    );

    return;
  }

  try {

    const result =
      await api(
        `/api/stocks/${stockId}/${side}`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json"
          },

          body: JSON.stringify({
            quantity: qty
          })
        }
      );

    if (result.state) {

      state =
        result.state;

    } else {

      state =
        await api("/api/state");
    }

    brokerageCache =
      await loadBrokerage();

    stocksCache =
      await loadStocks();

    renderHeader();

    await renderInvestments();

    const total =
      price * qty;

    modal(
      side === "buy"
        ? "Акции куплены"
        : "Акции проданы",

      side === "buy"

        ? `Куплено ${qty} шт. ${stock.symbol}

Сумма сделки: ${fmt(total)}`

        : `Продано ${qty} шт. ${stock.symbol}

Сумма сделки: ${fmt(total)}`
    );

    tg
      ?.HapticFeedback
      ?.notificationOccurred(
        "success"
      );

  } catch (error) {

    modal(
      "Сделка не выполнена",
      error.message
    );

    tg
      ?.HapticFeedback
      ?.notificationOccurred(
        "error"
      );
  }
}


/* ============================================================
   TAXES
============================================================ */

function formatTaxTime(seconds) {
  const total = Math.max(0, Number(seconds || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return `${hours} ч ${minutes} мин`;
}

function renderTaxes() {
  const taxes = state?.taxes || {};
  const unpaid = Number(taxes.unpaid || 0);
  const blocked = Boolean(taxes.blocked);

  document.querySelector("#content").innerHTML = `
    <section class="tax-page">
      <article class="tax-hero ${blocked ? "tax-blocked" : ""}">
        <div class="eyebrow">НАЛОГОВАЯ СИСТЕМА</div>
        <h2>${blocked ? "⛔ Доход остановлен" : "🧾 Налоги"}</h2>
        <p>Налог составляет <b>${taxes.rate_percent || 5}%</b> от полученного дохода.</p>
      </article>

      <article class="stats-card">
        <span>Неоплаченный налог</span>
        <b>${fmt(unpaid)}</b>
      </article>

      <article class="card tax-info">
        ${unpaid > 0
          ? blocked
            ? `Срок оплаты истёк. Генерация прибыли остановлена до полной оплаты налога.`
            : `До остановки прибыли осталось: <b>${formatTaxTime(taxes.seconds_left)}</b>.`
          : `Задолженности нет. После получения дохода начисляется налог 5%, который нужно оплатить в течение 12 часов.`
        }
      </article>

      <button
        class="buy"
        ${unpaid > 0 ? "" : "disabled"}
        onclick="payTaxes()"
      >
        ${unpaid > 0 ? `Оплатить ${fmt(unpaid)}` : "Налогов к оплате нет"}
      </button>
    </section>
  `;
}

async function payTaxes() {
  try {
    const result = await api("/api/taxes/pay", { method: "POST" });
    state = result.state;
    renderHeader();
    renderTaxes();
    modal("Налог оплачен", `Оплачено ${fmt(result.paid)}. Прибыль снова начисляется.`);
    tg?.HapticFeedback?.notificationOccurred("success");
  } catch (error) {
    modal("Не удалось оплатить", error.message);
    tg?.HapticFeedback?.notificationOccurred("error");
  }
}


/* ============================================================
   MAIN RENDER
============================================================ */

function render() {

  renderHeader();

  if (page === "businesses") {
    renderBusinesses();
    return;
  }

  if (page === "techs") {
    renderTechs();
    return;
  }

  if (page === "investments") {
    renderInvestments();
    return;
  }

  if (page === "taxes") {
    renderTaxes();
    return;
  }

  if (page === "statistics") {
    renderStatistics();
    return;
  }

  if (page === "rating") {
    renderRating();
    return;
  }
}


/* ============================================================
   TABS
============================================================ */

function updateActiveTab() {

  document
    .querySelectorAll(".tab")
    .forEach(tab => {

      tab.classList.toggle(
        "active",
        tab.dataset.page === page
      );

    });
}


document
  .querySelectorAll(".tab")
  .forEach(button => {

    button.onclick = () => {

      page =
        button.dataset.page;

      updateActiveTab();

      render();

    };

  });


/* ============================================================
   BUSINESS ACTIONS
============================================================ */

window.buyBusiness =
  async function(id) {

    try {

      state =
        await api(
          `/api/business/${id}/buy`,
          {
            method: "POST"
          }
        );

      render();

    } catch (error) {

      modal(
        "Не удалось",
        error.message
      );
    }
  };


window.sellBusiness =
  async function(id) {
    const business = (state.businesses || []).find(item => item.id === id);

    if (!business || Number(business.level || 0) <= 0) {
      return;
    }

    const confirmed = confirm(
      `Продать ${business.name}?\n\nКапитализация: ${fmt(business.capitalization)}\nТы получишь 30%: ${fmt(business.sell_price)}\n\nОтменить продажу будет нельзя.`
    );

    if (!confirmed) {
      return;
    }

    try {
      const result = await api(`/api/business/${id}/sell`, { method: "POST" });
      state = result.state;
      render();
      modal("Бизнес продан", `Ты получил ${fmt(result.sell_price)}.`);
      tg?.HapticFeedback?.notificationOccurred("success");
    } catch (error) {
      modal("Продажа не выполнена", error.message);
      tg?.HapticFeedback?.notificationOccurred("error");
    }
  };


window.buyTech =
  async function(id) {

    try {

      state =
        await api(
          `/api/tech/${id}/buy`,
          {
            method: "POST"
          }
        );

      render();

    } catch (error) {

      modal(
        "Не удалось",
        error.message
      );
    }
  };


/* ============================================================
   COLLECT INCOME
============================================================ */

document
  .querySelector("#collectBtn")
  .onclick = async () => {

    try {

      const result =
        await api(
          "/api/collect",
          {
            method: "POST"
          }
        );

      state =
        result.state;

      render();

      modal(
        "Доход получен",
        `Ты получил ${fmt(result.earned)}.\nНачислен налог 5%: ${fmt(result.tax_accrued)}.\nОплатить его нужно в течение 12 часов.`
      );

      tg
        ?.HapticFeedback
        ?.notificationOccurred(
          "success"
        );

    } catch (error) {

      modal(
        "Доход",
        error.message
      );

      tg
        ?.HapticFeedback
        ?.notificationOccurred(
          "error"
        );
    }
  };


/* ============================================================
   RENAME
============================================================ */

document
  .querySelector("#renameBtn")
  .onclick = async () => {

    if (!state?.player) {
      return;
    }

    const name =
      prompt(
        "Новое название корпорации:",
        state.player.corp_name
      );

    if (!name) {
      return;
    }

    try {

      state =
        await api(
          "/api/rename",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify({
                name
              })
          }
        );

      render();

    } catch (error) {

      modal(
        "Ошибка",
        error.message
      );
    }
  };


/* ============================================================
   GLOBAL FUNCTIONS
============================================================ */

window.openPlayerProfile =
  openPlayerProfile;

window.backToRating =
  backToRating;

window.openStock =
  openStock;

window.openTrade =
  openTrade;

window.refreshInvestments =
  refreshInvestments;

window.payTaxes =
  payTaxes;


/* ============================================================
   START / REFRESH
============================================================ */

async function refresh() {

  try {

    state =
      await api("/api/state");

    updateActiveTab();

    render();

  } catch (error) {

    console.error(
      "Ошибка запуска:",
      error
    );

    modal(
      "Ошибка запуска",
      error.message
    );
  }
}


/* ============================================================
   START GAME
============================================================ */

refresh();