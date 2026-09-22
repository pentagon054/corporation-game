/* Corporation v32.1: required channel gate without startup flash + safe game bootstrap. */
(function () {
  'use strict';

  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try { tg.ready(); tg.expand(); } catch (_) {}
  }

  const gate = document.getElementById('subscriptionGate32');
  const subscribeBtn = document.getElementById('subscriptionSubscribe32');
  const checkBtn = document.getElementById('subscriptionCheck32');
  const statusEl = document.getElementById('subscriptionStatus32');
  const appEl = document.querySelector('main.app');
  let channelUrl = 'https://t.me/Corpgame054';
  let checking = false;
  let gameStarted = false;

  const gameScripts = [
    '/static/gestures_v30.js?v=300',
    '/static/app.js?v=280',
    '/static/v22_1.js?v=280',
    '/static/v20.js?v=280',
    '/static/v22.js?v=280',
    '/static/v22_performance.js?v=280',
    '/static/audit_v23.js?v=280',
    '/static/interactive_map.js?v=310',
    '/static/premium_v24.js?v=310',
    '/static/premium_v25.js?v=280',
    '/static/instances_v28.js?v=280',
    '/static/v29.js?v=290',
    '/static/v31.js?v=310'
  ];

  function setStatus(text, kind) {
    if (!statusEl) return;
    statusEl.textContent = text || '';
    statusEl.dataset.kind = kind || '';
  }

  function setChecking(value) {
    checking = value;
    if (checkBtn) {
      checkBtn.disabled = value;
      checkBtn.textContent = value ? 'Проверяем…' : '✓ Проверить подписку';
    }
  }

  function showGate(message, kind) {
    document.body.classList.remove('subscription-checking32', 'subscription-ok32');
    document.body.classList.add('subscription-pending32');
    if (gate) gate.hidden = false;
    if (appEl) appEl.setAttribute('aria-hidden', 'true');
    if (message) setStatus(message, kind || 'warning');
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = false;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Не удалось загрузить ' + src));
      document.body.appendChild(script);
    });
  }

  // v28/v29 business UI can render immediately after app.js receives /api/state.
  // With dynamic script loading that response could arrive before premium_v24.js,
  // where businessIcon24 is normally declared. Provide the same icon helper before
  // app.js starts, then premium_v24.js may replace it with its own declaration.
  function installBusinessIconBootstrap() {
    if (typeof window.businessIcon24 === 'function') return;
    window.businessIcon24 = function businessIcon24(id) {
      const paths = {
        coffee: 'M5 7h12v7a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5V7ZM17 8h2a3 3 0 0 1 0 6h-2M8 3v1M12 3v1M4 22h15',
        delivery: 'M3 6h11v12H3ZM14 10h4l3 4v4h-7M6 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 20a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
        factory: 'M3 21V10l6 3V8l6 4V3h4l2 18H3ZM7 17h1M12 17h1M17 17h1',
        it: 'M3 4h18v13H3ZM8 21h8M12 17v4M9 8l-3 3 3 3M15 8l3 3-3 3',
        finance: 'M3 9l9-6 9 6H3ZM5 11v8M10 11v8M14 11v8M19 11v8M3 22h18',
        conglomerate: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM3 12h18M12 3c-6 6-6 12 0 18M12 3c6 6 6 12 0 18'
      };
      const path = paths[id] || paths.finance;
      return `<span class="business-icon24"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg></span>`;
    };
  }

  // app.js starts refresh() immediately. While extensions are being loaded, keep
  // all game API requests behind a short barrier. This restores the effective
  // ordering that the old static <script> sequence had and prevents startup races.
  function installGameBootBarrier() {
    const originalFetch = window.fetch.bind(window);
    let releaseBarrier;
    let released = false;
    const ready = new Promise(resolve => { releaseBarrier = resolve; });

    async function gatedFetch(input, init) {
      let url = '';
      try {
        url = typeof input === 'string' ? input : String(input && input.url || '');
      } catch (_) {}

      const isGameApi = url.startsWith('/api/') && !url.startsWith('/api/subscription/check');
      if (isGameApi && !released) await ready;
      return originalFetch(input, init);
    }

    window.fetch = gatedFetch;

    return function release() {
      if (released) return;
      released = true;
      releaseBarrier();
      // Calls that already captured gatedFetch can finish; new calls use native fetch.
      window.fetch = originalFetch;
    };
  }

  async function startGame() {
    if (gameStarted) return;
    gameStarted = true;
    installBusinessIconBootstrap();
    const releaseBootBarrier = installGameBootBarrier();

    try {
      for (const src of gameScripts) await loadScript(src);
      releaseBootBarrier();
      document.body.classList.remove('subscription-checking32', 'subscription-pending32');
      document.body.classList.add('subscription-ok32');
      if (gate) gate.hidden = true;
      if (appEl) appEl.removeAttribute('aria-hidden');
    } catch (error) {
      releaseBootBarrier();
      gameStarted = false;
      console.error(error);
      showGate('Ошибка загрузки игры. Закройте Mini App и откройте снова.', 'error');
    }
  }

  async function checkSubscription() {
    if (checking || gameStarted) return;

    if (!tg || !tg.initData) {
      showGate('Откройте Corporation через Telegram-бота, чтобы подтвердить аккаунт.', 'error');
      return;
    }

    setChecking(true);

    try {
      const response = await fetch('/api/subscription/check', {
        method: 'GET',
        headers: { 'X-Telegram-Init-Data': tg.initData },
        cache: 'no-store'
      });

      let data = {};
      try { data = await response.json(); } catch (_) {}

      if (!response.ok) {
        throw new Error(data.detail || 'Не удалось проверить подписку.');
      }

      if (data.channel_url) channelUrl = data.channel_url;

      if (data.subscribed === true) {
        await startGame();
        return;
      }

      showGate('Подписка пока не найдена. Подпишитесь на канал и нажмите «Проверить подписку».', 'warning');
    } catch (error) {
      showGate(error && error.message ? error.message : 'Ошибка проверки подписки.', 'error');
    } finally {
      setChecking(false);
    }
  }

  if (subscribeBtn) {
    subscribeBtn.addEventListener('click', () => {
      try {
        if (tg && typeof tg.openTelegramLink === 'function') tg.openTelegramLink(channelUrl);
        else window.location.href = channelUrl;
      } catch (_) {
        window.location.href = channelUrl;
      }
    });
  }

  if (checkBtn) checkBtn.addEventListener('click', checkSubscription);

  if (appEl) appEl.setAttribute('aria-hidden', 'true');
  if (gate) gate.hidden = true;
  checkSubscription();
})();
