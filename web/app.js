const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
  tg.expand();
}

const DEV_ID = 999001;

let state = null;
let page = "businesses";


function fmt(n) {
  return Number(n || 0).toLocaleString("ru-RU") + " ₽";
}


async function api(
  url,
  options = {}
) {

  const headers = {
    ...(options.headers || {})
  };

  if (tg?.initData) {

    headers[
      "X-Telegram-Init-Data"
    ] = tg.initData;

  } else {

    headers[
      "X-User-Id"
    ] = String(DEV_ID);

  }


  const res = await fetch(
    url,
    {
      ...options,
      headers
    }
  );


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


function modal(
  title,
  text
) {

  document
    .querySelector("#modalTitle")
    .textContent = title;


  document
    .querySelector("#modalText")
    .textContent = text;


  document
    .querySelector("#modal")
    .classList
    .remove("hidden");

}


document
  .querySelector("#modalClose")
  .onclick = () => {

    document
      .querySelector("#modal")
      .classList
      .add("hidden");

  };



function businessCount() {

  return state.businesses.reduce(

    (total, business) =>

      total + business.level,

    0

  );

}



function renderHeader() {

  const player = state.player;


  document
    .querySelector("#corpName")
    .textContent = player.corp_name;


  document
    .querySelector("#money")
    .textContent = fmt(player.money);


  document
    .querySelector("#income")
    .textContent =

      fmt(state.hourly_income)
      + "/ч";


  document
    .querySelector("#businessCount")
    .textContent =

      businessCount();

}



function renderBusinesses() {

  const html =

    state.businesses
      .map(business => {


        const canBuy =

          state.player.money
          >= business.next_cost;


        return `

          <article class="card">

            <div class="business-head">

              <div>

                <h3>
                  ${business.name}
                </h3>

                <p>
                  ${business.desc}
                </p>

              </div>


              <b>
                ур. ${business.level}
              </b>

            </div>


            <div class="meta">

              <span>

                📈 +${fmt(
                  business.base_income
                  * business.level
                )}/ч

              </span>


              <span>

                ${business.level
                  ? "📈 Улучшается"
                  : "🆕 Новый бизнес"}

              </span>

            </div>


            <button

              class="buy"

              ${canBuy
                ? ""
                : "disabled"}

              onclick="
                buyBusiness(
                  '${business.id}'
                )
              "

            >

              ${business.level
                ? "Улучшить"
                : "Открыть"}

              за

              ${fmt(
                business.next_cost
              )}

            </button>

          </article>

        `;

      })
      .join("");


  document
    .querySelector("#content")
    .innerHTML =

      `<div class="grid">

        ${html}

      </div>`;

}



function renderTechs() {

  const html =

    state.techs
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


            ${tech.owned
              ? "✅"
              : ""}

          </div>


          <button

            class="buy"

            ${tech.owned
              || state.player.money < tech.cost

              ? "disabled"

              : ""}

            onclick="
              buyTech(
                '${tech.id}'
              )
            "

          >

            ${tech.owned

              ? "Исследовано"

              : "Исследовать за "
                + fmt(tech.cost)

            }

          </button>

        </article>

      `)
      .join("");


  document
    .querySelector("#content")
    .innerHTML =

      `<div class="grid">

        ${html}

      </div>`;

}



function renderProfitChart(
  data
) {

  if (!data.length) {

    return `

      <div class="empty">

        Пока нет собранной прибыли.

      </div>

    `;

  }


  const max = Math.max(

    ...data.map(
      item => item.earned
    ),

    1

  );


  return `

    <div class="profit-chart">

      ${data.map(item => {

        const height = Math.max(

          6,

          Math.round(
            item.earned
            / max
            * 100
          )

        );


        const date =

          item.day
            .split("-")
            .slice(1)
            .join(".");


        return `

          <div
            class="chart-column"
          >

            <div
              class="chart-value"
            >

              ${fmt(item.earned)}

            </div>


            <div
              class="chart-bar"
              style="
                height:${height}%;
              "
            >
            </div>


            <div
              class="chart-date"
            >

              ${date}

            </div>

          </div>

        `;

      }).join("")}

    </div>

  `;

}



async function renderStatistics() {

  document
    .querySelector("#content")
    .innerHTML =

      `<div class="empty">

        Загружаем статистику...

      </div>`;


  try {

    const stats = await api(
      "/api/statistics"
    );


    document
      .querySelector("#content")
      .innerHTML = `

        <section class="stats-page">


          <article class="stats-card">

            <span>
              💰 Общая прибыль
            </span>

            <b>
              ${fmt(
                stats.total_earned
              )}
            </b>

          </article>


          <article class="stats-card">

            <span>
              💸 Общие расходы
            </span>

            <b>
              ${fmt(
                stats.total_spent
              )}
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
              stats.daily_profit
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



async function renderRating() {

  document
    .querySelector("#content")
    .innerHTML =

      `<div class="empty">

        Загружаем рейтинг...

      </div>`;


  try {

    const rows = await api(
      "/api/rating"
    );


    document
      .querySelector("#content")
      .innerHTML =

        `<div class="grid">

          ${rows.map(
            (player, index) => `

              <button

                class="card rank rank-button"

                onclick="
                  openPlayerProfile(
                    ${player.user_id}
                  )
                "

              >

                <div
                  class="rank-num"
                >

                  #${index + 1}

                </div>


                <div>

                  <h3>
                    ${player.corp_name}
                  </h3>


                  <p>

                    💰 ${fmt(
                      player.money
                    )}

                  </p>

                </div>

              </button>

            `
          ).join("")}

        </div>`;

  } catch (error) {

    modal(
      "Ошибка",
      error.message
    );

  }

}



async function openPlayerProfile(
  playerId
) {

  document
    .querySelector("#content")
    .innerHTML =

      `<div class="empty">

        Загружаем профиль...

      </div>`;


  try {

    const profile = await api(

      `/api/player/${playerId}`

    );


    const businesses =

      profile.businesses.length

        ? profile.businesses
            .map(business => `

              <article
                class="profile-business"
              >

                <div>

                  <h3>
                    ${business.name}
                  </h3>

                  <p>
                    ${business.description}
                  </p>

                </div>


                <b>

                  ур.
                  ${business.level}

                </b>

              </article>

            `)
            .join("")

        : `

          <div class="empty">

            Бизнесов пока нет.

          </div>

        `;


    document
      .querySelector("#content")
      .innerHTML = `

        <section class="profile-page">


          <button

            class="back-button"

            onclick="
              backToRating()
            "

          >

            ← Назад к рейтингу

          </button>


          <article
            class="profile-header"
          >

            <div class="eyebrow">

              ПРОФИЛЬ ИГРОКА

            </div>


            <h2>

              ${profile.player.corp_name}

            </h2>


            <p>

              💰 Капитал:
              ${fmt(
                profile.player.money
              )}

            </p>


            <p>

              📈 Доход:
              ${fmt(
                profile.hourly_income
              )}/ч

            </p>

          </article>


          <section
            class="profile-stats"
          >

            <div>

              <span>
                💰 Общая прибыль
              </span>

              <b>

                ${fmt(
                  profile.stats.total_earned
                )}

              </b>

            </div>


            <div>

              <span>
                💸 Общие расходы
              </span>

              <b>

                ${fmt(
                  profile.stats.total_spent
                )}

              </b>

            </div>

          </section>


          <section
            class="profile-businesses"
          >

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

  renderRating();

}



function render() {

  renderHeader();


  if (

    page === "businesses"

  ) {

    renderBusinesses();

  }


  if (

    page === "techs"

  ) {

    renderTechs();

  }


  if (

    page === "statistics"

  ) {

    renderStatistics();

  }


  if (

    page === "rating"

  ) {

    renderRating();

  }

}



async function refresh() {

  state = await api(
    "/api/state"
  );

  render();

}



window.buyBusiness = async function(
  id
) {

  try {

    state = await api(

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



window.buyTech = async function(
  id
) {

  try {

    state = await api(

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



document
  .querySelector("#collectBtn")
  .onclick = async () => {

    try {

      const result = await api(

        "/api/collect",

        {
          method: "POST"
        }

      );


      state = result.state;


      render();


      modal(

        "Доход получен",

        `Ты получил ${fmt(
          result.earned
        )}.`

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



document
  .querySelector("#renameBtn")
  .onclick = async () => {

    const name = prompt(

      "Новое название корпорации:",

      state.player.corp_name

    );


    if (!name) {

      return;

    }


    try {

      state = await api(

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



window.openPlayerProfile =
  openPlayerProfile;


window.backToRating =
  backToRating;



document
  .querySelectorAll(".tab")
  .forEach(button =>

    button.onclick = () => {

      page =

        button.dataset.page;


      document
        .querySelectorAll(".tab")
        .forEach(tab =>

          tab.classList.toggle(

            "active",

            tab === button

          )

        );


      render();

    }

  );



refresh().catch(error =>

  modal(

    "Ошибка запуска",

    error.message

  )

);