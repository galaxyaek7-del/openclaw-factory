// Tests for lib/health_checks.js (Enterprise Infrastructure & HA
// Mission, 2026-07-23, finding 4.7). No live server needed — same
// isolation discipline as tests/test_dashboard_data.js.
//
//   node --test tests/test_health_checks.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  checkMemory, checkCpu, checkDiskSpace, checkNetworkReachability,
  checkStorageIntegrity, notApplicableChecks, buildHealthReport,
} = require('../lib/health_checks.js');

test('checkMemory reports real, plausible values', () => {
  const result = checkMemory();
  assert.equal(typeof result.ok, 'boolean');
  assert.ok(result.process_rss_mb > 0, 'a running Node process always has non-zero RSS');
  assert.ok(result.system_free_pct >= 0 && result.system_free_pct <= 100);
});

test('checkCpu is honest about os.loadavg() being meaningless on Windows', () => {
  const result = checkCpu();
  assert.ok(result.cores > 0);
  if (process.platform === 'win32') {
    assert.equal(result.load_avg_available, false);
    assert.equal(result.load_avg, null);
    assert.match(result.detail, /Windows/);
  } else {
    assert.equal(result.load_avg_available, true);
    assert.ok(Array.isArray(result.load_avg));
  }
});

test('checkDiskSpace on Windows: parses a real PowerShell-shaped response', async () => {
  const fakeRun = (cmd, args, opts, cb) => {
    cb(null, JSON.stringify({ Used: 400 * 1e9, Free: 100 * 1e9 }));
  };
  const result = await checkDiskSpace(__dirname, { run: process.platform === 'win32' ? fakeRun : undefined });
  if (process.platform === 'win32') {
    assert.equal(result.ok, true);
    assert.equal(result.free_gb, 100);
    assert.equal(result.free_pct, 20);
  } else {
    assert.equal(result.ok, null);
    assert.match(result.detail, /Windows/);
  }
});

test('checkDiskSpace reports low free space as not ok, never silently green', async () => {
  if (process.platform !== 'win32') return; // this path is Windows-specific by design, see the module's own comment
  const fakeRun = (cmd, args, opts, cb) => {
    cb(null, JSON.stringify({ Used: 990 * 1e9, Free: 10 * 1e9 })); // 1% free
  };
  const result = await checkDiskSpace(__dirname, { run: fakeRun });
  assert.equal(result.ok, false);
  assert.equal(result.severity, 'critical');
});

test('checkDiskSpace never throws when the shell-out fails, reports honestly', async () => {
  if (process.platform !== 'win32') return;
  const fakeRun = (cmd, args, opts, cb) => cb(new Error('powershell not found'));
  const result = await checkDiskSpace(__dirname, { run: fakeRun });
  assert.equal(result.ok, null);
  assert.match(result.detail, /تعذَّر/);
});

test('checkNetworkReachability: all real targets reachable', async () => {
  const fakeFetch = async () => ({ ok: true });
  const result = await checkNetworkReachability({ fetchImpl: fakeFetch, hasTelegramToken: true, hasGitRemote: true });
  assert.equal(result.ok, true);
  assert.deepEqual(Object.keys(result.targets).sort(), ['github_remote', 'groq_api', 'telegram_api']);
});

test('checkNetworkReachability: groq down (required) fails the whole check', async () => {
  const fakeFetch = async (url) => {
    if (url.includes('groq')) throw new Error('network unreachable');
    return { ok: true };
  };
  const result = await checkNetworkReachability({ fetchImpl: fakeFetch, hasTelegramToken: true });
  assert.equal(result.ok, false);
  assert.equal(result.targets.groq_api.ok, false);
});

test('checkNetworkReachability: telegram down (optional) does not fail the whole check', async () => {
  const fakeFetch = async (url) => {
    if (url.includes('telegram')) throw new Error('network unreachable');
    return { ok: true };
  };
  const result = await checkNetworkReachability({ fetchImpl: fakeFetch, hasTelegramToken: true });
  assert.equal(result.ok, true, 'an optional target being down must not fail the overall check');
  assert.equal(result.targets.telegram_api.ok, false);
});

test('checkNetworkReachability: telegram_api is only checked when a real token is configured', async () => {
  const fakeFetch = async () => ({ ok: true });
  const result = await checkNetworkReachability({ fetchImpl: fakeFetch, hasTelegramToken: false });
  assert.ok(!('telegram_api' in result.targets));
});

function tempFile(suffix) {
  return path.join(os.tmpdir(), `health_check_test_${Date.now()}_${Math.random().toString(36).slice(2)}${suffix}`);
}

test('checkStorageIntegrity: a missing file is reported ok (not yet created, not corrupt)', () => {
  const missing = tempFile('.json');
  const result = checkStorageIntegrity([{ name: 'missing', filePath: missing, format: 'json' }]);
  assert.equal(result.ok, true);
  assert.equal(result.files.missing.exists, false);
});

test('checkStorageIntegrity: a valid JSON file passes', () => {
  const p = tempFile('.json');
  fs.writeFileSync(p, JSON.stringify({ real: true }));
  try {
    const result = checkStorageIntegrity([{ name: 'f', filePath: p, format: 'json' }]);
    assert.equal(result.ok, true);
    assert.equal(result.files.f.ok, true);
  } finally { fs.rmSync(p); }
});

test('checkStorageIntegrity: a corrupt JSON file is caught, not silently passed', () => {
  const p = tempFile('.json');
  fs.writeFileSync(p, '{ this is not valid json');
  try {
    const result = checkStorageIntegrity([{ name: 'f', filePath: p, format: 'json' }]);
    assert.equal(result.ok, false);
    assert.equal(result.files.f.ok, false);
  } finally { fs.rmSync(p); }
});

test('checkStorageIntegrity: a real JSONL file with one corrupt trailing line is caught precisely, not treated as fully broken', () => {
  const p = tempFile('.jsonl');
  fs.writeFileSync(p, '{"a":1}\n{"a":2}\n{"a":3, corrupt\n');
  try {
    const result = checkStorageIntegrity([{ name: 'f', filePath: p, format: 'jsonl' }]);
    assert.equal(result.files.f.ok, false);
    assert.equal(result.files.f.valid_lines, 2);
    assert.equal(result.files.f.invalid_lines, 1);
  } finally { fs.rmSync(p); }
});

test('notApplicableChecks reports database/queue/worker honestly as not_applicable, never fabricated as ok', () => {
  const result = notApplicableChecks();
  for (const key of ['database', 'queue_system', 'worker_pool']) {
    assert.equal(result[key].severity, 'not_applicable');
    assert.equal(result[key].ok, null, `${key} must never be a fabricated true/false — it doesn't exist`);
  }
});

test('buildHealthReport: not_applicable checks never affect overall status', async () => {
  const report = await buildHealthReport({
    run: (cmd, args, opts, cb) => cb(null, JSON.stringify({ Used: 100e9, Free: 900e9 })),
    fetchImpl: async () => ({ ok: true }),
    hasTelegramToken: false,
    storageFiles: [],
  });
  assert.equal(report.status, 'healthy');
  assert.equal(report.checks.database.severity, 'not_applicable');
});

test('buildHealthReport: a real critical failure (network down) surfaces as overall critical', async () => {
  const report = await buildHealthReport({
    run: (cmd, args, opts, cb) => cb(null, JSON.stringify({ Used: 100e9, Free: 900e9 })),
    fetchImpl: async () => { throw new Error('down'); },
    hasTelegramToken: false,
    storageFiles: [],
  });
  assert.equal(report.status, 'critical');
});
