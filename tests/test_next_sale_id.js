// Regression test for the Phase 10 red-team audit's MEDIUM finding:
// server.js used `id: Date.now()` for a sale's unique id, so two sales
// added within the same millisecond collided; DELETE
// /finance/delete/:id then silently deleted both. Pure unit test —
// no server, no real finance_data.json touched.
//
//   node --test tests/test_next_sale_id.js

const test = require('node:test');
const assert = require('node:assert/strict');
const { nextSaleId } = require('../lib/next_sale_id.js');

test('nextSaleId: returns an id that does not collide with an existing sale at the same millisecond', () => {
  const now = Date.now();
  const existing = [{ id: now, platform: 'Gumroad', amount: 10, product: 'x', date: '2026-07-17' }];
  const id = nextSaleId(existing);
  assert.notEqual(id, now);
  assert.equal(typeof id, 'number');
});

test('nextSaleId: three sequential calls against the same growing list never collide', () => {
  const sales = [];
  const ids = new Set();
  for (let i = 0; i < 3; i++) {
    const id = nextSaleId(sales);
    assert.ok(!ids.has(id), `id ${id} collided`);
    ids.add(id);
    sales.push({ id, platform: 'Gumroad', amount: 1, product: 'x', date: '2026-07-17' });
  }
  assert.equal(ids.size, 3);
});

test('nextSaleId: with no existing sales, returns a plain integer close to Date.now()', () => {
  const before = Date.now();
  const id = nextSaleId([]);
  const after = Date.now();
  assert.ok(Number.isInteger(id));
  assert.ok(id >= before && id <= after + 5);
});

test('nextSaleId: DELETE /finance/delete/:id contract is preserved — id round-trips through parseInt', () => {
  const id = nextSaleId([{ id: Date.now() }]);
  assert.equal(parseInt(String(id), 10), id);
});
