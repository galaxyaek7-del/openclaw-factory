// B38 low-disk mode in factory_loop.js (2026-10-29). Below 2 GB free, PDF/cover
// generation (triggerGenerateBook) is refused without any HTTP call; the state
// comes from the /health disk check. No network, no server needed.
const test = require('node:test');
const assert = require('node:assert/strict');

const fl = require('../factory_loop.js');

test('state follows the disk check', () => {
  assert.deepEqual(fl.lowDiskState({ disk: { ok: false, free_gb: 1.4 } }), { active: true, free_gb: 1.4 });
  assert.deepEqual(fl.lowDiskState({ disk: { ok: true, free_gb: 5.7 } }), { active: false, free_gb: 5.7 });
  assert.deepEqual(fl.lowDiskState({ disk: { ok: false } }), { active: false, free_gb: null });
  assert.deepEqual(fl.lowDiskState(null), { active: false, free_gb: null });
});

test('book generation is refused in low-disk mode without calling the server', async () => {
  const realFetch = global.fetch;
  let called = 0;
  global.fetch = async () => { called++; throw new Error('must not be called'); };
  try {
    fl.setLowDiskState({ active: true, free_gb: 1.2 });
    const r = await fl.triggerGenerateBook({ title: 'x' });
    assert.equal(r.ok, false);
    assert.equal(r.low_disk, true);
    assert.match(r.detail, /1\.2GB/);
    assert.equal(called, 0);
  } finally {
    fl.setLowDiskState(null);
    global.fetch = realFetch;
  }
});

test('outside low-disk mode the guard does not interfere', async () => {
  const realFetch = global.fetch;
  global.fetch = async () => { throw new Error('offline in test'); };
  try {
    fl.setLowDiskState({ active: false, free_gb: 9 });
    const r = await fl.triggerGenerateBook({ title: 'x' });
    assert.equal(r.low_disk, undefined);
    assert.equal(r.ok, false);
  } finally {
    fl.setLowDiskState(null);
    global.fetch = realFetch;
  }
});
