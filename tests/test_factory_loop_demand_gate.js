// Founder's second order 2026-11-05: the freeze lifts only on real demand, and the gate fails closed.
//   node tests/test_factory_loop_demand_gate.js
const assert = require('assert');
const path = require('path');
const os = require('os');
const fs = require('fs');
const { execFileSync } = require('child_process');

const PROBE = path.join(__dirname, 'helpers', 'probe_demand_gate.js');
let passed = 0;
function test(name, fn) {
  try { fn(); console.log(`ok - ${name}`); passed++; } catch (err) { console.error(`FAIL - ${name}`); console.error(err); process.exitCode = 1; }
}

function probe(env) {
  const slotsFile = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf-slots-')), 'slots.json');
  const base = { ...process.env };
  for (const k of ['GF_FREEZE_NEW_PRODUCTS', 'GF_DEMAND_GATED', 'PROBE_GATE', 'PROBE_CAP', 'PROBE_SLOTS']) delete base[k];
  const out = execFileSync(process.execPath, [PROBE], {
    cwd: os.tmpdir(), env: { ...base, GF_DEMAND_SLOTS_PATH: slotsFile, ...env }, encoding: 'utf-8',
  });
  return JSON.parse(out);
}

test('no freeze flag: never frozen, whatever the gate says', () => {
  assert.strictEqual(probe({ PROBE_GATE: 'closed' }).frozen, false);
});

test('freeze flag without the gate switch: frozen, exactly as before', () => {
  assert.strictEqual(probe({ GF_FREEZE_NEW_PRODUCTS: 'true', PROBE_GATE: 'open' }).frozen, true);
});

test('gated and demand is real: the freeze lifts', () => {
  assert.strictEqual(probe({ GF_FREEZE_NEW_PRODUCTS: 'true', GF_DEMAND_GATED: 'true', PROBE_GATE: 'open' }).frozen, false);
});

test('gated and no demand: stays frozen', () => {
  assert.strictEqual(probe({ GF_FREEZE_NEW_PRODUCTS: 'true', GF_DEMAND_GATED: 'true', PROBE_GATE: 'closed' }).frozen, true);
});

test('gated and the gate cannot be evaluated: fail closed', () => {
  for (const mode of ['garbage', 'error']) {
    assert.strictEqual(probe({ GF_FREEZE_NEW_PRODUCTS: 'true', GF_DEMAND_GATED: 'true', PROBE_GATE: mode }).frozen, true, mode);
  }
});

test('the daily cap is enforced while the gate is open', () => {
  const r = probe({ GF_FREEZE_NEW_PRODUCTS: 'true', GF_DEMAND_GATED: 'true', PROBE_GATE: 'open', PROBE_CAP: '2', PROBE_SLOTS: '4' });
  assert.deepStrictEqual(r.slots, [true, true, false, false]);
});

test('no slot is ever granted while the gate is closed', () => {
  const r = probe({ GF_FREEZE_NEW_PRODUCTS: 'true', GF_DEMAND_GATED: 'true', PROBE_GATE: 'closed', PROBE_SLOTS: '2' });
  assert.deepStrictEqual(r.slots, [false, false]);
});

test('without freeze or gate flags the cap does not apply', () => {
  const r = probe({ PROBE_GATE: 'closed', PROBE_SLOTS: '3' });
  assert.deepStrictEqual(r.slots, [true, true, true]);
});

console.log(`${passed} passed`);
