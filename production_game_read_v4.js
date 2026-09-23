import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || '').replace(/\/+$/, '');
const TOKEN = __ENV.LOAD_TEST_TOKEN || '';

if (!BASE_URL) throw new Error('BASE_URL is required');
if (!TOKEN) throw new Error('LOAD_TEST_TOKEN is required');

export const options = {
  scenarios: {
    game_read_breakpoint: {
      executor: 'ramping-vus',
      startVUs: 0,
      gracefulRampDown: '15s',
      stages: [
        { duration: '15s', target: 10 },
        { duration: '20s', target: 25 },
        { duration: '20s', target: 50 },
        { duration: '25s', target: 100 },
        { duration: '25s', target: 200 },
        { duration: '25s', target: 300 },
        { duration: '30s', target: 500 },
        { duration: '30s', target: 750 },
        { duration: '30s', target: 1000 },
        { duration: '30s', target: 1000 },
      ],
    },
  },
  thresholds: {
    'http_req_failed{endpoint:game_read}': [{
      threshold: 'rate<0.03',
      abortOnFail: true,
      delayAbortEval: '25s',
    }],
    'http_req_duration{endpoint:game_read}': [{
      threshold: 'p(95)<2500',
      abortOnFail: true,
      delayAbortEval: '25s',
    }],
  },
};

const headers = {
  'X-Load-Test-Token': TOKEN,
  'User-Agent': 'Corporation-authorized-production-load-test-v4',
};

function get(path, endpoint, timeout = '10s') {
  return http.get(`${BASE_URL}${path}`, {
    headers,
    tags: { endpoint },
    timeout,
  });
}

export default function () {
  if (__ITER === 0) {
    const root = get('/', 'root');
    check(root, { 'root OK': (r) => r.status === 200 });

    const js = get('/static/app.js', 'app_js');
    check(js, { 'app.js OK': (r) => r.status === 200 || r.status === 304 });

    const css = get('/static/style.css', 'style_css');
    check(css, { 'style.css OK': (r) => r.status === 200 || r.status === 304 });
  }

  const seed = (__VU * 1000000) + __ITER;
  const r = get(`/__loadtest/read?seed=${seed}`, 'game_read', '10s');

  check(r, {
    'game read 200': (res) => res.status === 200,
    'game read payload OK': (res) => {
      try {
        const body = res.json();
        return body && body.ok === true && body.queries >= 1;
      } catch (_) {
        return false;
      }
    },
  });

  sleep(1.0 + Math.random());
}
