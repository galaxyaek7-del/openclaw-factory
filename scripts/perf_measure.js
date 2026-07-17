// Standalone performance/load measurement tool (Phase 10B — Production
// Hardening). Not wired into the live app — a deliberately-run tool,
// same convention as every other script/ file in this factory. Uses
// only native fetch (no new dependency).
//
//   node scripts/perf_measure.js <base_url> <password> latency
//   node scripts/perf_measure.js <base_url> <password> load <concurrency>

const [, , baseUrl, password, mode, concurrencyArg] = process.argv;

const ENDPOINTS = [
  '/api/v1/company-health',
  '/api/v1/market-intelligence',
  '/api/v1/opportunity-queue',
  '/api/v1/decision-history',
  '/api/v1/production-queue',
  '/api/v1/automation-status',
  '/api/v1/alerts',
  '/api/v1/system-configuration',
];

async function login() {
  const res = await fetch(`${baseUrl}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  const setCookie = res.headers.get('set-cookie');
  if (!setCookie) throw new Error('login failed, no cookie returned');
  return setCookie.split(';')[0];
}

function percentile(sorted, p) {
  const idx = Math.min(sorted.length - 1, Math.floor(p / 100 * sorted.length));
  return sorted[idx];
}

async function timedGet(url, cookie) {
  const started = process.hrtime.bigint();
  let status = null, ok = false;
  try {
    const res = await fetch(url, { headers: { Cookie: cookie } });
    status = res.status;
    ok = res.ok;
    await res.text();
  } catch (err) {
    status = 'error:' + err.message;
  }
  const durationMs = Number(process.hrtime.bigint() - started) / 1e6;
  return { durationMs, status, ok };
}

async function runLatency(cookie) {
  console.log('=== per-endpoint latency (5 sequential requests each) ===');
  for (const ep of ENDPOINTS) {
    const durations = [];
    for (let i = 0; i < 5; i++) {
      const r = await timedGet(`${baseUrl}${ep}`, cookie);
      durations.push(r.durationMs);
    }
    durations.sort((a, b) => a - b);
    const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
    console.log(`${ep}: avg=${avg.toFixed(1)}ms min=${durations[0].toFixed(1)}ms max=${durations[durations.length - 1].toFixed(1)}ms`);
  }
}

async function runLoad(cookie, concurrency) {
  console.log(`=== concurrent load test: ${concurrency} concurrent requests, mixed real endpoints ===`);
  const started = Date.now();
  const requests = [];
  for (let i = 0; i < concurrency; i++) {
    const ep = ENDPOINTS[i % ENDPOINTS.length];
    requests.push(timedGet(`${baseUrl}${ep}`, cookie));
  }
  const results = await Promise.all(requests);
  const wallMs = Date.now() - started;
  const durations = results.map(r => r.durationMs).sort((a, b) => a - b);
  const errors = results.filter(r => !r.ok);
  const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
  console.log(`wall time: ${wallMs}ms`);
  console.log(`requests: ${results.length}, errors: ${errors.length}`);
  console.log(`latency: avg=${avg.toFixed(1)}ms p50=${percentile(durations, 50).toFixed(1)}ms p95=${percentile(durations, 95).toFixed(1)}ms p99=${percentile(durations, 99).toFixed(1)}ms max=${durations[durations.length - 1].toFixed(1)}ms`);
  if (errors.length) {
    console.log('error statuses:', errors.map(e => e.status));
  }
}

(async () => {
  const cookie = await login();
  if (mode === 'latency') {
    await runLatency(cookie);
  } else if (mode === 'load') {
    await runLoad(cookie, parseInt(concurrencyArg, 10) || 10);
  } else {
    console.log('usage: node scripts/perf_measure.js <base_url> <password> latency|load <concurrency>');
    process.exit(1);
  }
})();
