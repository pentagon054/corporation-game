import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || '').replace(/\/+$/, '');
if (!BASE_URL) {
  throw new Error('BASE_URL is required');
}

export const options = {
  scenarios: {
    public_breakpoint: {
      executor: 'ramping-vus',
      startVUs: 0,
      gracefulRampDown: '5s',
      stages: [
        { duration: '15s', target: 5 },
        { duration: '25s', target: 10 },
        { duration: '25s', target: 25 },
        { duration: '25s', target: 50 },
        { duration: '25s', target: 100 },
        { duration: '25s', target: 150 },
        { duration: '25s', target: 250 },
        { duration: '25s', target: 400 },
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

export default function () {
  const r = http.get(`${BASE_URL}/`, {
    tags: { endpoint: 'root' },
    timeout: '5s',
  });

  check(r, {
    'root status 200': (res) => res.status === 200,
  });

  sleep(0.3 + Math.random() * 0.7);
}
