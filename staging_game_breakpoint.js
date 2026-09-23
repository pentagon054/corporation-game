import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || '').replace(/\/+$/, '');
if (!BASE_URL) {
  throw new Error('BASE_URL is required');
}

const endpoints = [
  '/api/state',
  '/api/statistics',
  '/api/rating',
  '/api/stocks',
  '/api/bonds',
  '/api/real-estate',
];

export const options = {
  scenarios: {
    game_breakpoint: {
      executor: 'ramping-vus',
      startVUs: 0,
      gracefulRampDown: '10s',
      stages: [
        { duration: '20s', target: 5 },
        { duration: '30s', target: 10 },
        { duration: '30s', target: 25 },
        { duration: '30s', target: 50 },
        { duration: '30s', target: 75 },
        { duration: '30s', target: 100 },
        { duration: '30s', target: 150 },
        { duration: '30s', target: 200 },
        { duration: '30s', target: 300 },
        { duration: '30s', target: 500 },
      ],
    },
  },
  thresholds: {
    http_req_failed: [{
      threshold: 'rate<0.03',
      abortOnFail: true,
      delayAbortEval: '25s',
    }],
    http_req_duration: [{
      threshold: 'p(95)<2500',
      abortOnFail: true,
      delayAbortEval: '25s',
    }],
  },
};

function headersForVu() {
  // Works ONLY when the staging service has ALLOW_DEV_AUTH=1.
  // Each VU becomes a separate synthetic player.
  const uid = 9000000000 + __VU;
  return {
    'X-User-Id': String(uid),
    'User-Agent': 'Corporation-k6-authorized-load-test/1.0',
  };
}

export default function () {
  const headers = headersForVu();

  // State is requested every iteration because the real Mini App refreshes
  // balance/state frequently.
  const state = http.get(`${BASE_URL}/api/state`, {
    headers,
    tags: { endpoint: 'state' },
    timeout: '5s',
  });

  check(state, {
    'state 200': (r) => r.status === 200,
  });

  const path = endpoints[Math.floor(Math.random() * endpoints.length)];
  const r = http.get(`${BASE_URL}${path}`, {
    headers,
    tags: { endpoint: path },
    timeout: '5s',
  });

  check(r, {
    'game read status 200': (res) => res.status === 200,
  });

  // Human-like pause. This makes VU count closer to "simultaneously active
  // players", rather than raw request workers.
  sleep(0.8 + Math.random() * 1.4);
}
