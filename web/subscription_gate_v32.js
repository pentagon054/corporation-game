/* Corporation v32: required Telegram channel subscription gate. */
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

  async function startGame() {
    if (gameStarted) return;
    gameStarted = true;
    setStatus('Подписка подтверждена. Запускаем Corporation…', 'success');

    try {
      for (const src of gameScripts) await loadScript(src);
      document.body.classList.remove('subscription-pending32');
      document.body.classList.add('subscription-ok32');
      if (gate) gate.hidden = true;
      if (appEl) appEl.removeAttribute('aria-hidden');
    } catch (error) {
      gameStarted = false;
      setStatus('Ошибка загрузки игры. Закройте Mini App и откройте снова.', 'error');
      console.error(error);
    }
  }

  async function checkSubscription() {
    if (checking || gameStarted) return;

    if (!tg || !tg.initData) {
      setStatus('Откройте Corporation через Telegram-бота, чтобы подтвердить аккаунт.', 'error');
      return;
    }

    setChecking(true);
    setStatus('Проверяем подписку…', 'loading');

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

      setStatus('Подписка пока не найдена. Подпишитесь на канал и нажмите «Проверить подписку».', 'warning');
    } catch (error) {
      setStatus(error && error.message ? error.message : 'Ошибка проверки подписки.', 'error');
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
  checkSubscription();
})();
