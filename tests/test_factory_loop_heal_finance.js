// Tests for factory_loop.js healFinance() (Cycle 99). Temp files only —
// never the real finance_data.json.
//
//   node --test tests/test_factory_loop_heal_finance.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { healFinance } = require('../factory_loop.js');

const UNHEALTHY = { checks: { finance: { ok: false } } };
const REAL = JSON.stringify({ sales: [{ id: 's1', amount: 14.99 }], totalSales: 14.99 });

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'heal-finance-'));
}

test('healthy report: file untouched', () => {
  const d = tempDir(); const f = path.join(d, 'finance_data.json');
  fs.writeFileSync(f, REAL);
  const r = healFinance({ checks: { finance: { ok: true } } }, { financeFile: f });
  assert.equal(r.action, 'none');
  assert.equal(fs.readFileSync(f, 'utf8'), REAL);
});

test('stale "unhealthy" report but the file parses now: never reset', () => {
  const d = tempDir(); const f = path.join(d, 'finance_data.json');
  fs.writeFileSync(f, REAL);
  const r = healFinance(UNHEALTHY, { financeFile: f });
  assert.equal(r.action, 'none');
  assert.equal(fs.readFileSync(f, 'utf8'), REAL, 'real sales must survive a transient health failure');
  assert.deepEqual(fs.readdirSync(d), ['finance_data.json']);
});

test('unreadable file (e.g. a lock): skipped, never reset', () => {
  const d = tempDir(); const f = path.join(d, 'finance_data.json');
  fs.writeFileSync(f, REAL);
  const original = fs.readFileSync;
  fs.readFileSync = (p, ...rest) => {
    if (p === f) { const e = new Error('resource busy'); e.code = 'EBUSY'; throw e; }
    return original(p, ...rest);
  };
  let r;
  try { r = healFinance(UNHEALTHY, { financeFile: f }); } finally { fs.readFileSync = original; }
  assert.equal(r.action, 'skipped');
  assert.match(r.detail, /EBUSY/);
  assert.equal(fs.readFileSync(f, 'utf8'), REAL);
});

test('genuinely corrupt file: quarantined with a backup, then a clean file', () => {
  const d = tempDir(); const f = path.join(d, 'finance_data.json');
  fs.writeFileSync(f, '{"sales": [ broken');
  const r = healFinance(UNHEALTHY, { financeFile: f });
  assert.equal(r.action, 'healed');
  const backups = fs.readdirSync(d).filter((n) => n.includes('.loop-corrupt-'));
  assert.equal(backups.length, 1);
  assert.equal(fs.readFileSync(path.join(d, backups[0]), 'utf8'), '{"sales": [ broken');
  assert.deepEqual(JSON.parse(fs.readFileSync(f, 'utf8')).sales, []);
  assert.equal(fs.readdirSync(d).filter((n) => n.includes('.tmp-')).length, 0, 'no temp file left behind');
});

test('missing file: created clean', () => {
  const d = tempDir(); const f = path.join(d, 'finance_data.json');
  const r = healFinance(UNHEALTHY, { financeFile: f });
  assert.equal(r.action, 'healed');
  assert.deepEqual(JSON.parse(fs.readFileSync(f, 'utf8')).sales, []);
});
