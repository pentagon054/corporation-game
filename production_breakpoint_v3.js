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
      delayAbortEval: '20s',
    }],
    http_req_duration: [{
      threshold: 'p(95)<2500',
      abortOnFail: true,
      delayAbortEval: '20s',
    }],
  },
};

function get(path, tag) {
  const r = http.get(`${BASE_URL}${path}`, {
    tags: { endpoint: tag },
    timeout: '10s',
  });
  check(r, {
    [`${tag} OK`]: (res) => res.status === 200 || res.status === 304,
  });
  return r;
}

export default function () {
  // Simulate initial WebApp load only once per VU.
  if (__ITER === 0) {
    get('/static/app.js', 'app.js');
    get('/static/style.css', 'style.css');
  }

  // Main production-safe FastAPI load.
  // GET / only; no auth, no database writes, no player changes.
  get('/', 'root');

  sleep(0.35 + Math.random() * 0.65);
}
