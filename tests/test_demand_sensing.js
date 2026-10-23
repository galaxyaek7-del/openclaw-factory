// lib/demand_sensing.js -- real questions to /api/trends, once a day, no repeats.
// Fake fetch and post; temp state file. node --test tests/test_demand_sensing.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { runDemandSensing, clean, SE_SITES } = require('../lib/demand_sensing');

const statePath = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf_ds_')), 'state.json');

function fakeFetch({ failSites = [], hnFail = false } = {}) {
  return async (url) => {
    const site = /site=(\w+)/.exec(url);
    if (site) {
      if (failSites.includes(site[1])) return { ok: false, status: 503 };
      return { ok: true, json: async () => ({ items: [{ question_id: 1, title: `How do I invoice clients on ${site[1]}?` }] }) };
    }
    if (hnFail) return { ok: false, status: 500 };
    return { ok: true, json: async () => ({ hits: [{ objectID: '42', title: 'Ask HN: How do you track client time &amp; expenses?' }] }) };
  };
}

function fakePost(accept = 1) {
  const sent = [];
  return { sent, post: async (items) => { sent.push(...items); return { added: accept }; } };
}

test('fetches every source and delivers new questions through /api/trends', async () => {
  const p = fakePost(2);
  const r = await runDemandSensing({ post: p.post, day: '2026-10-24', statePath: statePath(), fetchImpl: fakeFetch() });
  assert.equal(p.sent.length, SE_SITES.length + 1);
  assert.ok(p.sent.some((i) => i.title === 'How do you track client time & expenses?'), 'HN prefix and entities cleaned');
  assert.ok(p.sent.every((i) => i.niche === i.title && i.source));
  assert.equal(r.action, 'added');
});

test('runs once per day and never resends a question id', async () => {
  const s = statePath();
  const p = fakePost();
  await runDemandSensing({ post: p.post, day: 'd1', statePath: s, fetchImpl: fakeFetch() });
  assert.equal((await runDemandSensing({ post: p.post, day: 'd1', statePath: s, fetchImpl: fakeFetch() })).action, 'none');
  const before = p.sent.length;
  await runDemandSensing({ post: p.post, day: 'd2', statePath: s, fetchImpl: fakeFetch() });
  assert.equal(p.sent.length, before, 'same ids on the next day are not sent again');
});

test('one source failing does not stop the others; errors are reported', async () => {
  const p = fakePost();
  const r = await runDemandSensing({ post: p.post, day: 'd', statePath: statePath(), fetchImpl: fakeFetch({ failSites: ['money'], hnFail: true }) });
  assert.equal(p.sent.length, SE_SITES.length - 1);
  assert.match(r.detail, /stackexchange\/money: HTTP 503/);
  assert.match(r.detail, /ask_hn: HTTP 500/);
});

test('a failed delivery leaves the day open for the next tick', async () => {
  const s = statePath();
  await assert.rejects(runDemandSensing({ post: async () => { throw new Error('server down'); }, day: 'd', statePath: s, fetchImpl: fakeFetch() }));
  const p = fakePost();
  await runDemandSensing({ post: p.post, day: 'd', statePath: s, fetchImpl: fakeFetch() });
  assert.equal(p.sent.length, SE_SITES.length + 1);
});

test('all sources down is a failure, not silence', async () => {
  const r = await runDemandSensing({ post: fakePost().post, day: 'd', statePath: statePath(),
    fetchImpl: fakeFetch({ failSites: SE_SITES, hnFail: true }) });
  assert.equal(r.action, 'failed');
});

test('clean() never leaves the " — " separator OPPORTUNITIES.md lines rely on', () => {
  assert.equal(clean('Tell HN: a — b'), 'a - b');
});
