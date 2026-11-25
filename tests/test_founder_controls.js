// Tests for lib/founder_controls.js and founder_controls.html (local founder
// controls: STOP/resume and production pause). No server is booted; the module
// takes explicit paths so nothing under data/ or the repo root is touched.
//
//   node --test tests/test_founder_controls.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const C = require('../lib/founder_controls.js');

const HTML_PATH = path.join(__dirname, '..', 'founder_controls.html');
const HTML = fs.readFileSync(HTML_PATH, 'utf8');
const DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'gf-founder-controls-'));
const PATHS = {
  stop: path.join(DIR, 'STOP'),
  heartbeat: path.join(DIR, 'heartbeat.json'),
  production: path.join(DIR, 'production_control.json'),
};

test.after(() => {
  fs.rmSync(DIR, { recursive: true, force: true });
});

test('default paths match the real consumers', () => {
  const p = C.resolve();
  assert.ok(p.stop.endsWith('STOP'));
  assert.ok(p.heartbeat.endsWith(path.join('data', 'heartbeat.json')));
  assert.ok(p.production.endsWith(path.join('data', 'production_control.json')));
});

test('initial status is stopped=false, paused=false, heartbeat absent', () => {
  const s = C.status(PATHS);
  assert.equal(s.stop.requested, false);
  assert.equal(s.production.paused, false);
  assert.equal(s.heartbeat.present, false);
  assert.equal(s.gates.live_publish, process.env.FACTORY_LIVE_PUBLISH === 'true');
});

test('requestStop writes the STOP file and status reflects it', () => {
  const s = C.requestStop(PATHS);
  assert.equal(s.stop.requested, true);
  assert.equal(fs.existsSync(PATHS.stop), true);
  assert.match(fs.readFileSync(PATHS.stop, 'utf8'), /STOP requested/);
});

test('clearStop removes the STOP file and is idempotent', () => {
  assert.equal(C.clearStop(PATHS).stop.requested, false);
  assert.equal(fs.existsSync(PATHS.stop), false);
  assert.equal(C.clearStop(PATHS).stop.requested, false);
});

test('setProductionPaused(true, reason) persists and is read back', () => {
  const s = C.setProductionPaused(true, 'test reason', PATHS);
  assert.equal(s.production.paused, true);
  assert.equal(s.production.reason, 'test reason');
  const onDisk = JSON.parse(fs.readFileSync(PATHS.production, 'utf8'));
  assert.equal(onDisk.paused, true);
  assert.equal(onDisk.reason, 'test reason');
  assert.match(onDisk.changed_at, /^\d{4}-\d{2}-\d{2}T/);
});

test('setProductionPaused(false) clears the reason', () => {
  const s = C.setProductionPaused(false, 'ignored', PATHS);
  assert.equal(s.production.paused, false);
  assert.equal(s.production.reason, null);
});

test('heartbeat status reports present, pid and a non-negative age', () => {
  fs.writeFileSync(PATHS.heartbeat, JSON.stringify({ at: '2026-11-25T00:00:00.000Z', pid: 4321, phase: 'start' }), 'utf8');
  const s = C.status(PATHS);
  assert.equal(s.heartbeat.present, true);
  assert.equal(s.heartbeat.pid, 4321);
  assert.equal(s.heartbeat.phase, 'start');
  assert.ok(Number.isInteger(s.heartbeat.age_seconds));
  assert.ok(s.heartbeat.age_seconds >= 0);
});

test('the page is RTL, offline and names every control endpoint', () => {
  assert.match(HTML, /dir="rtl"/);
  assert.doesNotMatch(HTML, /https?:\/\//, 'the control page must not reference any external URL');
  for (const ep of [
    '/api/v1/founder/control',
    '/api/v1/founder/control/stop',
    '/api/v1/founder/control/resume',
    '/api/v1/founder/control/pause-production',
    '/api/v1/founder/control/resume-production',
  ]) {
    assert.ok(HTML.includes(ep), 'missing endpoint in page: ' + ep);
  }
});

test('the page offers the four safe controls and states the locked gates', () => {
  for (const label of ['إيقاف المصنع فوراً (STOP)', 'استئناف المصنع', 'إيقاف الإنتاج مؤقتاً', 'استئناف الإنتاج']) {
    assert.ok(HTML.includes(label), 'missing control: ' + label);
  }
  assert.match(HTML, /بوابات مقفلة/);
  assert.match(HTML, /إعادة تشغيل/);
});

test('the page script parses (no syntax error)', () => {
  const m = HTML.match(/<script>([\s\S]*?)<\/script>/);
  assert.ok(m, 'no inline script found');
  assert.doesNotThrow(() => new Function(m[1]));
});
