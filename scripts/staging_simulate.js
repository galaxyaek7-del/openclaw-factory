// Local staging simulation (Phase 10C — Operations Automation & CI/CD
// Pipeline). Formalizes the exact manual verification pattern used
// throughout this project's own development sessions: run full
// regression, boot a real throwaway server on an alternate port, smoke-
// test it, tear it down cleanly, report pass/fail. This factory has one
// real environment (CLAUDE.md: "everything local, no cloud") — this is
// the closest honest equivalent to a "staging" gate: the same code,
// running for real, on a port that can never collide with the actual
// running production instance (port 3000).
//
// Never touches the real running server.js/factory_loop.js. Standalone,
// deliberately-run tool — not wired into CI or any automation; run it
// yourself before considering a change ready to promote.
//
//   node scripts/staging_simulate.js

const { spawn, spawnSync } = require('child_process');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const STAGING_PORT = 3198;
const BASE_URL = `http://localhost:${STAGING_PORT}`;
const STAGING_PASSWORD = 'staging-simulation-password';

const results = [];

function step(name, fn) {
  console.log(`\n=== ${name} ===`);
  try {
    fn();
    results.push({ name, ok: true });
    console.log(`✔ ${name}`);
  } catch (err) {
    results.push({ name, ok: false, error: err.message });
    console.log(`✘ ${name}: ${err.message}`);
  }
}

async function stepAsync(name, fn) {
  console.log(`\n=== ${name} ===`);
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`✔ ${name}`);
  } catch (err) {
    results.push({ name, ok: false, error: err.message });
    console.log(`✘ ${name}: ${err.message}`);
  }
}

function run(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, { cwd: REPO_ROOT, stdio: 'inherit', ...opts });
  if (res.status !== 0) throw new Error(`${cmd} ${args.join(' ')} exited with code ${res.status}`);
}

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
  throw new Error('staging server did not become ready in time');
}

async function smokeTest() {
  await waitForServer();

  const loginRes = await fetch(`${BASE_URL}/api/mission-control/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: STAGING_PASSWORD }),
  });
  const setCookie = loginRes.headers.get('set-cookie');
  if (!setCookie) throw new Error('login did not set a session cookie');
  const cookie = setCookie.split(';')[0];

  const docsRes = await fetch(`${BASE_URL}/api/v1/docs`, { headers: { Cookie: cookie } });
  const docs = await docsRes.json();
  if (!docs.success || !Array.isArray(docs.services) || docs.services.length < 11) {
    throw new Error(`expected >=11 services in /api/v1/docs, got ${docs.services?.length}`);
  }

  for (const svc of docs.services) {
    const res = await fetch(`${BASE_URL}${svc.data_endpoint}`, { headers: { Cookie: cookie } });
    if (res.status !== 200) throw new Error(`${svc.name} data endpoint returned ${res.status}`);
  }

  const healthRes = await fetch(`${BASE_URL}/api/v1/health`, { headers: { Cookie: cookie } });
  const health = await healthRes.json();
  if (health.overall !== 'healthy') throw new Error(`aggregate health is ${health.overall}, expected healthy`);

  const mcRes = await fetch(`${BASE_URL}/mission_control.html`, { headers: { Cookie: cookie } });
  if (mcRes.status !== 200) throw new Error(`mission_control.html returned ${mcRes.status}`);
}

(async () => {
  step('Python regression suite', () => {
    run(process.platform === 'win32' ? 'python' : 'python3', ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py']);
  });

  step('JavaScript unit tests', () => {
    run('node', ['--test', 'tests/test_metrics.js', 'tests/test_dashboard_data.js', 'tests/test_n8n_notify.js']);
  });

  step('Factory Loop tests', () => {
    run('node', ['tests/test_factory_loop_golden.js']);
  });

  let serverProcess;
  step('Boot staging server on an isolated port', () => {
    serverProcess = spawn(process.execPath, ['server.js'], {
      cwd: REPO_ROOT,
      env: { ...process.env, PORT: String(STAGING_PORT), MISSION_CONTROL_PASSWORD: STAGING_PASSWORD },
      detached: false,
    });
  });

  await stepAsync('Smoke test staging server (auth, all services, aggregate health, Mission Control page)', smokeTest);

  step('Tear down staging server', () => {
    if (serverProcess) serverProcess.kill();
  });

  const failed = results.filter(r => !r.ok);
  console.log('\n=== Staging simulation summary ===');
  for (const r of results) console.log(`${r.ok ? '✔' : '✘'} ${r.name}${r.error ? ` — ${r.error}` : ''}`);
  console.log(failed.length ? `\nSTAGING: FAILED (${failed.length} step(s) failed)` : '\nSTAGING: PASSED — ready to promote');
  process.exit(failed.length ? 1 : 0);
})();
