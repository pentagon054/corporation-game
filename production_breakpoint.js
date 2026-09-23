import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || '').replace(/\/+$/, '');
if (!BASE_URL) throw new Error('BASE_URL is required');

export const options = {
  scenarios: {
    production_breakpoint: {
      executor: 'ramping-vus',
      startVUs: 0,
      gracefulRampDown: '10s',
      stages: [
        { duration: '15s', target: 5 },
        { duration: '20s', target: 10 },
        { duration: '20s', target: 25 },
        { duration: '20s', target: 50 },
        { duration: '20s', target: 75 },
        { duration: '20s', target: 100 },
        { duration: '20s', target: 150 },
        { duration: '20s', target: 200 },
        { duration: '20s', target: 300 },
      ],
    },
  },
  thresholds: {
    http_req_failed: [{
      threshold: 'rate<0.03',
      abortOnFail: true,
      delayAbortEval: '15s',
    }],
    http_req_duration: [{
      threshold: 'p(95)<2500',
      abortOnFail: true,
      delayAbortEval: '15s',
    }],
  },
};

function req(path, tag) {
  const r = http.get(`${BASE_URL}${path}`, {
    tags: { endpoint: tag },
    timeout: '5s',
  });
  check(r, {
    [`${tag} status 200`]: (res) => res.status === 200,
  });
  return r;
}

export default function () {
  // Only public/read-only web assets. No player creation, no purchases,
  // no writes to SQLite, no bot API calls.
  req('/', 'root');

  // These are the main assets used by the Telegram Mini App.
  // 304 is also acceptable if the platform/cache returns it.
  const js = http.get(`${BASE_URL}/static/app.js`, {
    tags: { endpoint: 'app.js' },
    timeout: '5s',
  });
  check(js, {
    'app.js OK': (r) => r.status === 200 || r.status === 304,
  });

  const css = http.get(`${BASE_URL}/static/style.css`, {
    tags: { endpoint: 'style.css' },
    timeout: '5s',
  });
  check(css, {
    'style.css OK': (r) => r.status === 200 || r.status === 304,
  });

  sleep(0.6 + Math.random() * 1.2);
}
