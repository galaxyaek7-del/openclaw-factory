// API contract tests (Phase 10C — Operations Automation & CI/CD).
// Unlike every other test in this repo, this one boots a real server.js
// subprocess — safe here because CI always runs against a fresh
// checkout with no already-running production instance to interfere
// with (the same reason this suite never does this against the real
// local factory: there, a second instance would collide with the one
// already running). Verifies the *shape* of the Unified Service Layer's
// contract (envelope, service registry completeness, action registry
// completeness) — not the business logic inside each service, which is
// already covered by its own tests.
//
//   node --test tests/test_api_contract.js
//
// Requires no real secrets: MISSION_CONTROL_PASSWORD is set to a
// throwaway value for the test process only; GROQ_KEY/N8N_*/GUMROAD_*
// are all optional at server startup (confirmed: server.js never fails
// to boot without them, it only degrades those specific features).

const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const PORT = 3199; // distinct from the interactive-session convention (3099), to avoid any collision if both ever run at once
const BASE_URL = `http://localhost:${PORT}`;
const TEST_PASSWORD = 'contract-test-password';
const TEST_INTERNAL_TOKEN = 'contract-test-internal-token';
const REPO_ROOT = path.join(__dirname, '..');

let serverProcess;
let cookie;

async function waitForServer(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/api/dashboard`);
      if (res.status) return;
    } catch {
      // not up yet
    }
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: TEST_PASSWORD, INTERNAL_SERVICE_TOKEN: TEST_INTERNAL_TOKEN },
  });
  await waitForServer();

  const loginRes = await fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: TEST_PASSWORD }),
  });
  const setCookie = loginRes.headers.get('set-cookie');
  assert.ok(setCookie, 'login must set a session cookie');
  cookie = setCookie.split(';')[0];
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('GET /api/v1/docs lists every registered service with both a data and health endpoint', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.success, true);
  assert.ok(Array.isArray(body.services));
  assert.ok(body.services.length >= 11, `expected at least 11 services, got ${body.services.length}`);
  for (const svc of body.services) {
    assert.equal(svc.data_endpoint, `/api/v1/${svc.name}`);
    assert.equal(svc.health_endpoint, `/api/v1/${svc.name}/health`);
    assert.ok(svc.description && svc.description.length > 0);
  }
});

test('every documented service responds 200 with the standard success envelope', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  for (const svc of services) {
    const res = await fetch(`${BASE_URL}${svc.data_endpoint}`, { headers: { Cookie: cookie } });
    assert.equal(res.status, 200, `${svc.name} data endpoint should return 200`);
    const body = await res.json();
    assert.equal(body.success, true, `${svc.name} should report success:true`);
    assert.equal(body.service, svc.name);
    assert.equal(body.version, 'v1');
    assert.ok('data' in body, `${svc.name} response must have a data field`);
  }
});

test('every documented service health endpoint responds with a real status', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  for (const svc of services) {
    const res = await fetch(`${BASE_URL}${svc.health_endpoint}`, { headers: { Cookie: cookie } });
    assert.equal(res.status, 200, `${svc.name} health endpoint should return 200`);
    const body = await res.json();
    assert.equal(body.success, true);
    assert.ok(['ok', 'error'].includes(body.status), `${svc.name} health status must be ok/error, got ${body.status}`);
  }
});

test('GET /api/v1/health aggregates all documented services', async () => {
  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const { services } = await docsRes.json();
  const res = await fetch(`${BASE_URL}/api/v1/health`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.total_count, services.length);
  assert.ok(['healthy', 'degraded', 'unhealthy'].includes(body.overall));
});

test('GET /api/v1/metrics returns valid Prometheus exposition format', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/metrics`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  assert.match(res.headers.get('content-type'), /text\/plain/);
  const text = await res.text();
  assert.match(text, /^# HELP galaxy_forge_uptime_seconds/m);
  assert.match(text, /^# TYPE galaxy_forge_uptime_seconds gauge/m);
});

// Galaxy Forge Executive Mission Control v1 (2026-07-24): the 4 new,
// thin, read-only services this dashboard added. Shape-only, real-data
// assertions here (the generic "every documented service" tests above
// already cover the envelope contract) — never asserts a specific
// count/value that would make this test flaky against real, changing
// factory state.

test('evidence-engine-status reports the real Market Evidence Ledger honestly', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/evidence-engine-status`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const { data } = await res.json();
  assert.ok(typeof data.total_events === 'number');
  assert.ok(typeof data.niches_with_evidence === 'number');
  assert.ok(typeof data.by_event_type === 'object');
  assert.ok(typeof data.payment_evidence_events === 'number');
});

test('scheduler-status reports a real shape regardless of platform (never fabricates availability)', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/scheduler-status`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const { data } = await res.json();
  assert.ok(typeof data.available === 'boolean');
  if (data.available) {
    assert.equal(typeof data.task_name, 'string');
    assert.equal(typeof data.state, 'string');
  } else {
    assert.ok(typeof data.note === 'string' && data.note.length > 0, 'unavailable must explain why, never a silent false');
  }
});

test('recent-adr-decisions lists real ADRs, sorted newest-number-first', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/recent-adr-decisions`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const { data } = await res.json();
  assert.ok(data.total > 100, `expected 100+ real ADRs on record, got ${data.total}`);
  assert.ok(Array.isArray(data.recent) && data.recent.length > 0);
  for (let i = 1; i < data.recent.length; i++) {
    assert.ok(data.recent[i - 1].number >= data.recent[i].number, 'must be sorted newest-first');
  }
  assert.ok(data.recent[0].title && data.recent[0].title.length > 0);
});

test('system-logs reads the real log files this factory actually writes', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/system-logs`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const { data } = await res.json();
  assert.ok('factory_loop.log' in data);
  assert.ok('server_crashes.log' in data);
  for (const info of Object.values(data)) {
    assert.equal(typeof info.exists, 'boolean');
    if (info.exists && !info.error) assert.ok(Array.isArray(info.last_lines));
  }
});

test('GET /api/v1/actions lists every registered action with a name, description, and kind', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/actions`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.ok(Array.isArray(body.actions));
  assert.ok(body.actions.length >= 8, `expected at least 8 actions, got ${body.actions.length}`);
  for (const action of body.actions) {
    assert.ok(action.name);
    assert.ok(['sync', 'async'].includes(action.kind));
    assert.equal(typeof action.reversible, 'boolean');
  }
});

test('POST /api/v1/actions/:name requires confirmed:true (contract, not just one action)', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/actions/refresh-data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({}),
  });
  assert.equal(res.status, 400);
  const body = await res.json();
  assert.equal(body.success, false);
  assert.equal(body.error.code, 'confirmation_required');
});

test('unauthenticated requests to /api/v1/* are rejected as JSON, not redirected', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/company-health`, { redirect: 'manual' });
  assert.equal(res.status, 401);
  const body = await res.json();
  assert.equal(body.success, false);
});

test('unknown /api/v1/* path returns a 404 JSON envelope, not the SPA fallback', async () => {
  const res = await fetch(`${BASE_URL}/api/v1/not-a-real-service`, { headers: { Cookie: cookie } });
  assert.equal(res.status, 404);
  const contentType = res.headers.get('content-type');
  assert.match(contentType, /application\/json/);
});

test('GET /api/dashboard (pre-existing, unauthenticated) still responds 200', async () => {
  const res = await fetch(`${BASE_URL}/api/dashboard`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.success, true);
});

// Red-team audit (Phase 10 follow-up) — CRITICAL finding, fixed: server.js
// used to serve the entire repo root via express.static with no auth,
// exposing finance_data.json, data/*.jsonl, config/*.json, and every real
// product PDF under books/ to anyone who could reach the port.
test('sensitive repo files are no longer served as static content', async () => {
  for (const p of ['/finance_data.json', '/data/decisions.jsonl', '/config/economics.json']) {
    const res = await fetch(`${BASE_URL}${p}`, { redirect: 'manual' });
    // Must fall through to the SPA catch-all (text/html), never the real
    // file's own content-type — proves the raw file isn't being served.
    const contentType = res.headers.get('content-type') || '';
    assert.ok(
      contentType.includes('text/html'),
      `${p} must not be served with its real content-type, got: ${contentType}`
    );
  }
});

test('real product PDFs under books/ are no longer served as static content', async () => {
  const fs = require('fs');
  const path = require('path');
  const booksDir = path.join(REPO_ROOT, 'books');
  const pdfs = fs.existsSync(booksDir) ? fs.readdirSync(booksDir).filter(f => f.endsWith('.pdf')) : [];
  if (pdfs.length === 0) return; // nothing to check in this environment
  const res = await fetch(`${BASE_URL}/books/${encodeURIComponent(pdfs[0])}`, { redirect: 'manual' });
  const contentType = res.headers.get('content-type') || '';
  assert.ok(!contentType.includes('application/pdf'), `a real product PDF must not be downloadable unauthenticated, got: ${contentType}`);
});

// Zero-assumption audit follow-up — Critical finding, fixed: server.js
// used to bind all interfaces (0.0.0.0 + ::), making every unauthenticated
// legacy route reachable from the LAN. Now binds 127.0.0.1 explicitly. If
// the real server were still bound to all interfaces, a second listener
// could NOT also bind 0.0.0.0 on the same port (EADDRINUSE) — succeeding
// here proves the real server is loopback-only, not just claimed to be.
// Zero-assumption audit follow-up — Critical finding, fixed: /chat,
// /finance/add, and DELETE /finance/delete/:id predated Mission Control's
// auth layer and had zero authentication (confirmed zero callers anywhere
// in the UI, so gating them has no regression risk).
test('POST /chat now requires Mission Control auth', async () => {
  const unauth = await fetch(`${BASE_URL}/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'hi' }),
  });
  assert.equal(unauth.status, 401);
  const body = await unauth.json();
  assert.equal(body.success, false);
});

test('POST /finance/add now requires Mission Control auth, and works when authenticated', async () => {
  const unauth = await fetch(`${BASE_URL}/finance/add`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ platform: 'Gumroad', amount: 1, product: 'test' }),
  });
  assert.equal(unauth.status, 401);

  // This suite runs against the real finance_data.json (same cwd as the
  // real factory) — the test sale is immediately deleted afterward so no
  // trace is left in real financial data.
  const authed = await fetch(`${BASE_URL}/finance/add`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ platform: 'Gumroad', amount: 1, product: 'contract-test-sale-DELETE-ME' }),
  });
  assert.equal(authed.status, 200);
  const body = await authed.json();
  assert.equal(body.success, true);
  assert.ok(body.sale && body.sale.id);

  const cleanup = await fetch(`${BASE_URL}/finance/delete/${body.sale.id}`, {
    method: 'DELETE', headers: { Cookie: cookie },
  });
  assert.equal(cleanup.status, 200, 'cleanup delete of the test sale must succeed — no trace should remain in real finance_data.json');
});

// ADR-065 Step 3(c) — finance's "4-layer" rollup: platform totals now
// include Paddle (paddle_arm.py, Step 4), and every sale rolls up under a
// Strategic Production Priority Ladder rank (byLadder), defaulting to
// 'kdp_books' when omitted so pre-existing sales self-heal honestly
// instead of guessing a different rank.
test('POST /finance/add accepts Paddle + a ladder rank, and GET /finance rolls both up', async () => {
  const authed = await fetch(`${BASE_URL}/finance/add`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ platform: 'Paddle', amount: 150, product: 'contract-test-ladder-DELETE-ME', ladder: 'ai_saas' }),
  });
  assert.equal(authed.status, 200);
  const body = await authed.json();
  assert.equal(body.success, true);
  assert.equal(body.sale.ladder, 'ai_saas');

  const fin = await (await fetch(`${BASE_URL}/finance`, { headers: { Cookie: cookie } })).json();
  assert.ok(fin.totalPaddle >= 150);
  assert.ok(fin.byLadder && fin.byLadder.ai_saas >= 150);

  await fetch(`${BASE_URL}/finance/delete/${body.sale.id}`, { method: 'DELETE', headers: { Cookie: cookie } });
});

test('POST /finance/add with an unknown ladder value defaults to kdp_books, never rejects', async () => {
  const authed = await fetch(`${BASE_URL}/finance/add`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ platform: 'KDP', amount: 5, product: 'contract-test-unknown-ladder-DELETE-ME', ladder: 'not-a-real-rank' }),
  });
  assert.equal(authed.status, 200);
  const body = await authed.json();
  assert.equal(body.sale.ladder, 'kdp_books');
  await fetch(`${BASE_URL}/finance/delete/${body.sale.id}`, { method: 'DELETE', headers: { Cookie: cookie } });
});

test('DELETE /finance/delete/:id now requires Mission Control auth', async () => {
  const unauth = await fetch(`${BASE_URL}/finance/delete/123`, { method: 'DELETE' });
  assert.equal(unauth.status, 401);

  const authed = await fetch(`${BASE_URL}/finance/delete/999999999`, { method: 'DELETE', headers: { Cookie: cookie } });
  assert.equal(authed.status, 200, 'an authenticated call for a non-existent id must still succeed cleanly (idempotent delete)');
});

// Enterprise Security & Cyber Defense Mission, Phase 2, finding 2.1
// (2026-07-23) — Critical finding, fixed: ~15+ routes had zero
// authentication, including a direct, unmetered proxy to the founder's
// real Groq API key (POST /api/agent/:name). Every browser-only route
// (no internal automation caller) now requires requireMissionControlAuth.
// A representative sample is tested here, not every route — the
// middleware itself is the thing under test, not each handler's business
// logic (already covered elsewhere). /api/agent/:name's "authenticated"
// path is deliberately NOT exercised here (it would make a real,
// billed Groq call on every CI run) — only that it 401s unauthenticated,
// which never reaches the Groq call.
test('GET /oracle now requires Mission Control auth, and works when authenticated', async () => {
  // A non-/api/ GET route redirects to the login page rather than
  // returning 401 JSON (requireMissionControlAuth's own real behavior,
  // already covered generally by the /api/v1/* test above) — redirect:
  // 'manual' inspects that real redirect instead of letting fetch()
  // silently follow it to the (intentionally public) login page's own
  // 200, which would otherwise make this assertion pass for the wrong
  // reason.
  const unauth = await fetch(`${BASE_URL}/oracle`, { redirect: 'manual' });
  assert.equal(unauth.status, 302);
  assert.equal(unauth.headers.get('location'), '/mission_control_login.html');

  const authed = await fetch(`${BASE_URL}/oracle`, { headers: { Cookie: cookie } });
  assert.equal(authed.status, 200);
});

test('POST /api/agent/:name now requires Mission Control auth (never reaches the real Groq call unauthenticated)', async () => {
  const unauth = await fetch(`${BASE_URL}/api/agent/scout`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'this must never reach Groq unauthenticated' }),
  });
  assert.equal(unauth.status, 401);
  const body = await unauth.json();
  assert.equal(body.success, false);
});

// The 4 routes real internal automation calls with no browser session
// available (factory_loop.js's own pipeline, and the 01_Market_Scout n8n
// workflow) — these accept EITHER a session OR X-Internal-Token, never
// neither. /api/sales/poll is used as the representative case: safe to
// fully execute repeatedly (no configured real sales-channel tokens in
// this test environment, so it reports real skip_reasons, never a crash
// or a real external call — same real, already-tested behavior
// poll_sales.py's own test suite covers).
test('POST /api/sales/poll requires a session OR the internal service token, never neither', async () => {
  const noAuth = await fetch(`${BASE_URL}/api/sales/poll`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
  });
  assert.equal(noAuth.status, 401);

  const wrongToken = await fetch(`${BASE_URL}/api/sales/poll`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Internal-Token': 'not-the-real-token' }, body: '{}',
  });
  assert.equal(wrongToken.status, 401, 'a wrong token must be rejected exactly like no token at all');

  const withToken = await fetch(`${BASE_URL}/api/sales/poll`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Internal-Token': TEST_INTERNAL_TOKEN }, body: '{}',
  });
  assert.equal(withToken.status, 200, 'the real internal service token (what factory_loop.js and the Scout n8n workflow actually send) must be accepted');

  const withCookie = await fetch(`${BASE_URL}/api/sales/poll`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Cookie: cookie }, body: '{}',
  });
  assert.equal(withCookie.status, 200, 'a real Mission Control session must also be accepted — this is (session OR token), not token-only');
});

// Zero-assumption audit follow-up — Medium-High finding, fixed: runReality()
// spawned a fresh Python interpreter on every call with no caching (freshly
// measured live: 3-4s per call on GET /api/dashboard, the exact endpoint
// dashboard.html polls every 60s). Now cached for 30s. This asserts real,
// repeat-call speed rather than a specific millisecond number, to stay
// robust across slower CI environments while still catching a regression
// back to "every call re-spawns Python" (which would consistently cost
// multiple real seconds per call, not sub-second).
test('GET /api/reality is cached — repeat calls within the TTL are consistently fast, not re-spawning Python each time', async () => {
  await fetch(`${BASE_URL}/api/reality`, { headers: { Cookie: cookie } }); // warm the cache
  const timings = [];
  for (let i = 0; i < 3; i++) {
    const start = Date.now();
    const res = await fetch(`${BASE_URL}/api/reality`, { headers: { Cookie: cookie } });
    await res.json();
    timings.push(Date.now() - start);
  }
  for (const t of timings) {
    assert.ok(t < 1500, `expected a cached /api/reality call to be well under 1500ms, got ${t}ms — caching may have regressed`);
  }
});

test('server binds to loopback only, not all interfaces', async () => {
  const probe = net.createServer();
  const bindResult = await new Promise((resolve) => {
    probe.once('error', (err) => resolve({ bound: false, code: err.code }));
    probe.once('listening', () => resolve({ bound: true }));
    probe.listen(PORT, '0.0.0.0');
  });
  probe.close();
  assert.equal(bindResult.bound, true, `expected to be able to also bind 0.0.0.0:${PORT} (proving the real server isn't on all interfaces), got: ${JSON.stringify(bindResult)}`);
});

test('dashboard.html and mission_control_login.html still serve correctly (no regression)', async () => {
  const dashRes = await fetch(`${BASE_URL}/dashboard.html`);
  assert.equal(dashRes.status, 200);
  assert.match(dashRes.headers.get('content-type'), /text\/html/);

  const loginRes = await fetch(`${BASE_URL}/mission_control_login.html`);
  assert.equal(loginRes.status, 200);
  assert.match(loginRes.headers.get('content-type'), /text\/html/);
});

test('mission_control_executive_v1.html requires Mission Control auth, and serves when authenticated (CEO review, 2026-07-25 polish pass)', async () => {
  const unauth = await fetch(`${BASE_URL}/mission_control_executive_v1.html`, { redirect: 'manual' });
  assert.equal(unauth.status, 302);
  assert.equal(unauth.headers.get('location'), '/mission_control_login.html');

  const authed = await fetch(`${BASE_URL}/mission_control_executive_v1.html`, { headers: { Cookie: cookie } });
  assert.equal(authed.status, 200);
  assert.match(authed.headers.get('content-type'), /text\/html/);
});
